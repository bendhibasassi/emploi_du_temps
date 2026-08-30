# app/routes.py
import io
import hashlib
import re

import pandas as pd
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from sqlalchemy import or_
from sqlalchemy.orm import joinedload, selectinload
from app import db
from app.models import (
    Professeur, Matiere, Niveau, Section, Groupe, Salle, Creneau,
    Affectation, Seance, AnneeUniversitaire, Indisponibilite, Historique
)
from datetime import datetime


CODES_AMPHIS = ('A0', 'A1', 'A2', 'A3', 'BIO1', 'BIO2')
CODES_GRANDES_SALLES = (
    'DSP1', 'DSP2', 'DSP3', 'DSP4', 'DSP5', 'DSP6', 'DSP7',
    'DSP22', 'DSP23', 'DSP24'
)
CODES_PETITES_SALLES = tuple(f'DSP{numero}' for numero in range(8, 22))

REFERENTIEL_SALLES = {
    **{code: (f'Amphithéâtre {code}', 'AMPHI') for code in CODES_AMPHIS},
    **{code: (code, 'GRANDE_SALLE') for code in CODES_GRANDES_SALLES},
    **{code: (code, 'PETITE_SALLE') for code in CODES_PETITES_SALLES},
}


def ajouter_historique(utilisateur, action, type_objet, id_objet,
                       ancienne_valeur=None, nouvelle_valeur=None, ip=None):
    """Ajoute une entrée dans l'historique"""
    try:
        historique = Historique(
            utilisateur=utilisateur or 'Système',
            action=action,
            type_objet=type_objet,
            id_objet=id_objet,
            ancienne_valeur=ancienne_valeur,
            nouvelle_valeur=nouvelle_valeur,
            date_heure=datetime.utcnow(),
            ip_adresse=ip
        )
        db.session.add(historique)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"⚠️ Erreur historique : {e}")


def formater_valeur(objet, attributs):
    """Formate un objet en chaîne pour l'historique"""
    valeurs = []
    for attribut in attributs:
        valeur = getattr(objet, attribut, None)
        if valeur is not None:
            valeurs.append(f"{attribut}: {valeur}")
    return " | ".join(valeurs)


def verifier_conflit_etudiants(query, affectation):
    """Vérifie le chevauchement des étudiants selon le type d'enseignement."""
    query = query.filter(Affectation.id_section == affectation.id_section)

    if affectation.type_enseignement == 'CM':
        return query.first() is not None

    return query.filter(or_(
        Affectation.type_enseignement == 'CM',
        Affectation.id_groupe == affectation.id_groupe
    )).first() is not None


def filtrer_semaines_compatibles(query, semaine_type):
    """Conserve les séances dont la semaine chevauche la semaine demandée."""
    if semaine_type == 'TOUTES':
        return query

    return query.filter(or_(
        Seance.semaine_type == 'TOUTES',
        Seance.semaine_type == semaine_type
    ))


def verifier_capacite_salle(affectation, id_salle):
    """Retourne la salle et l'effectif requis lorsqu'elle est trop petite."""
    salle = Salle.query.get(id_salle)
    public = (Section.query.get(affectation.id_section)
              if affectation.type_enseignement == 'CM'
              else Groupe.query.get(affectation.id_groupe))

    if (salle and salle.capacite is not None and public
            and public.effectif is not None
            and salle.capacite < public.effectif):
        return salle, public.effectif
    return None


def convertir_capacite_salle(valeur):
    """Convertit une capacité facultative ou lève une erreur de validation."""
    valeur = (valeur or '').strip()
    if not valeur:
        return None

    try:
        capacite = int(valeur)
    except ValueError as exc:
        raise ValueError('La capacité doit être un nombre entier.') from exc

    if capacite < 1:
        raise ValueError('La capacité doit être supérieure à 0.')

    return capacite


def cle_tri_naturel_salle(salle):
    """Trie les codes de salles par blocs de texte et de chiffres."""
    return tuple(
        (0, int(part)) if part.isdigit() else (1, part.casefold())
        for part in re.split(r'(\d+)', salle.code_salle)
        if part
    )


def cle_priorite_salle(salle, type_enseignement):
    """Place les types conseillés en premier sans exclure aucune salle."""
    if salle.code_salle not in REFERENTIEL_SALLES:
        priorite = 3
    elif type_enseignement == 'CM':
        priorite = {'AMPHI': 0, 'GRANDE_SALLE': 1, 'PETITE_SALLE': 2}.get(
            salle.type_salle, 3
        )
    else:
        priorite = {'PETITE_SALLE': 0, 'GRANDE_SALLE': 1, 'AMPHI': 2}.get(
            salle.type_salle, 3
        )
    return priorite, cle_tri_naturel_salle(salle)


def codes_salles_officielles_disponibles():
    """Retourne les codes officiels qui ne sont pas encore enregistrés."""
    codes_utilises = {
        code for code, in db.session.query(Salle.code_salle).all()
    }
    return [code for code in REFERENTIEL_SALLES if code not in codes_utilises]

main = Blueprint('main', __name__)

# JOURS de la semaine
JOURS = {
    1: "Lundi",
    2: "Mardi", 
    3: "Mercredi",
    4: "Jeudi",
    5: "Vendredi",
    6: "Samedi",
    7: "Dimanche"
}

# ============ SERVICES ============

def verifier_indisponibilite(session, id_annee, id_professeur, jour, id_creneau):
    """Vérifie si un professeur est indisponible à un créneau donné"""
    indispo = session.query(Indisponibilite).filter(
        Indisponibilite.id_annee == id_annee,
        Indisponibilite.id_professeur == id_professeur,
        Indisponibilite.jour == jour,
        Indisponibilite.id_creneau == id_creneau,
        Indisponibilite.actif == True
    ).first()

    if indispo:
        if indispo.type_contrainte == 'INTERDIT':
            return False, f"INTERDIT : {indispo.commentaire or 'Professeur indisponible'}"
        elif indispo.type_contrainte == 'EVITER':
            return True, f"À éviter : {indispo.commentaire or ''}"
        elif indispo.type_contrainte == 'PREFERE':
            return True, f"Préféré : {indispo.commentaire or ''}"

    return True, None

@main.route('/')
def index():
    """Tableau de bord"""
    annees = AnneeUniversitaire.query.all()
    annee_active = AnneeUniversitaire.query.filter_by(active=True).first()
    professeurs = Professeur.query.all()
    matieres = Matiere.query.all()
    sections = Section.query.all()
    groupes = Groupe.query.all()
    affectations = Affectation.query.all()
    salles = Salle.query.all()
    seances = Seance.query.all()
    affectations_sans_seance = Affectation.query.outerjoin(Seance).filter(
        Seance.id_seance.is_(None)
    ).count()
    matieres_sans_affectation = Matiere.query.outerjoin(Affectation).filter(
        Affectation.id_affectation.is_(None)
    ).count()
    professeurs_sans_affectation = Professeur.query.outerjoin(Affectation).filter(
        Affectation.id_affectation.is_(None)
    ).count()
    indisponibilites = Indisponibilite.query.count()
    
    return render_template('index.html',
        annees=annees,
        professeurs=professeurs,
        matieres=matieres,
        sections=sections,
        groupes=groupes,
        affectations=affectations,
        salles=salles,
        seances=seances,
        annee_active=annee_active,
        affectations_sans_seance=affectations_sans_seance,
        matieres_sans_affectation=matieres_sans_affectation,
        professeurs_sans_affectation=professeurs_sans_affectation,
        indisponibilites=indisponibilites
    )


@main.route('/affectations')
def affectations():
    """Consulter les affectations pédagogiques existantes."""
    annees_list = AnneeUniversitaire.query.order_by(
        AnneeUniversitaire.date_debut.desc()
    ).all()
    niveaux_list = Niveau.query.order_by(
        Niveau.cycle,
        Niveau.annee_etude,
        Niveau.code_niveau
    ).all()
    sections_list = Section.query.order_by(
        Section.id_niveau,
        Section.code_section
    ).all()
    professeurs_list = Professeur.query.order_by(
        Professeur.nom,
        Professeur.prenom
    ).all()
    semestres_list = [valeur for valeur, in db.session.query(
        Affectation.semestre
    ).distinct().order_by(Affectation.semestre).all()]
    types_list = ('CM', 'TD', 'TP')

    annee_id = request.args.get('annee_id', type=int)
    niveau_id = request.args.get('niveau_id', type=int)
    section_id = request.args.get('section_id', type=int)
    professeur_id = request.args.get('professeur_id', type=int)
    semestre = request.args.get('semestre', type=int)
    type_enseignement = request.args.get('type_enseignement', '').strip()
    actif = request.args.get('actif', '').strip()
    page = max(request.args.get('page', 1, type=int) or 1, 1)

    query = Affectation.query.options(
        joinedload(Affectation.annee),
        joinedload(Affectation.professeur),
        joinedload(Affectation.matiere),
        joinedload(Affectation.section).joinedload(Section.niveau),
        joinedload(Affectation.groupe),
        selectinload(Affectation.seances),
    )

    if annee_id is not None:
        query = query.filter(Affectation.id_annee == annee_id)
    if niveau_id is not None:
        query = query.join(
            Section, Affectation.id_section == Section.id_section
        ).filter(Section.id_niveau == niveau_id)
    if section_id is not None:
        query = query.filter(Affectation.id_section == section_id)
    if professeur_id is not None:
        query = query.filter(Affectation.id_professeur == professeur_id)
    if semestre is not None:
        query = query.filter(Affectation.semestre == semestre)
    if type_enseignement in types_list:
        query = query.filter(Affectation.type_enseignement == type_enseignement)
    elif type_enseignement:
        query = query.filter(Affectation.id_affectation.is_(None))
    if actif in {'0', '1'}:
        query = query.filter(Affectation.actif.is_(actif == '1'))

    total_affectations = Affectation.query.count()
    pagination = query.order_by(
        Affectation.id_annee,
        Affectation.id_section,
        Affectation.type_enseignement,
        Affectation.id_groupe
    ).paginate(page=page, per_page=25, error_out=False)

    filtres_url = {
        cle: valeur for cle, valeur in {
            'annee_id': annee_id,
            'niveau_id': niveau_id,
            'section_id': section_id,
            'professeur_id': professeur_id,
            'semestre': semestre,
            'type_enseignement': type_enseignement or None,
            'actif': actif if actif in {'0', '1'} else None,
        }.items() if valeur is not None
    }

    return render_template(
        'affectations.html',
        affectations=pagination.items,
        pagination=pagination,
        total_affectations=total_affectations,
        filtres_url=filtres_url,
        annees=annees_list,
        niveaux=niveaux_list,
        sections=sections_list,
        professeurs=professeurs_list,
        semestres=semestres_list,
        types_enseignement=types_list,
        annee_id=annee_id,
        niveau_id=niveau_id,
        section_id=section_id,
        professeur_id=professeur_id,
        semestre_selectionne=semestre,
        type_selectionne=type_enseignement,
        actif_selectionne=actif
    )


@main.route('/niveaux-sections')
def niveaux_sections():
    """Consulter la hiérarchie des niveaux, sections et groupes."""
    niveaux_list = Niveau.query.order_by(
        Niveau.cycle,
        Niveau.annee_etude,
        Niveau.code_niveau
    ).all()
    return render_template('niveaux_sections.html', niveaux=niveaux_list)


@main.route('/creneaux')
def creneaux():
    """Consulter les créneaux horaires configurés."""
    creneaux_list = Creneau.query.order_by(Creneau.ordre).all()
    return render_template('creneaux.html', creneaux=creneaux_list)


@main.route('/annees-universitaires')
def annees_universitaires():
    """Consulter les années universitaires configurées."""
    annees_list = AnneeUniversitaire.query.order_by(
        AnneeUniversitaire.date_debut.desc()
    ).all()
    return render_template('annees_universitaires.html', annees=annees_list)

@main.route('/ajouter_seance', methods=['GET', 'POST'])
def ajouter_seance():
    """Ajouter une séance à partir d'une affectation existante."""
    if request.method == 'POST':
        id_affectation = request.form.get('id_affectation', type=int)
        jour = request.form.get('jour', type=int)
        id_creneau = request.form.get('id_creneau', type=int)
        id_salle = request.form.get('id_salle', type=int)
        semaine_type = request.form.get('semaine_type', 'TOUTES')

        # === VÉRIFICATIONS ===
        conflits = []

        # Vérifier que tous les champs sont remplis
        if not id_salle:
            flash('❌ Salle invalide ou non sélectionnée !', 'danger')
            return redirect(url_for('main.ajouter_seance'))

        if not all([id_affectation, jour, id_creneau]):
            flash('❌ Tous les champs sont obligatoires !', 'danger')
            return redirect(url_for('main.ajouter_seance'))

        if jour not in JOURS:
            flash('❌ Jour invalide !', 'danger')
            return redirect(url_for('main.ajouter_seance'))

        if Creneau.query.get(id_creneau) is None:
            flash('❌ Créneau invalide ou inexistant !', 'danger')
            return redirect(url_for('main.ajouter_seance'))

        if semaine_type not in {'TOUTES', 'PAIRE', 'IMPAIRE'}:
            flash('❌ Type de semaine invalide !', 'danger')
            return redirect(url_for('main.ajouter_seance'))

        salle_choisie = Salle.query.get(id_salle)
        if salle_choisie is None or not salle_choisie.actif:
            flash('❌ Salle invalide, inexistante ou inactive !', 'danger')
            return redirect(url_for('main.ajouter_seance'))

        affectation = Affectation.query.get(id_affectation)
        if affectation is None:
            flash('❌ Affectation invalide ou inexistante !', 'danger')
            return redirect(url_for('main.ajouter_seance'))

        id_annee = affectation.id_annee
        id_professeur = affectation.id_professeur
        id_matiere = affectation.id_matiere
        id_section = affectation.id_section
        type_enseignement = affectation.type_enseignement

        # 1. Vérifier la salle
        salle_occupee = filtrer_semaines_compatibles(Seance.query.filter_by(
            id_annee=id_annee,
            jour=jour,
            id_creneau=id_creneau,
            id_salle=id_salle
        ), semaine_type).first()
        if salle_occupee:
            salle = Salle.query.get(id_salle)
            conflits.append(f"❌ La salle {salle.nom_salle} est déjà occupée à ce créneau !")

        # 2. Vérifier le professeur
        prof_occupe = filtrer_semaines_compatibles(Seance.query.join(
            Affectation, Seance.id_affectation == Affectation.id_affectation
        ).filter(
            Seance.id_annee == id_annee,
            Seance.jour == jour,
            Seance.id_creneau == id_creneau,
            Affectation.id_professeur == id_professeur
        ), semaine_type).first()
        if prof_occupe:
            prof = Professeur.query.get(id_professeur)
            conflits.append(f"❌ Le professeur {prof.prenom} {prof.nom} est déjà occupé !")

        # 3. Vérifier les étudiants (section en CM, groupe en TD/TP)
        conflit_etudiants = verifier_conflit_etudiants(filtrer_semaines_compatibles(Seance.query.join(
            Affectation, Seance.id_affectation == Affectation.id_affectation
        ).filter(
            Seance.id_annee == id_annee,
            Seance.jour == jour,
            Seance.id_creneau == id_creneau
        ), semaine_type), affectation)
        if conflit_etudiants:
            public = (f"La section {affectation.section.libelle}"
                      if type_enseignement == 'CM'
                      else f"Le groupe {affectation.groupe.nom_groupe}")
            conflits.append(f"❌ {public} est déjà occupé !")

        # 4. Vérifier l'indisponibilité du professeur
        ok, message = verifier_indisponibilite(
            db.session, id_annee, id_professeur, jour, id_creneau
        )
        if not ok:
            conflits.append(f"❌ Indisponibilité : {message}")

        # 5. Vérifier la capacité de la salle
        conflit_capacite = verifier_capacite_salle(affectation, id_salle)
        if conflit_capacite:
            salle, effectif = conflit_capacite
            conflits.append(f"❌ Salle trop petite ! Capacité: {salle.capacite}, Effectif: {effectif}")

        # === AJOUT DE LA SÉANCE ===
        if conflits:
            for conflit in conflits:
                flash(conflit, 'danger')
            return redirect(url_for('main.ajouter_seance'))

        # Créer la séance
        seance = Seance(
            id_annee=id_annee,
            id_affectation=affectation.id_affectation,
            jour=jour,
            id_creneau=id_creneau,
            id_salle=id_salle,
            semaine_type=semaine_type,
            statut="PROPOSEE"
        )

        try:
            db.session.add(seance)
            db.session.commit()

            # Historique
            ajouter_historique(
                utilisateur='Administrateur',
                action='AJOUT',
                type_objet='SEANCE',
                id_objet=seance.id_seance,
                nouvelle_valeur=f"Prof: {id_professeur}, Matière: {id_matiere}, Section: {id_section}, Jour: {jour}, Créneau: {id_creneau}, Salle: {id_salle}",
                ip=request.remote_addr
            )

            flash('✅ Séance ajoutée avec succès !', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Erreur : {e}', 'danger')

        return redirect(url_for('main.ajouter_seance'))

    # === GET : Afficher le formulaire ===
    affectations = Affectation.query.order_by(
        Affectation.id_annee,
        Affectation.id_section,
        Affectation.type_enseignement,
        Affectation.id_groupe
    ).all()
    professeurs = Professeur.query.order_by(
        Professeur.nom,
        Professeur.prenom
    ).all()
    creneaux = Creneau.query.order_by(Creneau.ordre).all()
    salles = sorted(Salle.query.filter_by(actif=True).all(), key=cle_tri_naturel_salle)

    return render_template('ajouter_seance.html',
        affectations=affectations,
        professeurs=professeurs,
        creneaux=creneaux,
        salles=salles,
        JOURS=JOURS
    )


def verifier_conflits_seance(seance, jour, id_creneau, id_salle,
                             semaine_type=None):
    """Vérifie les conflits d'une séance, en excluant la séance modifiée."""
    conflits = []
    semaine_type = semaine_type or seance.semaine_type

    creneau_demande = Creneau.query.get(id_creneau)
    salle_occupee = None
    if creneau_demande:
        salle_occupee = filtrer_semaines_compatibles(
            Seance.query.join(
                Creneau, Seance.id_creneau == Creneau.id_creneau
            ).filter(
                Seance.id_seance != seance.id_seance,
                Seance.id_annee == seance.id_annee,
                Seance.jour == jour,
                Seance.id_salle == id_salle,
                Seance.statut != 'ANNULEE',
                Creneau.heure_debut < creneau_demande.heure_fin,
                Creneau.heure_fin > creneau_demande.heure_debut
            ), semaine_type
        ).options(
            joinedload(Seance.salle),
            joinedload(Seance.creneau),
            joinedload(Seance.affectation).joinedload(Affectation.matiere),
            joinedload(Seance.affectation).joinedload(Affectation.professeur),
            joinedload(Seance.affectation).joinedload(Affectation.section),
            joinedload(Seance.affectation).joinedload(Affectation.groupe)
        ).first()
    if salle_occupee:
        affectation_conflit = salle_occupee.affectation
        public = affectation_conflit.section.libelle
        if affectation_conflit.groupe:
            public += f' / {affectation_conflit.groupe.code_groupe}'
        conflits.append(
            f'Conflit de salle : {salle_occupee.salle.code_salle} est déjà '
            f'occupée le {JOURS[jour].lower()} de '
            f'{salle_occupee.creneau.heure_debut.strftime("%H:%M")} à '
            f'{salle_occupee.creneau.heure_fin.strftime("%H:%M")} '
            f'({affectation_conflit.matiere.nom_matiere} — '
            f'{affectation_conflit.professeur.prenom or ""} '
            f'{affectation_conflit.professeur.nom} — {public}).'
        )

    affectation = Affectation.query.get(seance.id_affectation)
    if affectation:
        professeur_occupe = filtrer_semaines_compatibles(Seance.query.join(Affectation).filter(
            Seance.id_seance != seance.id_seance,
            Seance.id_annee == seance.id_annee,
            Seance.jour == jour,
            Seance.id_creneau == id_creneau,
            Affectation.id_professeur == affectation.id_professeur,
            Seance.statut != 'ANNULEE'
        ), semaine_type).first()
        if professeur_occupe:
            conflits.append('Le professeur est déjà occupé à ce créneau.')

        conflit_etudiants = verifier_conflit_etudiants(filtrer_semaines_compatibles(
            Seance.query.join(Affectation).filter(
            Seance.id_seance != seance.id_seance,
            Seance.id_annee == seance.id_annee,
            Seance.jour == jour,
            Seance.id_creneau == id_creneau,
            Seance.statut != 'ANNULEE'
        ), semaine_type), affectation)
        if conflit_etudiants:
            public = 'La section' if affectation.type_enseignement == 'CM' else 'Le groupe'
            conflits.append(f'{public} est déjà occupé à ce créneau.')

        conflit_capacite = verifier_capacite_salle(affectation, id_salle)
        if conflit_capacite:
            salle, effectif = conflit_capacite
            conflits.append(
                f'Cette salle est trop petite (capacité : {salle.capacite}, effectif : {effectif}).'
            )

    return conflits


@main.route('/seance/<int:id_seance>/modifier', methods=['GET', 'POST'])
def modifier_seance(id_seance):
    """Modifier le jour, le créneau ou la salle d'une séance."""
    seance = Seance.query.get_or_404(id_seance)

    if request.method == 'POST':
        ancienne_valeur = f"Jour: {seance.jour}, Créneau: {seance.id_creneau}, Salle: {seance.id_salle}"
        jour = request.form.get('jour', type=int)
        id_creneau = request.form.get('id_creneau', type=int)
        id_salle = request.form.get('id_salle', type=int)
        semaine_type = request.form.get('semaine_type', '')

        if Affectation.query.get(seance.id_affectation) is None:
            flash('❌ Affectation invalide ou inexistante.', 'danger')
            return redirect(url_for('main.modifier_seance', id_seance=id_seance))

        if semaine_type not in {'TOUTES', 'PAIRE', 'IMPAIRE'}:
            flash('❌ Type de semaine invalide.', 'danger')
            return redirect(url_for('main.modifier_seance', id_seance=id_seance))

        salle_choisie = Salle.query.get(id_salle) if id_salle else None
        salle_autorisee = (salle_choisie is not None and
                           (salle_choisie.actif or id_salle == seance.id_salle))
        if jour not in JOURS or not Creneau.query.get(id_creneau) or not salle_autorisee:
            flash('❌ Jour, créneau ou salle invalide.', 'danger')
            return redirect(url_for('main.modifier_seance', id_seance=id_seance))

        conflits = verifier_conflits_seance(
            seance, jour, id_creneau, id_salle, semaine_type
        )
        if conflits:
            flash('❌ ' + ' '.join(conflits), 'danger')
            return redirect(url_for('main.modifier_seance', id_seance=id_seance))

        conflit_capacite = verifier_capacite_salle(seance.affectation, id_salle)
        if conflit_capacite:
            salle, effectif = conflit_capacite
            flash(
                f'❌ Capacité insuffisante : {salle.nom_salle} '
                f'({salle.capacite} places) pour {effectif} étudiants.',
                'danger'
            )
            return redirect(url_for('main.modifier_seance', id_seance=id_seance))

        try:
            seance.jour = jour
            seance.id_creneau = id_creneau
            seance.id_salle = id_salle
            seance.semaine_type = semaine_type
            nouvelle_valeur = f"Jour: {seance.jour}, Créneau: {seance.id_creneau}, Salle: {seance.id_salle}"
            db.session.commit()
            ajouter_historique(
                utilisateur='Administrateur',
                action='MODIFICATION',
                type_objet='SEANCE',
                id_objet=seance.id_seance,
                ancienne_valeur=ancienne_valeur,
                nouvelle_valeur=nouvelle_valeur,
                ip=request.remote_addr
            )
            flash('✅ Séance modifiée avec succès !', 'success')
            return redirect(url_for('main.emploi_du_temps'))
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Erreur lors de la modification : {e}', 'danger')

    creneaux = Creneau.query.order_by(Creneau.ordre).all()
    salles = Salle.query.filter(or_(
        Salle.actif.is_(True),
        Salle.id_salle == seance.id_salle
    )).all()
    type_enseignement = (seance.affectation.type_enseignement
                         if seance.affectation else '')
    salles = sorted(
        salles,
        key=lambda salle: cle_priorite_salle(salle, type_enseignement)
    )
    return render_template(
        'modifier_seance.html',
        seance=seance,
        creneaux=creneaux,
        salles=salles,
        JOURS=JOURS
    )


@main.route('/seance/<int:id_seance>/supprimer', methods=['POST'])
def supprimer_seance(id_seance):
    """Supprimer une séance existante."""
    seance = Seance.query.get_or_404(id_seance)
    ancienne_valeur = (f"Affectation: {seance.id_affectation}, Jour: {seance.jour}, "
                       f"Créneau: {seance.id_creneau}, Salle: {seance.id_salle}")
    try:
        ajouter_historique(
            utilisateur='Administrateur',
            action='SUPPRESSION',
            type_objet='SEANCE',
            id_objet=id_seance,
            ancienne_valeur=ancienne_valeur,
            ip=request.remote_addr
        )
        db.session.delete(seance)
        db.session.commit()
        flash('✅ Séance supprimée avec succès !', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Erreur lors de la suppression : {e}', 'danger')
    return redirect(url_for('main.emploi_du_temps'))

@main.route('/emploi_du_temps')
def emploi_du_temps():
    """Afficher l'emploi du temps"""
    seances = Seance.query.all()
    
    planning = []
    for seance in seances:
        affectation = Affectation.query.get(seance.id_affectation)
        if affectation:
            prof = Professeur.query.get(affectation.id_professeur)
            matiere = Matiere.query.get(affectation.id_matiere)
            section = Section.query.get(affectation.id_section)
            salle = Salle.query.get(seance.id_salle)
            creneau = Creneau.query.get(seance.id_creneau)
            
            planning.append({
                'id_seance': seance.id_seance,
                'prof': f"{prof.prenom} {prof.nom}" if prof else "Inconnu",
                'matiere': matiere.nom_matiere if matiere else "Inconnu",
                'section': section.libelle if section else "Inconnu",
                'groupe': affectation.groupe.code_groupe if affectation.groupe else None,
                'type_enseignement': affectation.type_enseignement,
                'jour': JOURS.get(seance.jour, "Inconnu"),
                'debut': creneau.heure_debut.strftime('%H:%M') if creneau else "???",
                'fin': creneau.heure_fin.strftime('%H:%M') if creneau else "???",
                'salle': salle.nom_salle if salle else "Inconnu",
                'capacite': salle.capacite if salle else 0,
                'semaine_type': seance.semaine_type
            })
    
    planning = sorted(planning, key=lambda x: (list(JOURS.values()).index(x['jour']) if x['jour'] in JOURS.values() else 99, x['debut']))
    
    return render_template('emploi_du_temps.html', planning=planning)

@main.route('/professeurs')
def professeurs():
    """Lister les professeurs"""
    professeurs = Professeur.query.all()
    return render_template('professeurs.html', professeurs=professeurs)


@main.route('/professeurs/<int:id_professeur>/affectations')
def affectations_professeur(id_professeur):
    """Consulter les affectations d'un professeur."""
    professeur = Professeur.query.get_or_404(id_professeur)
    affectations_list = Affectation.query.filter_by(
        id_professeur=id_professeur
    ).options(
        joinedload(Affectation.annee),
        joinedload(Affectation.matiere),
        joinedload(Affectation.section).joinedload(Section.niveau),
        joinedload(Affectation.groupe),
    ).order_by(
        Affectation.id_annee,
        Affectation.id_section,
        Affectation.semestre,
        Affectation.type_enseignement,
        Affectation.id_groupe
    ).all()

    return render_template(
        'affectations_professeur.html',
        professeur=professeur,
        affectations=affectations_list
    )


@main.route('/professeurs/<int:id_professeur>/emploi-du-temps')
def emploi_du_temps_professeur(id_professeur):
    """Afficher l'emploi du temps individuel, sans modifier les séances."""
    professeur = Professeur.query.get_or_404(id_professeur)
    seances = Seance.query.join(Affectation).filter(
        Affectation.id_professeur == id_professeur,
        Seance.statut != 'ANNULEE'
    ).options(
        joinedload(Seance.affectation).joinedload(Affectation.annee),
        joinedload(Seance.affectation).joinedload(Affectation.matiere),
        joinedload(Seance.affectation).joinedload(Affectation.section).joinedload(Section.niveau),
        joinedload(Seance.affectation).joinedload(Affectation.groupe),
        joinedload(Seance.salle),
        joinedload(Seance.creneau),
    ).join(Creneau, Seance.id_creneau == Creneau.id_creneau).order_by(
        Seance.jour,
        Creneau.heure_debut,
        Creneau.heure_fin,
        Seance.semaine_type
    ).all()

    jours_utilises = {seance.jour for seance in seances}
    jours_affiches = [
        (numero, libelle) for numero, libelle in JOURS.items()
        if numero <= 4 or numero in jours_utilises
    ]
    creneaux = sorted(
        {seance.creneau for seance in seances},
        key=lambda creneau: (creneau.heure_debut, creneau.heure_fin)
    )
    annees = sorted({seance.affectation.annee.libelle for seance in seances})

    return render_template(
        'emploi_du_temps_professeur.html',
        professeur=professeur,
        seances=seances,
        jours_affiches=jours_affiches,
        creneaux=creneaux,
        annees=annees
    )

@main.route('/ajouter_professeur', methods=['GET', 'POST'])
def ajouter_professeur():
    """Ajouter un professeur"""
    if request.method == 'POST':
        nom = request.form.get('nom', '').strip()
        prenom = request.form.get('prenom', '').strip()
        grade = request.form.get('grade', '').strip()
        email = request.form.get('email', '').strip()
        telephone = request.form.get('telephone', '').strip()
        
        # Vérifications
        if not nom:
            flash('❌ Le nom est obligatoire !', 'danger')
            return redirect(url_for('main.ajouter_professeur'))
        
        # Vérifier si l'email existe déjà
        if email:
            existing = Professeur.query.filter_by(email=email).first()
            if existing:
                flash(f'❌ L\'email {email} est déjà utilisé par {existing.prenom} {existing.nom} !', 'danger')
                return redirect(url_for('main.ajouter_professeur'))
        
        # Créer le professeur
        professeur = Professeur(
            nom=nom,
            prenom=prenom,
            grade=grade,
            email=email,
            telephone=telephone,
            actif=True
        )
        
        try:
            db.session.add(professeur)
            db.session.commit()
            ajouter_historique(
                utilisateur='Administrateur',
                action='AJOUT',
                type_objet='PROFESSEUR',
                id_objet=professeur.id_professeur,
                nouvelle_valeur=(f"Nom: {professeur.nom}, Prénom: {professeur.prenom or ''}, "
                                 f"Email: {professeur.email or ''}"),
                ip=request.remote_addr
            )
            flash(f'✅ Professeur {prenom} {nom} ajouté avec succès !', 'success')
            return redirect(url_for('main.professeurs'))
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Erreur lors de l\'ajout : {e}', 'danger')
            return redirect(url_for('main.ajouter_professeur'))
    
    # GET : Afficher le formulaire
    return render_template('ajouter_professeur.html')


# ============ GESTION DES PROFESSEURS ============

@main.route('/professeur/<int:id_professeur>/modifier', methods=['GET', 'POST'])
def modifier_professeur(id_professeur):
    """Modifier un professeur"""
    professeur = Professeur.query.get_or_404(id_professeur)

    if request.method == 'POST':
        try:
            # Récupérer les données du formulaire
            nom = request.form.get('nom', '').strip()
            prenom = request.form.get('prenom', '').strip()
            grade = request.form.get('grade', '').strip()
            email = request.form.get('email', '').strip()
            telephone = request.form.get('telephone', '').strip()
            actif = request.form.get('actif') == 'on'

            # === NOUVEAUX CHAMPS ===
            statut = request.form.get('statut', 'Permanent').strip()
            peut_cm = request.form.get('peut_cm') == 'on'
            peut_td = request.form.get('peut_td') == 'on'
            peut_tp = request.form.get('peut_tp') == 'on'

            # Validation du nom
            if not nom:
                flash('❌ Le nom est obligatoire !', 'danger')
                return redirect(url_for('main.modifier_professeur', id_professeur=id_professeur))

            # Vérifier si l'email est déjà utilisé par un autre professeur
            if email:
                existing = Professeur.query.filter(
                    Professeur.email == email,
                    Professeur.id_professeur != id_professeur
                ).first()
                if existing:
                    flash(f'❌ L\'email "{email}" est déjà utilisé par {existing.prenom} {existing.nom} !', 'danger')
                    return redirect(url_for('main.modifier_professeur', id_professeur=id_professeur))

            # Mettre à jour les champs
            ancienne_valeur = (f"Nom: {professeur.nom}, Prénom: {professeur.prenom}, "
                               f"Grade: {professeur.grade}, Statut: {professeur.statut}")

            professeur.nom = nom
            professeur.prenom = prenom if prenom else None
            professeur.grade = grade if grade else None
            professeur.email = email if email else None
            professeur.telephone = telephone if telephone else None
            professeur.actif = actif
            professeur.statut = statut
            professeur.peut_cm = peut_cm
            professeur.peut_td = peut_td
            professeur.peut_tp = peut_tp

            # Enregistrer
            db.session.commit()

            nouvelle_valeur = (f"Nom: {professeur.nom}, Prénom: {professeur.prenom}, "
                               f"Grade: {professeur.grade}, Statut: {professeur.statut}")

            # Historique
            ajouter_historique(
                utilisateur='Administrateur',
                action='MODIFICATION',
                type_objet='PROFESSEUR',
                id_objet=professeur.id_professeur,
                ancienne_valeur=ancienne_valeur,
                nouvelle_valeur=nouvelle_valeur,
                ip=request.remote_addr
            )

            flash(f'✅ Professeur {prenom} {nom} modifié avec succès !', 'success')
            return redirect(url_for('main.professeurs'))

        except Exception as e:
            db.session.rollback()
            flash(f'❌ Erreur lors de la modification : {str(e)}', 'danger')
            return redirect(url_for('main.modifier_professeur', id_professeur=id_professeur))

    return render_template('modifier_professeur.html', professeur=professeur)


@main.route('/professeur/<int:id_professeur>/supprimer', methods=['POST'])
def supprimer_professeur(id_professeur):
    """Supprimer un professeur"""
    professeur = Professeur.query.get_or_404(id_professeur)
    ancienne_valeur = f"Nom: {professeur.nom}, Prénom: {professeur.prenom}"

    try:
        db.session.delete(professeur)
        ajouter_historique(
            utilisateur='Administrateur',
            action='SUPPRESSION',
            type_objet='PROFESSEUR',
            id_objet=professeur.id_professeur,
            ancienne_valeur=ancienne_valeur,
            ip=request.remote_addr
        )
        flash(f'✅ Professeur {professeur.prenom} {professeur.nom} supprimé avec succès !', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Erreur lors de la suppression : {e}', 'danger')

    return redirect(url_for('main.professeurs'))


# ============ SALLES ============

@main.route('/salles')
def salles():
    """Liste des salles"""
    salles_list = Salle.query.filter_by(actif=True).all()
    return render_template('salles.html', salles=salles_list)


@main.route('/ajouter_salle', methods=['GET', 'POST'])
def ajouter_salle():
    """Ajouter une salle"""
    if request.method == 'POST':
        code_salle = request.form.get('code_salle', '').strip()
        batiment = request.form.get('batiment', '').strip()

        definition_salle = REFERENTIEL_SALLES.get(code_salle)
        if definition_salle is None:
            flash('❌ Code de salle invalide !', 'danger')
            return redirect(url_for('main.ajouter_salle'))

        nom_salle, type_salle = definition_salle

        try:
            capacite = convertir_capacite_salle(request.form.get('capacite'))
        except ValueError as exc:
            flash(f'❌ {exc}', 'danger')
            return redirect(url_for('main.ajouter_salle'))

        existing = Salle.query.filter_by(code_salle=code_salle).first()
        if existing:
            flash(f'❌ La salle {code_salle} existe déjà !', 'danger')
            return redirect(url_for('main.ajouter_salle'))

        salle = Salle(
            code_salle=code_salle,
            nom_salle=nom_salle,
            type_salle=type_salle,
            capacite=capacite,
            batiment=batiment if batiment else None,
            actif=True
        )

        try:
            db.session.add(salle)
            db.session.commit()
            ajouter_historique(
                utilisateur='Administrateur',
                action='AJOUT',
                type_objet='SALLE',
                id_objet=salle.id_salle,
                nouvelle_valeur=f"Code: {code_salle}, Nom: {nom_salle}, Capacité: {capacite}",
                ip=request.remote_addr
            )
            flash(f'✅ Salle {nom_salle} ajoutée avec succès !', 'success')
            return redirect(url_for('main.salles'))
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Erreur : {e}', 'danger')

    return render_template(
        'ajouter_salle.html',
        codes_salles=codes_salles_officielles_disponibles()
    )


@main.route('/salle/<int:id_salle>/modifier', methods=['GET', 'POST'])
def modifier_salle(id_salle):
    """Modifier une salle"""
    salle = Salle.query.get_or_404(id_salle)

    if request.method == 'POST':
        ancienne_valeur = f"Code: {salle.code_salle}, Nom: {salle.nom_salle}, Capacité: {salle.capacite}"

        try:
            capacite = convertir_capacite_salle(request.form.get('capacite'))
        except ValueError as exc:
            flash(f'❌ {exc}', 'danger')
            return redirect(url_for('main.modifier_salle', id_salle=id_salle))

        definition_salle = REFERENTIEL_SALLES.get(salle.code_salle)
        if definition_salle is None:
            nouveau_code = request.form.get('code_salle', '').strip()
            if nouveau_code:
                definition_salle = REFERENTIEL_SALLES.get(nouveau_code)
                code_deja_utilise = Salle.query.filter(
                    Salle.code_salle == nouveau_code,
                    Salle.id_salle != salle.id_salle
                ).first()
                if definition_salle is None or code_deja_utilise:
                    flash('❌ Code de salle invalide ou déjà utilisé !', 'danger')
                    return redirect(url_for('main.modifier_salle', id_salle=id_salle))

                salle.code_salle = nouveau_code
                salle.nom_salle, salle.type_salle = definition_salle
        else:
            code_soumis = request.form.get('code_salle', '').strip()
            if code_soumis and code_soumis != salle.code_salle:
                flash('❌ Le code d’une salle officielle ne peut pas être modifié !', 'danger')
                return redirect(url_for('main.modifier_salle', id_salle=id_salle))
            salle.nom_salle, salle.type_salle = definition_salle

        salle.capacite = capacite
        salle.batiment = request.form.get('batiment', '').strip() or None
        salle.actif = request.form.get('actif') == 'on'

        try:
            db.session.commit()
            nouvelle_valeur = f"Code: {salle.code_salle}, Nom: {salle.nom_salle}, Capacité: {salle.capacite}"
            ajouter_historique(
                utilisateur='Administrateur',
                action='MODIFICATION',
                type_objet='SALLE',
                id_objet=salle.id_salle,
                ancienne_valeur=ancienne_valeur,
                nouvelle_valeur=nouvelle_valeur,
                ip=request.remote_addr
            )
            flash(f'✅ Salle {salle.nom_salle} modifiée avec succès !', 'success')
            return redirect(url_for('main.salles'))
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Erreur : {e}', 'danger')

    return render_template(
        'modifier_salle.html',
        salle=salle,
        code_officiel=salle.code_salle in REFERENTIEL_SALLES,
        codes_salles=codes_salles_officielles_disponibles()
    )


@main.route('/salle/<int:id_salle>/supprimer', methods=['POST'])
def supprimer_salle(id_salle):
    """Supprimer une salle"""
    salle = Salle.query.get_or_404(id_salle)

    if Seance.query.filter_by(id_salle=id_salle).first():
        flash(f'❌ La salle {salle.nom_salle} est utilisée dans des séances !', 'danger')
        return redirect(url_for('main.salles'))

    try:
        ancienne_valeur = f"Code: {salle.code_salle}, Nom: {salle.nom_salle}, Capacité: {salle.capacite}"
        ajouter_historique(
            utilisateur='Administrateur',
            action='SUPPRESSION',
            type_objet='SALLE',
            id_objet=id_salle,
            ancienne_valeur=ancienne_valeur,
            ip=request.remote_addr
        )
        db.session.delete(salle)
        db.session.commit()
        flash(f'✅ Salle {salle.nom_salle} supprimée avec succès !', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Erreur : {e}', 'danger')

    return redirect(url_for('main.salles'))


# ============ GROUPES ============

@main.route('/groupes')
def groupes():
    """Liste des groupes"""
    # Récupérer tous les groupes avec leurs sections et niveaux
    groupes_list = db.session.query(
        Groupe,
        Section,
        Niveau
    ).join(
        Section, Groupe.id_section == Section.id_section
    ).join(
        Niveau, Section.id_niveau == Niveau.id_niveau
    ).filter(
        Groupe.actif == True
    ).all()

    return render_template('groupes.html', groupes=groupes_list)


@main.route('/ajouter_groupe', methods=['GET', 'POST'])
def ajouter_groupe():
    """Ajouter un groupe"""
    if request.method == 'POST':
        id_section = request.form.get('id_section', type=int)
        code_groupe = request.form.get('code_groupe', '').strip()
        nom_groupe = request.form.get('nom_groupe', '').strip()
        effectif = request.form.get('effectif', type=int)

        # Vérifications
        if not id_section or not code_groupe or not nom_groupe:
            flash('❌ La section, le code et le nom sont obligatoires !', 'danger')
            return redirect(url_for('main.ajouter_groupe'))

        # Vérifier si le groupe existe déjà dans cette section
        existing = Groupe.query.filter_by(
            id_section=id_section,
            code_groupe=code_groupe
        ).first()

        if existing:
            flash(f'❌ Le groupe {code_groupe} existe déjà dans cette section !', 'danger')
            return redirect(url_for('main.ajouter_groupe'))

        # Créer le groupe
        groupe = Groupe(
            id_section=id_section,
            code_groupe=code_groupe,
            nom_groupe=nom_groupe,
            effectif=effectif if effectif else None,
            actif=True
        )

        try:
            db.session.add(groupe)
            db.session.commit()

            # Historique
            ajouter_historique(
                utilisateur='Administrateur',
                action='AJOUT',
                type_objet='GROUPE',
                id_objet=groupe.id_groupe,
                nouvelle_valeur=f"Section: {id_section}, Code: {code_groupe}, Nom: {nom_groupe}",
                ip=request.remote_addr
            )

            flash(f'✅ Groupe {code_groupe} ajouté avec succès !', 'success')
            return redirect(url_for('main.groupes'))
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Erreur : {e}', 'danger')

    # GET : Afficher le formulaire
    sections = Section.query.filter_by(actif=True).all()
    return render_template('ajouter_groupe.html', sections=sections)


@main.route('/groupe/<int:id_groupe>/modifier', methods=['GET', 'POST'])
def modifier_groupe(id_groupe):
    """Modifier un groupe"""
    groupe = Groupe.query.get_or_404(id_groupe)

    if request.method == 'POST':
        ancienne_valeur = f"Code: {groupe.code_groupe}, Nom: {groupe.nom_groupe}, Effectif: {groupe.effectif}"

        groupe.id_section = request.form.get('id_section', type=int) or groupe.id_section
        groupe.code_groupe = request.form.get('code_groupe', groupe.code_groupe).strip()
        groupe.nom_groupe = request.form.get('nom_groupe', groupe.nom_groupe).strip()
        groupe.effectif = request.form.get('effectif', type=int) or None
        groupe.actif = request.form.get('actif') == 'on'

        try:
            db.session.commit()

            nouvelle_valeur = f"Code: {groupe.code_groupe}, Nom: {groupe.nom_groupe}, Effectif: {groupe.effectif}"

            ajouter_historique(
                utilisateur='Administrateur',
                action='MODIFICATION',
                type_objet='GROUPE',
                id_objet=groupe.id_groupe,
                ancienne_valeur=ancienne_valeur,
                nouvelle_valeur=nouvelle_valeur,
                ip=request.remote_addr
            )

            flash(f'✅ Groupe {groupe.code_groupe} modifié avec succès !', 'success')
            return redirect(url_for('main.groupes'))
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Erreur : {e}', 'danger')

    sections = Section.query.filter_by(actif=True).all()
    return render_template('modifier_groupe.html', groupe=groupe, sections=sections)


@main.route('/groupe/<int:id_groupe>/supprimer', methods=['POST'])
def supprimer_groupe(id_groupe):
    """Supprimer un groupe"""
    groupe = Groupe.query.get_or_404(id_groupe)

    # Vérifier si le groupe est utilisé dans des affectations
    affectations = Affectation.query.filter_by(id_groupe=id_groupe).first()
    if affectations:
        flash(f'❌ Le groupe {groupe.code_groupe} est utilisé dans des affectations !', 'danger')
        return redirect(url_for('main.groupes'))

    try:
        ancienne_valeur = f"Code: {groupe.code_groupe}, Nom: {groupe.nom_groupe}, Section: {groupe.id_section}"

        ajouter_historique(
            utilisateur='Administrateur',
            action='SUPPRESSION',
            type_objet='GROUPE',
            id_objet=id_groupe,
            ancienne_valeur=ancienne_valeur,
            ip=request.remote_addr
        )

        db.session.delete(groupe)
        db.session.commit()
        flash(f'✅ Groupe {groupe.code_groupe} supprimé avec succès !', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Erreur : {e}', 'danger')

    return redirect(url_for('main.groupes'))


# ============ MATIERES ============

SEMESTRES_MATIERE = ('S1', 'S2', 'S3', 'S4', 'S5', 'S6')


@main.route('/matieres')
def matieres():
    """Liste des matières"""
    matieres_list = Matiere.query.outerjoin(Niveau).order_by(
        Niveau.code_niveau,
        Matiere.semestre,
        Matiere.code_matiere
    ).all()
    return render_template('matieres.html', matieres=matieres_list)


@main.route('/ajouter_matiere', methods=['GET', 'POST'])
def ajouter_matiere():
    """Ajouter une matière"""
    if request.method == 'POST':
        code_matiere = request.form.get('code_matiere', '').strip()
        nom_matiere = request.form.get('nom_matiere', '').strip()
        id_niveau = request.form.get('id_niveau', type=int)
        semestre = request.form.get('semestre', '').strip().upper()
        avec_cm = request.form.get('avec_cm') == 'on'
        avec_td = request.form.get('avec_td') == 'on'

        # Vérifications
        if not code_matiere or not nom_matiere or not id_niveau or not semestre:
            flash('❌ Code, nom, niveau et semestre sont obligatoires !', 'danger')
            return redirect(url_for('main.ajouter_matiere'))

        if semestre not in SEMESTRES_MATIERE:
            flash('❌ Le semestre sélectionné est invalide !', 'danger')
            return redirect(url_for('main.ajouter_matiere'))

        if not Niveau.query.get(id_niveau):
            flash('❌ Le niveau sélectionné est invalide !', 'danger')
            return redirect(url_for('main.ajouter_matiere'))

        # Vérifier si la matière existe déjà
        existing = Matiere.query.filter_by(code_matiere=code_matiere).first()
        if existing:
            flash(f'❌ La matière {code_matiere} existe déjà !', 'danger')
            return redirect(url_for('main.ajouter_matiere'))

        # Créer la matière
        matiere = Matiere(
            code_matiere=code_matiere,
            nom_matiere=nom_matiere,
            id_niveau=id_niveau,
            semestre=semestre,
            avec_cm=avec_cm,
            avec_td=avec_td,
            actif=True
        )

        try:
            db.session.add(matiere)
            db.session.commit()

            # Historique
            ajouter_historique(
                utilisateur='Administrateur',
                action='AJOUT',
                type_objet='MATIERE',
                id_objet=matiere.id_matiere,
                nouvelle_valeur=(f"Code: {code_matiere}, Nom: {nom_matiere}, "
                                  f"Niveau: {id_niveau}, Semestre: {semestre}, "
                                  f"CM: {avec_cm}, TD: {avec_td}, Actif: True"),
                ip=request.remote_addr
            )

            flash(f'✅ Matière {nom_matiere} ajoutée avec succès !', 'success')
            return redirect(url_for('main.matieres'))
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Erreur : {e}', 'danger')

    niveaux = Niveau.query.order_by(Niveau.code_niveau, Niveau.libelle).all()
    return render_template(
        'ajouter_matiere.html',
        niveaux=niveaux,
        semestres=SEMESTRES_MATIERE
    )


@main.route('/matiere/<int:id_matiere>/modifier', methods=['GET', 'POST'])
def modifier_matiere(id_matiere):
    """Modifier une matière"""
    matiere = Matiere.query.get_or_404(id_matiere)

    if request.method == 'POST':
        code_matiere = request.form.get('code_matiere', '').strip()
        nom_matiere = request.form.get('nom_matiere', '').strip()
        id_niveau = request.form.get('id_niveau', type=int)
        semestre = request.form.get('semestre', '').strip().upper()
        avec_cm = request.form.get('avec_cm') == 'on'
        avec_td = request.form.get('avec_td') == 'on'
        actif = request.form.get('actif') == 'on'

        if not code_matiere or not nom_matiere or not id_niveau or not semestre:
            flash('❌ Code, nom, niveau et semestre sont obligatoires !', 'danger')
            return redirect(url_for('main.modifier_matiere', id_matiere=id_matiere))

        if semestre not in SEMESTRES_MATIERE:
            flash('❌ Le semestre sélectionné est invalide !', 'danger')
            return redirect(url_for('main.modifier_matiere', id_matiere=id_matiere))

        if not Niveau.query.get(id_niveau):
            flash('❌ Le niveau sélectionné est invalide !', 'danger')
            return redirect(url_for('main.modifier_matiere', id_matiere=id_matiere))

        existing = Matiere.query.filter(
            Matiere.code_matiere == code_matiere,
            Matiere.id_matiere != id_matiere
        ).first()
        if existing:
            flash(f'❌ La matière {code_matiere} existe déjà !', 'danger')
            return redirect(url_for('main.modifier_matiere', id_matiere=id_matiere))

        ancienne_valeur = (f"Code: {matiere.code_matiere}, Nom: {matiere.nom_matiere}, "
                           f"Niveau: {matiere.id_niveau}, Semestre: {matiere.semestre}, "
                           f"CM: {matiere.avec_cm}, TD: {matiere.avec_td}, Actif: {matiere.actif}")

        matiere.code_matiere = code_matiere
        matiere.nom_matiere = nom_matiere
        matiere.id_niveau = id_niveau
        matiere.semestre = semestre
        matiere.avec_cm = avec_cm
        matiere.avec_td = avec_td
        matiere.actif = actif

        try:
            db.session.commit()

            nouvelle_valeur = (f"Code: {matiere.code_matiere}, Nom: {matiere.nom_matiere}, "
                               f"Niveau: {matiere.id_niveau}, Semestre: {matiere.semestre}, "
                               f"CM: {matiere.avec_cm}, TD: {matiere.avec_td}, Actif: {matiere.actif}")

            ajouter_historique(
                utilisateur='Administrateur',
                action='MODIFICATION',
                type_objet='MATIERE',
                id_objet=matiere.id_matiere,
                ancienne_valeur=ancienne_valeur,
                nouvelle_valeur=nouvelle_valeur,
                ip=request.remote_addr
            )

            flash(f'✅ Matière {matiere.nom_matiere} modifiée avec succès !', 'success')
            return redirect(url_for('main.matieres'))
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Erreur : {e}', 'danger')

    niveaux = Niveau.query.order_by(Niveau.code_niveau, Niveau.libelle).all()
    return render_template(
        'modifier_matiere.html',
        matiere=matiere,
        niveaux=niveaux,
        semestres=SEMESTRES_MATIERE
    )


@main.route('/matiere/<int:id_matiere>/supprimer', methods=['POST'])
def supprimer_matiere(id_matiere):
    """Supprimer une matière"""
    matiere = Matiere.query.get_or_404(id_matiere)

    # Vérifier si la matière est utilisée dans des affectations
    affectations = Affectation.query.filter_by(id_matiere=id_matiere).first()
    if affectations:
        flash(f'❌ La matière {matiere.nom_matiere} est utilisée dans des cours !', 'danger')
        return redirect(url_for('main.matieres'))

    try:
        ancienne_valeur = f"Code: {matiere.code_matiere}, Nom: {matiere.nom_matiere}"

        ajouter_historique(
            utilisateur='Administrateur',
            action='SUPPRESSION',
            type_objet='MATIERE',
            id_objet=id_matiere,
            ancienne_valeur=ancienne_valeur,
            ip=request.remote_addr
        )

        db.session.delete(matiere)
        db.session.commit()
        flash(f'✅ Matière {matiere.nom_matiere} supprimée avec succès !', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Erreur : {e}', 'danger')

    return redirect(url_for('main.matieres'))


# ============ INDISPONIBILITES ============

@main.route('/indisponibilites')
def indisponibilites():
    """Liste des indisponibilités"""
    indispos = Indisponibilite.query.order_by(
        Indisponibilite.jour,
        Indisponibilite.id_creneau
    ).all()
    return render_template('indisponibilites.html', indispos=indispos, JOURS=JOURS)


@main.route('/indisponibilite/ajouter', methods=['GET', 'POST'])
def ajouter_indisponibilite():
    """Ajouter une indisponibilité"""
    if request.method == 'POST':
        id_annee = request.form.get('id_annee', type=int)
        id_professeur = request.form.get('id_professeur', type=int)
        jour = request.form.get('jour', type=int)
        id_creneau = request.form.get('id_creneau', type=int)
        type_contrainte = request.form.get('type_contrainte', 'INTERDIT')
        commentaire = request.form.get('commentaire', '').strip()

        existing = Indisponibilite.query.filter_by(
            id_annee=id_annee,
            id_professeur=id_professeur,
            jour=jour,
            id_creneau=id_creneau
        ).first()

        if existing:
            flash('⚠️ Cette indisponibilité existe déjà !', 'warning')
            return redirect(url_for('main.ajouter_indisponibilite'))

        indispo = Indisponibilite(
            id_annee=id_annee,
            id_professeur=id_professeur,
            jour=jour,
            id_creneau=id_creneau,
            type_contrainte=type_contrainte,
            commentaire=commentaire,
            actif=True
        )

        try:
            db.session.add(indispo)
            db.session.commit()
            ajouter_historique(
                utilisateur='Administrateur',
                action='AJOUT',
                type_objet='INDISPONIBILITE',
                id_objet=indispo.id_indisponibilite,
                nouvelle_valeur=(f"Prof: {id_professeur}, Jour: {jour}, "
                                 f"Créneau: {id_creneau}, Type: {type_contrainte}"),
                ip=request.remote_addr
            )
            prof = Professeur.query.get(id_professeur)
            flash(f'✅ Indisponibilité ajoutée pour {prof.prenom} {prof.nom}', 'success')
            return redirect(url_for('main.indisponibilites'))
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Erreur : {e}', 'danger')

    annees = AnneeUniversitaire.query.all()
    professeurs = Professeur.query.filter_by(actif=True).all()
    creneaux = Creneau.query.order_by(Creneau.ordre).all()

    return render_template(
        'ajouter_indisponibilite.html',
        annees=annees,
        professeurs=professeurs,
        creneaux=creneaux,
        JOURS=JOURS
    )


@main.route('/indisponibilite/<int:id_indispo>/supprimer', methods=['POST'])
def supprimer_indisponibilite(id_indispo):
    """Supprimer une indisponibilité"""
    indispo = Indisponibilite.query.get_or_404(id_indispo)
    prof = Professeur.query.get(indispo.id_professeur)
    ancienne_valeur = (f"Prof: {indispo.id_professeur}, Jour: {indispo.jour}, "
                       f"Créneau: {indispo.id_creneau}, Type: {indispo.type_contrainte}")

    try:
        ajouter_historique(
            utilisateur='Administrateur',
            action='SUPPRESSION',
            type_objet='INDISPONIBILITE',
            id_objet=id_indispo,
            ancienne_valeur=ancienne_valeur,
            ip=request.remote_addr
        )
        db.session.delete(indispo)
        db.session.commit()
        flash(f'✅ Indisponibilité supprimée pour {prof.prenom} {prof.nom}', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Erreur : {e}', 'danger')

    return redirect(url_for('main.indisponibilites'))


# ============ IMPORT EXCEL ============

ALLOWED_EXTENSIONS = {'xlsx', 'xls'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@main.route('/importer_professeurs', methods=['GET', 'POST'])
def importer_professeurs():
    """Importer des professeurs depuis un fichier Excel"""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('❌ Aucun fichier sélectionné !', 'danger')
            return redirect(url_for('main.importer_professeurs'))

        file = request.files['file']

        if file.filename == '':
            flash('❌ Aucun fichier sélectionné !', 'danger')
            return redirect(url_for('main.importer_professeurs'))

        if not allowed_file(file.filename):
            flash('❌ Format non supporté. Utilisez .xlsx ou .xls', 'danger')
            return redirect(url_for('main.importer_professeurs'))

        try:
            df = pd.read_excel(file)
            colonnes_requises = ['nom', 'prenom', 'grade', 'email', 'telephone']
            colonnes_manquantes = [col for col in colonnes_requises if col not in df.columns]

            if colonnes_manquantes:
                flash(f'❌ Colonnes manquantes : {", ".join(colonnes_manquantes)}', 'danger')
                return redirect(url_for('main.importer_professeurs'))

            ajoutes = 0
            ignores = 0
            erreurs = []

            for index, row in df.iterrows():
                nom = str(row['nom']).strip() if pd.notna(row['nom']) else ''
                prenom = str(row['prenom']).strip() if pd.notna(row['prenom']) else ''
                grade = str(row['grade']).strip() if pd.notna(row['grade']) else ''
                email = str(row['email']).strip() if pd.notna(row['email']) else ''
                telephone = str(row['telephone']).strip() if pd.notna(row['telephone']) else ''

                if not nom:
                    erreurs.append(f'Ligne {index + 2}: Nom manquant')
                    continue

                if email and Professeur.query.filter_by(email=email).first():
                    ignores += 1
                    erreurs.append(f'Ligne {index + 2}: Email {email} déjà utilisé')
                    continue

                db.session.add(Professeur(
                    nom=nom,
                    prenom=prenom or None,
                    grade=grade or None,
                    email=email or None,
                    telephone=telephone or None,
                    actif=True
                ))
                ajoutes += 1

            db.session.commit()

            message = f'✅ {ajoutes} professeurs importés avec succès !'
            if ignores:
                message += f' ⚠️ {ignores} ignorés (doublons)'
            flash(message, 'success')

            for erreur in erreurs[:5]:
                flash(f'⚠️ {erreur}', 'warning')

            return redirect(url_for('main.professeurs'))
        except Exception as e:
            db.session.rollback()
            flash(f"❌ Erreur lors de l'import : {e}", 'danger')
            return redirect(url_for('main.importer_professeurs'))

    return render_template('importer_professeurs.html')


@main.route('/exporter_modele_professeurs')
def exporter_modele_professeurs():
    """Exporter un modèle Excel pour l'import"""
    data = {
        'nom': ['Dupont', 'Martin', 'Garbi'],
        'prenom': ['Jean', 'Sophie', 'Mohamed'],
        'grade': ['Maître de conférences', 'Professeur des universités', 'Maître de conférences'],
        'email': ['jean.dupont@univ.fr', 'sophie.martin@univ.fr', 'mohamed.garbi@univ.fr'],
        'telephone': ['01 23 45 67 89', '01 23 45 67 90', '01 23 45 67 91']
    }
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        pd.DataFrame(data).to_excel(writer, sheet_name='Professeurs', index=False)

    output.seek(0)
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='modele_professeurs.xlsx'
    )


@main.route('/historique')
def historique():
    """Afficher l'historique des modifications"""
    page = request.args.get('page', 1, type=int)
    per_page = 50

    historiques = Historique.query.order_by(
        Historique.date_heure.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)

    return render_template('historique.html', historiques=historiques)
