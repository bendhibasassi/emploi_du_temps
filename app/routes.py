# app/routes.py
import io
import hashlib
import re
from urllib.parse import urlsplit

import pandas as pd
from flask import (
    Blueprint, abort, current_app, render_template, request, redirect, session,
    url_for, flash, send_file,
)
from werkzeug.security import check_password_hash
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload, selectinload, load_only
from app import db
from app.models import (
    Professeur, Matiere, Niveau, Section, Groupe, Salle, Creneau,
    Affectation, Seance, AnneeUniversitaire, Indisponibilite, Historique
)
from app.referentiels import SALLES_OFFICIELLES, TYPES_SALLE
from app.services.database_viewer import (
    lister_tables_autorisees,
    obtenir_donnees_paginees,
    obtenir_metadonnees,
    obtenir_table_autorisee,
)
from datetime import datetime


main = Blueprint('main', __name__)


def destination_sure(destination):
    """N'autorise qu'une destination locale après connexion."""
    if not destination:
        return None
    cible = urlsplit(destination)
    if cible.scheme or cible.netloc or not cible.path.startswith('/'):
        return None
    return destination


def administrateur_requis():
    """Redirige les consultations d'administration non authentifiées."""
    if not session.get('admin_connecte'):
        flash('Connectez-vous pour accéder à cette page.', 'warning')
        return redirect(url_for('main.connexion', next=request.full_path))
    return None


@main.route('/connexion', methods=['GET', 'POST'])
def connexion():
    """Ouvre une session administrateur configurée par l'environnement."""
    destination = destination_sure(request.values.get('next'))
    if request.method == 'POST':
        utilisateur = request.form.get('utilisateur', '').strip()
        mot_de_passe = request.form.get('mot_de_passe', '')
        utilisateur_attendu = current_app.config.get('ADMIN_USERNAME')
        hash_attendu = current_app.config.get('ADMIN_PASSWORD_HASH')

        if (hash_attendu and utilisateur == utilisateur_attendu and
                check_password_hash(hash_attendu, mot_de_passe)):
            session.clear()
            session['admin_connecte'] = True
            session['admin_username'] = utilisateur_attendu
            flash('Connexion réussie.', 'success')
            return redirect(destination or url_for('main.index'))

        flash('Identifiants invalides ou administrateur non configuré.', 'danger')

    return render_template('connexion.html', next_url=destination)


@main.route('/deconnexion', methods=['POST'])
def deconnexion():
    """Ferme la session administrateur."""
    session.clear()
    flash('Vous êtes déconnecté.', 'info')
    return redirect(url_for('main.index'))


@main.route('/admin/bdd', methods=['GET'])
def admin_bdd():
    """Présente les seules tables métier autorisées à la consultation."""
    refus = administrateur_requis()
    if refus:
        return refus
    return render_template(
        'admin_bdd.html', tables=lister_tables_autorisees()
    )


@main.route('/admin/bdd/<table>', methods=['GET'])
def admin_bdd_table(table):
    """Affiche les métadonnées et une page d'une table autorisée."""
    refus = administrateur_requis()
    if refus:
        return refus
    configuration = obtenir_table_autorisee(table)
    if configuration is None:
        abort(404)

    valeur_page = request.args.get('page', '1')
    try:
        page = int(valeur_page)
    except (TypeError, ValueError):
        abort(400, description='Le numéro de page doit être un entier positif.')
    if page < 1:
        abort(400, description='Le numéro de page doit être un entier positif.')

    metadonnees = obtenir_metadonnees(table)
    colonnes, lignes, pagination = obtenir_donnees_paginees(table, page)
    return render_template(
        'admin_bdd_table.html',
        nom_table=table,
        libelle_table=configuration['libelle'],
        metadonnees=metadonnees,
        colonnes=colonnes,
        lignes=lignes,
        pagination=pagination,
    )


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


def filtrer_chevauchements_creneau(query, creneau_demande):
    """Conserve les créneaux qui chevauchent réellement celui demandé."""
    return query.filter(
        Creneau.heure_debut < creneau_demande.heure_fin,
        Creneau.heure_fin > creneau_demande.heure_debut
    )


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
    if type_enseignement == 'CM':
        priorite = {'AMPHI': 0, 'GRANDE_SALLE': 1, 'PETITE_SALLE': 2}.get(
            salle.type_salle, 3
        )
    else:
        priorite = {'PETITE_SALLE': 0, 'GRANDE_SALLE': 1, 'AMPHI': 2}.get(
            salle.type_salle, 3
        )
    return priorite, cle_tri_naturel_salle(salle)


def determiner_annee_consultation():
    """Retourne l'année demandée, sinon l'année active, sinon aucune."""
    annee_brute = request.args.get('annee_id')
    if annee_brute is None:
        annee_brute = request.args.get('annee')

    if annee_brute and annee_brute.strip():
        try:
            return int(annee_brute), False
        except ValueError:
            return -1, False

    annee_active = AnneeUniversitaire.query.filter_by(active=True).first()
    return (
        annee_active.id_annee if annee_active else None,
        annee_active is None
    )

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
    creneau_demande = session.query(Creneau).get(id_creneau)
    if creneau_demande is None:
        return True, None

    indispo = filtrer_chevauchements_creneau(
        session.query(Indisponibilite).join(
            Creneau, Indisponibilite.id_creneau == Creneau.id_creneau
        ).filter(
            Indisponibilite.id_annee == id_annee,
            Indisponibilite.id_professeur == id_professeur,
            Indisponibilite.jour == jour,
            Indisponibilite.actif == True
        ), creneau_demande
    ).first()

    if indispo:
        if indispo.type_contrainte == 'INTERDIT':
            return False, f"INTERDIT : {indispo.commentaire or 'Professeur indisponible'}"
        elif indispo.type_contrainte == 'EVITER':
            return True, f"À éviter : {indispo.commentaire or ''}"
        elif indispo.type_contrainte == 'PREFERE':
            return True, f"Préféré : {indispo.commentaire or ''}"

    return True, None


def verifier_conflits_attribution_professeur(session, affectation, professeur):
    """Vérifie les contraintes du professeur pour les séances transférées."""
    conflits = []
    for seance in affectation.seances:
        if seance.statut == 'ANNULEE':
            continue

        creneau = session.query(Creneau).get(seance.id_creneau)
        if creneau is None:
            conflits.append(
                f'Séance {seance.id_seance} : créneau introuvable.'
            )
            continue

        professeur_occupe = filtrer_semaines_compatibles(
            filtrer_chevauchements_creneau(
                session.query(Seance).join(Affectation).join(
                    Creneau, Seance.id_creneau == Creneau.id_creneau
                ).filter(
                    Seance.id_seance != seance.id_seance,
                    Seance.id_annee == seance.id_annee,
                    Seance.jour == seance.jour,
                    Affectation.id_professeur == professeur.id_professeur,
                    Seance.statut != 'ANNULEE',
                ),
                creneau,
            ),
            seance.semaine_type,
        ).first()
        if professeur_occupe:
            conflits.append(
                f'Séance {seance.id_seance}, {JOURS[seance.jour]} '
                f'{creneau.heure_debut.strftime("%H:%M")}-'
                f'{creneau.heure_fin.strftime("%H:%M")} : le professeur est '
                'déjà occupé.'
            )

        disponible, message = verifier_indisponibilite(
            session,
            seance.id_annee,
            professeur.id_professeur,
            seance.jour,
            seance.id_creneau,
        )
        if not disponible:
            conflits.append(
                f'Séance {seance.id_seance}, {JOURS[seance.jour]} '
                f'{creneau.heure_debut.strftime("%H:%M")}-'
                f'{creneau.heure_fin.strftime("%H:%M")} : {message}'
            )
    return conflits


def trouver_affectation_equivalente(session, affectation, id_professeur):
    """Cherche une autre affectation ayant la même identité métier."""
    return session.query(Affectation).filter(
        Affectation.id_affectation != affectation.id_affectation,
        Affectation.id_annee == affectation.id_annee,
        Affectation.id_professeur == id_professeur,
        Affectation.id_matiere == affectation.id_matiere,
        Affectation.id_section == affectation.id_section,
        Affectation.id_groupe == affectation.id_groupe,
        Affectation.type_enseignement == affectation.type_enseignement,
        Affectation.semestre == affectation.semestre,
    ).first()


def remplacer_professeur_affectation(session, affectation, professeur):
    """Prépare un transfert placeholder vers professeur réel, sans commit."""
    if not affectation.professeur.est_placeholder:
        raise ValueError(
            'Seule une affectation actuellement liée à un profil « À affecter » '
            'peut utiliser ce workflow.'
        )
    if (professeur.est_placeholder or not professeur.actif or
            professeur.statut != 'Vacataire'):
        raise ValueError(
            'Le nouveau professeur doit être un vacataire réel et actif.'
        )

    if trouver_affectation_equivalente(
            session, affectation, professeur.id_professeur):
        raise ValueError(
            'Attribution refusée : ce vacataire possède déjà une affectation '
            'métier équivalente.'
        )

    conflits = verifier_conflits_attribution_professeur(
        session, affectation, professeur
    )
    if conflits:
        raise ValueError('Remplacement refusé : ' + ' '.join(conflits))

    ancien_professeur = affectation.professeur
    affectation.id_professeur = professeur.id_professeur
    return ancien_professeur

@main.route('/')
def index():
    """Tableau de bord"""
    annees = AnneeUniversitaire.query.all()
    annee_active = AnneeUniversitaire.query.filter_by(active=True).first()
    annee_id = annee_active.id_annee if annee_active else None
    professeurs = Professeur.query.filter(
        ~Professeur.est_placeholder
    ).all()
    matieres = Matiere.query.all()
    sections = Section.query.all()
    groupes = Groupe.query.all()
    salles = Salle.query.all()

    if annee_id is None:
        affectations = []
        seances = []
        affectations_sans_seance = 0
        matieres_sans_affectation = 0
        professeurs_sans_affectation = 0
        indisponibilites = 0
    else:
        affectations = Affectation.query.filter_by(id_annee=annee_id).all()
        seances = Seance.query.filter_by(id_annee=annee_id).all()
        affectations_sans_seance = Affectation.query.outerjoin(Seance).filter(
            Affectation.id_annee == annee_id,
            Seance.id_seance.is_(None)
        ).count()
        matieres_sans_affectation = Matiere.query.filter(
            ~Matiere.affectations.any(Affectation.id_annee == annee_id)
        ).count()
        professeurs_sans_affectation = Professeur.query.filter(
            ~Professeur.est_placeholder,
            ~Professeur.affectations.any(Affectation.id_annee == annee_id)
        ).count()
        indisponibilites = Indisponibilite.query.filter_by(
            id_annee=annee_id
        ).count()
    
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

    annee_id, aucune_annee_active = determiner_annee_consultation()
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

    if aucune_annee_active:
        query = query.filter(Affectation.id_affectation.is_(None))
    elif annee_id is not None:
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
        aucune_annee_active=aucune_annee_active,
        niveau_id=niveau_id,
        section_id=section_id,
        professeur_id=professeur_id,
        semestre_selectionne=semestre,
        type_selectionne=type_enseignement,
        actif_selectionne=actif
    )


TYPES_ENSEIGNEMENT = ('CM', 'TD', 'TP')


def contexte_formulaire_affectation(affectation=None):
    """Charge les référentiels nécessaires au formulaire d'affectation."""
    return {
        'affectation': affectation,
        'annees': AnneeUniversitaire.query.order_by(
            AnneeUniversitaire.date_debut.desc()
        ).all(),
        'professeurs': Professeur.query.order_by(
            Professeur.nom, Professeur.prenom
        ).all(),
        'matieres': Matiere.query.order_by(
            Matiere.code_matiere
        ).all(),
        'sections': Section.query.options(joinedload(Section.niveau)).order_by(
            Section.id_niveau, Section.code_section
        ).all(),
        'groupes': Groupe.query.order_by(
            Groupe.id_section, Groupe.code_groupe
        ).all(),
        'types_enseignement': TYPES_ENSEIGNEMENT,
        'annee_active': AnneeUniversitaire.query.filter_by(active=True).first(),
    }


def lire_affectation_formulaire(affectation=None):
    """Valide et normalise les champs communs de création/modification."""
    id_annee = request.form.get('id_annee', type=int)
    id_professeur = request.form.get('id_professeur', type=int)
    id_matiere = request.form.get('id_matiere', type=int)
    id_section = request.form.get('id_section', type=int)
    id_groupe = request.form.get('id_groupe', type=int)
    type_enseignement = request.form.get('type_enseignement', '').strip()

    objets = {
        'annee': AnneeUniversitaire.query.get(id_annee) if id_annee else None,
        'professeur': Professeur.query.get(id_professeur) if id_professeur else None,
        'matiere': Matiere.query.get(id_matiere) if id_matiere else None,
        'section': Section.query.get(id_section) if id_section else None,
        'groupe': Groupe.query.get(id_groupe) if id_groupe else None,
    }
    requis = ('annee', 'professeur', 'matiere', 'section')
    if any(objets[cle] is None for cle in requis):
        return None, 'Année, professeur, matière et section valides sont obligatoires.'
    if id_groupe and objets['groupe'] is None:
        return None, 'Le groupe sélectionné est invalide.'
    if objets['groupe'] and objets['groupe'].id_section != id_section:
        return None, 'Le groupe sélectionné n’appartient pas à la section choisie.'
    if type_enseignement not in TYPES_ENSEIGNEMENT:
        return None, 'Le type d’enseignement doit être CM, TD ou TP.'
    if type_enseignement == 'CM' and objets['groupe'] is not None:
        return None, 'Une affectation CM concerne toute la section et ne peut pas avoir de groupe.'
    if type_enseignement in {'TD', 'TP'} and objets['groupe'] is None:
        return None, 'Une affectation TD ou TP doit obligatoirement cibler un groupe.'
    if (objets['matiere'].id_niveau is not None and
            objets['matiere'].id_niveau != objets['section'].id_niveau):
        return None, 'La matière n’appartient pas au niveau de la section choisie.'

    paire_historique = bool(
        affectation and affectation.id_matiere == id_matiere and
        affectation.type_enseignement == type_enseignement
    )
    indicateur_inhabituel = (
        (type_enseignement == 'CM' and not objets['matiere'].avec_cm) or
        (type_enseignement == 'TD' and not objets['matiere'].avec_td)
    )
    if (indicateur_inhabituel and not paire_historique and
            request.form.get('confirmer_indicateur') != 'on'):
        return None, (
            f'La matière indique que le type {type_enseignement} n’est pas '
            'habituel. Cochez la confirmation pour enregistrer malgré cet '
            'avertissement.'
        )

    try:
        semestre = int(request.form.get('semestre', ''))
        nb_seances = int(request.form.get('nb_seances_semaine', ''))
        duree = int(request.form.get('duree_seance_minutes', ''))
        priorite = int(request.form.get('priorite', ''))
        volume_texte = request.form.get('volume_total_minutes', '').strip()
        volume = int(volume_texte) if volume_texte else None
    except (TypeError, ValueError):
        return None, 'Les valeurs de semestre et de charge doivent être des entiers.'
    if not 1 <= semestre <= 6:
        return None, 'Le semestre doit être compris entre 1 et 6.'
    if nb_seances <= 0 or duree <= 0 or priorite < 0:
        return None, 'Séances, durée et priorité doivent contenir des valeurs valides.'
    if volume is not None and volume < 0:
        return None, 'Le volume total ne peut pas être négatif.'

    valeurs = {
        'id_annee': id_annee,
        'id_professeur': id_professeur,
        'id_matiere': id_matiere,
        'id_section': id_section,
        'id_groupe': id_groupe,
        'type_enseignement': type_enseignement,
        'semestre': semestre,
        'nb_seances_semaine': nb_seances,
        'duree_seance_minutes': duree,
        'volume_total_minutes': volume,
        'priorite': priorite,
        'actif': request.form.get('actif') == 'on',
    }

    doublon = Affectation.query.filter_by(
        id_annee=id_annee,
        id_professeur=id_professeur,
        id_matiere=id_matiere,
        id_section=id_section,
        id_groupe=id_groupe,
        type_enseignement=type_enseignement,
        semestre=semestre,
    )
    if affectation:
        doublon = doublon.filter(
            Affectation.id_affectation != affectation.id_affectation
        )
    if doublon.first():
        return None, 'Une affectation identique existe déjà.'
    return valeurs, None


@main.route('/affectation/ajouter', methods=['GET', 'POST'])
def ajouter_affectation():
    """Créer une affectation pédagogique."""
    if request.method == 'POST':
        valeurs, erreur = lire_affectation_formulaire()
        if erreur:
            flash(erreur, 'danger')
        else:
            affectation = Affectation(**valeurs)
            db.session.add(affectation)
            db.session.commit()
            flash('Affectation créée avec succès.', 'success')
            return redirect(url_for(
                'main.affectations', annee_id=affectation.id_annee
            ))
    return render_template(
        'formulaire_affectation.html',
        **contexte_formulaire_affectation()
    )


@main.route('/affectation/<int:id_affectation>/modifier', methods=['GET', 'POST'])
def modifier_affectation(id_affectation):
    """Modifier une affectation sans altérer ses séances."""
    affectation = Affectation.query.options(
        selectinload(Affectation.seances)
    ).get_or_404(id_affectation)
    if request.method == 'POST':
        valeurs, erreur = lire_affectation_formulaire(affectation)
        if not erreur and affectation.seances:
            champs_semantiques = (
                'id_annee', 'id_professeur', 'id_matiere', 'id_section',
                'id_groupe', 'type_enseignement'
            )
            if any(getattr(affectation, champ) != valeurs[champ]
                   for champ in champs_semantiques):
                erreur = (
                    'Cette affectation possède des séances : année, professeur, '
                    'matière, section, groupe et type ne peuvent pas être modifiés.'
                )
        if erreur:
            flash(erreur, 'danger')
        else:
            for champ, valeur in valeurs.items():
                setattr(affectation, champ, valeur)
            db.session.commit()
            flash('Affectation modifiée avec succès.', 'success')
            return redirect(url_for(
                'main.affectations', annee_id=affectation.id_annee
            ))
    return render_template(
        'formulaire_affectation.html',
        **contexte_formulaire_affectation(affectation)
    )


@main.route(
    '/affectation/<int:id_affectation>/attribuer-professeur',
    methods=['GET', 'POST'],
)
def attribuer_professeur_affectation(id_affectation):
    """Remplacer un placeholder par un professeur réel existant."""
    affectation = Affectation.query.options(
        joinedload(Affectation.professeur),
        joinedload(Affectation.matiere),
        joinedload(Affectation.section),
        joinedload(Affectation.groupe),
        selectinload(Affectation.seances),
    ).get_or_404(id_affectation)

    if not affectation.professeur.est_placeholder:
        flash(
            'Cette action est réservée aux affectations encore à attribuer.',
            'danger',
        )
        return redirect(url_for(
            'main.modifier_affectation', id_affectation=id_affectation
        ))

    professeurs = Professeur.query.filter(
        ~Professeur.est_placeholder,
        Professeur.actif.is_(True),
        Professeur.statut == 'Vacataire',
    ).order_by(Professeur.nom, Professeur.prenom).all()

    if request.method == 'POST':
        id_professeur = request.form.get('id_professeur', type=int)
        professeur = Professeur.query.get(id_professeur) if id_professeur else None
        if professeur is None:
            flash('Sélectionnez un professeur valide.', 'danger')
        else:
            ancien_professeur = affectation.professeur
            try:
                remplacer_professeur_affectation(
                    db.session, affectation, professeur
                )
                db.session.add(Historique(
                    utilisateur='Administrateur',
                    action='MODIFICATION',
                    type_objet='AFFECTATION',
                    id_objet=affectation.id_affectation,
                    ancienne_valeur=(
                        f'Professeur: {ancien_professeur.id_professeur} — '
                        f'{ancien_professeur.prenom or ""} '
                        f'{ancien_professeur.nom}'
                    ),
                    nouvelle_valeur=(
                        f'Remplacement professeur affectation — Professeur: '
                        f'{professeur.id_professeur} — '
                        f'{professeur.prenom or ""} {professeur.nom}'
                    ),
                    date_heure=datetime.utcnow(),
                    ip_adresse=request.remote_addr,
                ))
                db.session.commit()
            except ValueError as exc:
                db.session.rollback()
                flash(str(exc), 'danger')
            except SQLAlchemyError:
                db.session.rollback()
                flash('Le remplacement n’a pas pu être enregistré.', 'danger')
            else:
                flash('Affectation attribuée au professeur avec succès.', 'success')
                return redirect(url_for(
                    'main.modifier_affectation', id_affectation=id_affectation
                ))

    return render_template(
        'attribuer_professeur_affectation.html',
        affectation=affectation,
        professeurs=professeurs,
    )


@main.route('/affectation/<int:id_affectation>/statut', methods=['POST'])
def changer_statut_affectation(id_affectation):
    """Activer ou désactiver une affectation sans supprimer ses séances."""
    affectation = Affectation.query.get_or_404(id_affectation)
    actif = request.form.get('actif')
    if actif not in {'0', '1'}:
        flash('Statut d’affectation invalide.', 'danger')
    else:
        affectation.actif = actif == '1'
        db.session.commit()
        flash(
            'Affectation activée.' if affectation.actif
            else 'Affectation désactivée.',
            'success'
        )
    return redirect(url_for(
        'main.affectations', annee_id=affectation.id_annee,
        actif='1' if affectation.actif else '0'
    ))


@main.route('/affectation/<int:id_affectation>/supprimer', methods=['POST'])
def supprimer_affectation(id_affectation):
    """Supprimer uniquement une affectation qui n'est liée à aucune séance."""
    affectation = Affectation.query.get_or_404(id_affectation)
    nombre_seances = Seance.query.filter_by(
        id_affectation=id_affectation
    ).count()
    if nombre_seances:
        flash(
            'Impossible de supprimer cette affectation : elle est utilisée '
            f'par {nombre_seances} séance(s).',
            'danger'
        )
    else:
        id_annee = affectation.id_annee
        db.session.delete(affectation)
        db.session.commit()
        flash('Affectation supprimée avec succès.', 'success')
        return redirect(url_for('main.affectations', annee_id=id_annee))

    return redirect(url_for(
        'main.affectations', annee_id=affectation.id_annee
    ))


@main.route('/niveaux-sections')
def niveaux_sections():
    """Consulter la hiérarchie des niveaux, sections et groupes."""
    niveaux_list = Niveau.query.order_by(
        Niveau.cycle,
        Niveau.annee_etude,
        Niveau.code_niveau
    ).all()
    return render_template('niveaux_sections.html', niveaux=niveaux_list)


@main.route('/niveau/ajouter', methods=['GET', 'POST'])
def ajouter_niveau():
    """Ajouter un niveau au référentiel."""
    if request.method == 'POST':
        code_niveau = request.form.get('code_niveau', '').strip()
        cycle = request.form.get('cycle', '').strip()
        specialite = request.form.get('specialite', '').strip()
        annee_etude = request.form.get('annee_etude', '').strip()
        libelle = request.form.get('libelle', '').strip()

        if not all([code_niveau, cycle, specialite, annee_etude, libelle]):
            flash('Tous les champs du niveau sont obligatoires.', 'danger')
            return redirect(url_for('main.ajouter_niveau'))
        if Niveau.query.filter_by(code_niveau=code_niveau).first():
            flash(f'Le code niveau {code_niveau} existe déjà.', 'danger')
            return redirect(url_for('main.ajouter_niveau'))
        if Niveau.query.filter_by(libelle=libelle).first():
            flash(f'Le libellé {libelle} existe déjà.', 'danger')
            return redirect(url_for('main.ajouter_niveau'))

        niveau = Niveau(
            code_niveau=code_niveau,
            cycle=cycle,
            specialite=specialite,
            annee_etude=annee_etude,
            libelle=libelle,
            actif=True
        )
        db.session.add(niveau)
        db.session.commit()
        flash(f'Niveau {code_niveau} ajouté avec succès.', 'success')
        return redirect(url_for('main.niveaux_sections'))

    return render_template('formulaire_niveau.html', niveau=None)


@main.route('/niveau/<int:id_niveau>/modifier', methods=['GET', 'POST'])
def modifier_niveau(id_niveau):
    """Modifier un niveau existant."""
    niveau = Niveau.query.get_or_404(id_niveau)
    if request.method == 'POST':
        code_niveau = request.form.get('code_niveau', '').strip()
        cycle = request.form.get('cycle', '').strip()
        specialite = request.form.get('specialite', '').strip()
        annee_etude = request.form.get('annee_etude', '').strip()
        libelle = request.form.get('libelle', '').strip()

        if not all([code_niveau, cycle, specialite, annee_etude, libelle]):
            flash('Tous les champs du niveau sont obligatoires.', 'danger')
            return redirect(url_for('main.modifier_niveau', id_niveau=id_niveau))
        if Niveau.query.filter(
            Niveau.code_niveau == code_niveau,
            Niveau.id_niveau != id_niveau
        ).first():
            flash(f'Le code niveau {code_niveau} existe déjà.', 'danger')
            return redirect(url_for('main.modifier_niveau', id_niveau=id_niveau))
        if Niveau.query.filter(
            Niveau.libelle == libelle,
            Niveau.id_niveau != id_niveau
        ).first():
            flash(f'Le libellé {libelle} existe déjà.', 'danger')
            return redirect(url_for('main.modifier_niveau', id_niveau=id_niveau))

        niveau.code_niveau = code_niveau
        niveau.cycle = cycle
        niveau.specialite = specialite
        niveau.annee_etude = annee_etude
        niveau.libelle = libelle
        niveau.actif = request.form.get('actif') == 'on'
        db.session.commit()
        flash(f'Niveau {code_niveau} modifié avec succès.', 'success')
        return redirect(url_for('main.niveaux_sections'))

    return render_template('formulaire_niveau.html', niveau=niveau)


@main.route('/section/ajouter', methods=['GET', 'POST'])
def ajouter_section():
    """Ajouter une section à un niveau existant."""
    if request.method == 'POST':
        id_niveau = request.form.get('id_niveau', type=int)
        code_section = request.form.get('code_section', '').strip()
        libelle = request.form.get('libelle', '').strip()
        effectif_texte = request.form.get('effectif', '').strip()

        if not id_niveau or not code_section or not libelle:
            flash('Niveau, code et libellé sont obligatoires.', 'danger')
            return redirect(url_for('main.ajouter_section'))
        if Niveau.query.get(id_niveau) is None:
            flash('Le niveau sélectionné est invalide.', 'danger')
            return redirect(url_for('main.ajouter_section'))
        try:
            effectif = int(effectif_texte) if effectif_texte else 0
        except ValueError:
            flash('L\'effectif doit être un nombre entier.', 'danger')
            return redirect(url_for('main.ajouter_section'))
        if effectif < 0:
            flash('L\'effectif ne peut pas être négatif.', 'danger')
            return redirect(url_for('main.ajouter_section'))
        if Section.query.filter_by(
            id_niveau=id_niveau, code_section=code_section
        ).first():
            flash('Ce code de section existe déjà pour ce niveau.', 'danger')
            return redirect(url_for('main.ajouter_section'))

        db.session.add(Section(
            id_niveau=id_niveau,
            code_section=code_section,
            libelle=libelle,
            effectif=effectif,
            actif=True
        ))
        db.session.commit()
        flash(f'Section {code_section} ajoutée avec succès.', 'success')
        return redirect(url_for('main.niveaux_sections'))

    niveaux = Niveau.query.order_by(Niveau.code_niveau).all()
    return render_template(
        'formulaire_section.html', section=None, niveaux=niveaux
    )


@main.route('/section/<int:id_section>/modifier', methods=['GET', 'POST'])
def modifier_section(id_section):
    """Modifier une section existante."""
    section = Section.query.get_or_404(id_section)
    if request.method == 'POST':
        id_niveau = request.form.get('id_niveau', type=int)
        code_section = request.form.get('code_section', '').strip()
        libelle = request.form.get('libelle', '').strip()
        effectif_texte = request.form.get('effectif', '').strip()

        if not id_niveau or not code_section or not libelle:
            flash('Niveau, code et libellé sont obligatoires.', 'danger')
            return redirect(url_for('main.modifier_section', id_section=id_section))
        if Niveau.query.get(id_niveau) is None:
            flash('Le niveau sélectionné est invalide.', 'danger')
            return redirect(url_for('main.modifier_section', id_section=id_section))
        try:
            effectif = int(effectif_texte) if effectif_texte else 0
        except ValueError:
            flash('L\'effectif doit être un nombre entier.', 'danger')
            return redirect(url_for('main.modifier_section', id_section=id_section))
        if effectif < 0:
            flash('L\'effectif ne peut pas être négatif.', 'danger')
            return redirect(url_for('main.modifier_section', id_section=id_section))
        if Section.query.filter(
            Section.id_niveau == id_niveau,
            Section.code_section == code_section,
            Section.id_section != id_section
        ).first():
            flash('Ce code de section existe déjà pour ce niveau.', 'danger')
            return redirect(url_for('main.modifier_section', id_section=id_section))

        section.id_niveau = id_niveau
        section.code_section = code_section
        section.libelle = libelle
        section.effectif = effectif
        section.actif = request.form.get('actif') == 'on'
        db.session.commit()
        flash(f'Section {code_section} modifiée avec succès.', 'success')
        return redirect(url_for('main.niveaux_sections'))

    niveaux = Niveau.query.order_by(Niveau.code_niveau).all()
    return render_template(
        'formulaire_section.html', section=section, niveaux=niveaux
    )


@main.route('/creneaux')
def creneaux():
    """Consulter les créneaux horaires configurés."""
    creneaux_list = Creneau.query.order_by(Creneau.ordre).all()
    return render_template('creneaux.html', creneaux=creneaux_list)


@main.route('/creneau/ajouter', methods=['GET', 'POST'])
def ajouter_creneau():
    """Ajouter un créneau horaire."""
    if request.method == 'POST':
        heure_debut_texte = request.form.get('heure_debut', '').strip()
        heure_fin_texte = request.form.get('heure_fin', '').strip()
        ordre = request.form.get('ordre', type=int)

        if not heure_debut_texte or not heure_fin_texte or ordre is None:
            flash('Heures et ordre sont obligatoires.', 'danger')
            return redirect(url_for('main.ajouter_creneau'))
        try:
            heure_debut = datetime.strptime(heure_debut_texte, '%H:%M').time()
            heure_fin = datetime.strptime(heure_fin_texte, '%H:%M').time()
        except ValueError:
            flash('Les heures saisies sont invalides.', 'danger')
            return redirect(url_for('main.ajouter_creneau'))
        if heure_debut >= heure_fin:
            flash('L\'heure de début doit précéder l\'heure de fin.', 'danger')
            return redirect(url_for('main.ajouter_creneau'))
        if ordre < 1:
            flash('L\'ordre doit être supérieur à zéro.', 'danger')
            return redirect(url_for('main.ajouter_creneau'))
        if Creneau.query.filter_by(ordre=ordre).first():
            flash(f'L\'ordre {ordre} est déjà utilisé.', 'danger')
            return redirect(url_for('main.ajouter_creneau'))

        db.session.add(Creneau(
            heure_debut=heure_debut,
            heure_fin=heure_fin,
            ordre=ordre,
            actif=True
        ))
        db.session.commit()
        flash('Créneau ajouté avec succès.', 'success')
        return redirect(url_for('main.creneaux'))

    return render_template('formulaire_creneau.html', creneau=None)


def verifier_conflits_modification_creneau(creneau, heure_debut, heure_fin):
    """Simule les horaires sans modifier le créneau ni les séances."""
    simulation = Creneau(heure_debut=heure_debut, heure_fin=heure_fin)
    creneaux_chevauchants = filtrer_chevauchements_creneau(
        db.session.query(Creneau.id_creneau), simulation
    )
    seances = Seance.query.filter(
        Seance.id_creneau == creneau.id_creneau,
        Seance.statut != 'ANNULEE'
    ).all()
    for seance in seances:
        candidates = filtrer_semaines_compatibles(
            Seance.query.join(Affectation).filter(
                Seance.id_seance != seance.id_seance,
                Seance.id_annee == seance.id_annee,
                Seance.jour == seance.jour,
                Seance.statut != 'ANNULEE',
                or_(
                    Seance.id_creneau == creneau.id_creneau,
                    Seance.id_creneau.in_(creneaux_chevauchants)
                )
            ), seance.semaine_type
        )
        if (candidates.filter(or_(
                Seance.id_salle == seance.id_salle,
                Affectation.id_professeur == seance.affectation.id_professeur
            )).first() or
                verifier_conflit_etudiants(candidates, seance.affectation)):
            return True
    return False


@main.route('/creneau/<int:id_creneau>/modifier', methods=['GET', 'POST'])
def modifier_creneau(id_creneau):
    """Modifier un créneau horaire."""
    creneau = Creneau.query.get_or_404(id_creneau)
    if request.method == 'POST':
        heure_debut_texte = request.form.get('heure_debut', '').strip()
        heure_fin_texte = request.form.get('heure_fin', '').strip()
        ordre = request.form.get('ordre', type=int)

        if not heure_debut_texte or not heure_fin_texte or ordre is None:
            flash('Heures et ordre sont obligatoires.', 'danger')
            return redirect(url_for('main.modifier_creneau', id_creneau=id_creneau))
        try:
            heure_debut = datetime.strptime(heure_debut_texte, '%H:%M').time()
            heure_fin = datetime.strptime(heure_fin_texte, '%H:%M').time()
        except ValueError:
            flash('Les heures saisies sont invalides.', 'danger')
            return redirect(url_for('main.modifier_creneau', id_creneau=id_creneau))
        if heure_debut >= heure_fin:
            flash('L\'heure de début doit précéder l\'heure de fin.', 'danger')
            return redirect(url_for('main.modifier_creneau', id_creneau=id_creneau))
        if ordre < 1:
            flash('L\'ordre doit être supérieur à zéro.', 'danger')
            return redirect(url_for('main.modifier_creneau', id_creneau=id_creneau))
        if Creneau.query.filter(
            Creneau.ordre == ordre,
            Creneau.id_creneau != id_creneau
        ).first():
            flash(f'L\'ordre {ordre} est déjà utilisé.', 'danger')
            return redirect(url_for('main.modifier_creneau', id_creneau=id_creneau))

        if ((heure_debut, heure_fin) != (creneau.heure_debut, creneau.heure_fin) and
                verifier_conflits_modification_creneau(creneau, heure_debut, heure_fin)):
            flash(
                'Impossible de modifier ce créneau : les nouvelles heures '
                'créeraient un conflit avec une ou plusieurs séances existantes.',
                'danger'
            )
            return redirect(url_for('main.modifier_creneau', id_creneau=id_creneau))

        creneau.heure_debut = heure_debut
        creneau.heure_fin = heure_fin
        creneau.ordre = ordre
        creneau.actif = request.form.get('actif') == 'on'
        db.session.commit()
        flash('Créneau modifié avec succès.', 'success')
        return redirect(url_for('main.creneaux'))

    return render_template('formulaire_creneau.html', creneau=creneau)


@main.route('/annees-universitaires')
def annees_universitaires():
    """Consulter les années universitaires configurées."""
    annees_list = AnneeUniversitaire.query.order_by(
        AnneeUniversitaire.date_debut.desc()
    ).all()
    return render_template('annees_universitaires.html', annees=annees_list)


@main.route('/annees-universitaires/ajouter', methods=['GET', 'POST'])
def ajouter_annee_universitaire():
    """Créer une année universitaire initialement inactive."""
    if request.method == 'POST':
        libelle = request.form.get('libelle', '').strip()
        date_debut_texte = request.form.get('date_debut', '').strip()
        date_fin_texte = request.form.get('date_fin', '').strip()

        if not libelle or not date_debut_texte or not date_fin_texte:
            flash('Tous les champs sont obligatoires.', 'danger')
            return render_template('ajouter_annee_universitaire.html')

        if not re.fullmatch(r'\d{4}-\d{4}', libelle):
            flash('Le libellé doit respecter le format YYYY-YYYY (exemple : 2026-2027).', 'danger')
            return render_template('ajouter_annee_universitaire.html')

        if AnneeUniversitaire.query.filter_by(libelle=libelle).first():
            flash(f'L\'année universitaire {libelle} existe déjà.', 'danger')
            return render_template('ajouter_annee_universitaire.html')

        try:
            date_debut = datetime.strptime(date_debut_texte, '%Y-%m-%d').date()
            date_fin = datetime.strptime(date_fin_texte, '%Y-%m-%d').date()
        except ValueError:
            flash('Les dates saisies sont invalides.', 'danger')
            return render_template('ajouter_annee_universitaire.html')

        if date_debut >= date_fin:
            flash('La date de début doit être strictement antérieure à la date de fin.', 'danger')
            return render_template('ajouter_annee_universitaire.html')

        annee = AnneeUniversitaire(
            libelle=libelle,
            date_debut=date_debut,
            date_fin=date_fin,
            active=False
        )
        db.session.add(annee)
        db.session.commit()
        flash(f'Année universitaire {libelle} créée avec succès. Elle est inactive.', 'success')
        return redirect(url_for('main.annees_universitaires'))

    return render_template('ajouter_annee_universitaire.html')


@main.route('/annees-universitaires/<int:id_annee>/activer', methods=['POST'])
def activer_annee_universitaire(id_annee):
    """Définir une année comme unique année de travail."""
    annee = AnneeUniversitaire.query.get_or_404(id_annee)
    etait_deja_active = bool(annee.active)

    try:
        AnneeUniversitaire.query.update(
            {AnneeUniversitaire.active: False},
            synchronize_session=False
        )
        AnneeUniversitaire.query.filter_by(id_annee=id_annee).update(
            {AnneeUniversitaire.active: True},
            synchronize_session=False
        )
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        flash('Impossible de modifier l\'année de travail.', 'danger')
        return redirect(url_for('main.annees_universitaires'))

    if etait_deja_active:
        flash(f'{annee.libelle} est déjà l\'année de travail.', 'info')
    else:
        flash(f'{annee.libelle} est maintenant l\'année de travail.', 'success')
    return redirect(url_for('main.annees_universitaires'))


def cle_metier_affectation(affectation):
    """Clé métier d'une affectation, hors année universitaire."""
    return (
        affectation.id_professeur,
        affectation.id_matiere,
        affectation.id_section,
        affectation.id_groupe,
        affectation.type_enseignement,
        affectation.semestre,
    )


def analyser_preparation_annee(annee_source, annee_cible):
    """Prépare sans écrire la copie des affectations entre deux années."""
    source = Affectation.query.filter_by(
        id_annee=annee_source.id_annee
    ).order_by(Affectation.id_affectation).all()
    cible = Affectation.query.filter_by(
        id_annee=annee_cible.id_annee
    ).all()

    professeurs_valides = {
        valeur for valeur, in db.session.query(Professeur.id_professeur).all()
    }
    matieres_valides = {
        valeur for valeur, in db.session.query(Matiere.id_matiere).all()
    }
    sections_valides = {
        valeur for valeur, in db.session.query(Section.id_section).all()
    }
    groupes_sections = dict(db.session.query(
        Groupe.id_groupe, Groupe.id_section
    ).all())
    cles_existantes = {cle_metier_affectation(item) for item in cible}

    a_creer = []
    doublons_ignores = 0
    references_invalides = []
    for affectation in source:
        groupe_valide = (
            affectation.id_groupe is None or
            groupes_sections.get(affectation.id_groupe) == affectation.id_section
        )
        references_valides = (
            affectation.id_professeur in professeurs_valides and
            affectation.id_matiere in matieres_valides and
            affectation.id_section in sections_valides and
            groupe_valide
        )
        if not references_valides:
            references_invalides.append(affectation.id_affectation)
            continue

        cle = cle_metier_affectation(affectation)
        if cle in cles_existantes:
            doublons_ignores += 1
            continue
        cles_existantes.add(cle)
        a_creer.append(affectation)

    return {
        'source_total': len(source),
        'cible_total': len(cible),
        'a_creer': a_creer,
        'nombre_a_creer': len(a_creer),
        'doublons_ignores': doublons_ignores,
        'references_invalides': references_invalides,
    }


@main.route('/annees-universitaires/preparer', methods=['GET', 'POST'])
def preparer_annee_universitaire():
    """Prévisualiser puis confirmer la copie contrôlée des affectations."""
    annees = AnneeUniversitaire.query.order_by(
        AnneeUniversitaire.date_debut.desc()
    ).all()
    source_id = request.values.get('source_id', type=int)
    cible_id = request.values.get('cible_id', type=int)
    source = AnneeUniversitaire.query.get(source_id) if source_id else None
    cible = AnneeUniversitaire.query.get(cible_id) if cible_id else None
    analyse = None

    if source_id or cible_id:
        if source is None or cible is None:
            flash('Les années source et cible doivent exister.', 'danger')
        elif source.id_annee == cible.id_annee:
            flash('Les années source et cible doivent être différentes.', 'danger')
        else:
            analyse = analyser_preparation_annee(source, cible)

    if request.method == 'POST':
        if analyse is None:
            flash('La préparation ne peut pas être exécutée.', 'danger')
        elif request.form.get('confirmer') != 'on':
            flash('La confirmation explicite est obligatoire.', 'danger')
        elif analyse['references_invalides']:
            flash(
                'La copie est bloquée par des références invalides dans la source.',
                'danger'
            )
        else:
            for original in analyse['a_creer']:
                db.session.add(Affectation(
                    id_annee=cible.id_annee,
                    id_professeur=original.id_professeur,
                    id_matiere=original.id_matiere,
                    id_section=original.id_section,
                    id_groupe=original.id_groupe,
                    semestre=original.semestre,
                    type_enseignement=original.type_enseignement,
                    nb_seances_semaine=original.nb_seances_semaine,
                    duree_seance_minutes=original.duree_seance_minutes,
                    volume_total_minutes=original.volume_total_minutes,
                    priorite=original.priorite,
                    actif=original.actif,
                ))
            db.session.commit()
            flash(
                f"Préparation terminée : {analyse['nombre_a_creer']} "
                f"affectation(s) créée(s), {analyse['doublons_ignores']} ignorée(s).",
                'success'
            )
            return redirect(url_for(
                'main.affectations', annee_id=cible.id_annee
            ))

    return render_template(
        'preparer_annee_universitaire.html',
        annees=annees,
        source=source,
        cible=cible,
        analyse=analyse,
    )


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

        creneau_demande = Creneau.query.get(id_creneau)
        if creneau_demande is None:
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
        if not affectation.actif:
            flash('❌ Cette affectation est inactive et ne peut pas être planifiée.', 'danger')
            return redirect(url_for('main.ajouter_seance'))

        id_annee = affectation.id_annee
        id_professeur = affectation.id_professeur
        id_matiere = affectation.id_matiere
        id_section = affectation.id_section
        type_enseignement = affectation.type_enseignement

        # 1. Vérifier la salle
        salle_occupee = filtrer_semaines_compatibles(
            filtrer_chevauchements_creneau(Seance.query.join(
                Creneau, Seance.id_creneau == Creneau.id_creneau
            ).filter(
                Seance.id_annee == id_annee,
                Seance.jour == jour,
                Seance.id_salle == id_salle,
                Seance.statut != 'ANNULEE'
            ), creneau_demande), semaine_type
        ).first()
        if salle_occupee:
            salle = Salle.query.get(id_salle)
            conflits.append(f"❌ La salle {salle.nom_salle} est déjà occupée à ce créneau !")

        # 2. Vérifier le professeur
        prof_occupe = filtrer_semaines_compatibles(
            filtrer_chevauchements_creneau(Seance.query.join(
                Affectation, Seance.id_affectation == Affectation.id_affectation
            ).join(
                Creneau, Seance.id_creneau == Creneau.id_creneau
            ).filter(
                Seance.id_annee == id_annee,
                Seance.jour == jour,
                Affectation.id_professeur == id_professeur,
                Seance.statut != 'ANNULEE'
            ), creneau_demande), semaine_type
        ).first()
        if prof_occupe:
            prof = Professeur.query.get(id_professeur)
            conflits.append(f"❌ Le professeur {prof.prenom} {prof.nom} est déjà occupé !")

        # 3. Vérifier les étudiants (section en CM, groupe en TD/TP)
        conflit_etudiants = verifier_conflit_etudiants(filtrer_semaines_compatibles(
            filtrer_chevauchements_creneau(Seance.query.join(
                Affectation, Seance.id_affectation == Affectation.id_affectation
            ).join(
                Creneau, Seance.id_creneau == Creneau.id_creneau
            ).filter(
                Seance.id_annee == id_annee,
                Seance.jour == jour,
                Seance.statut != 'ANNULEE'
            ), creneau_demande), semaine_type), affectation)
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
            db.session.flush()

            # Historique
            historique = Historique(
                utilisateur='Administrateur',
                action='AJOUT',
                type_objet='SEANCE',
                id_objet=seance.id_seance,
                nouvelle_valeur=f"Prof: {id_professeur}, Matière: {id_matiere}, Section: {id_section}, Jour: {jour}, Créneau: {id_creneau}, Salle: {id_salle}",
                date_heure=datetime.utcnow(),
                ip_adresse=request.remote_addr
            )
            db.session.add(historique)
            db.session.commit()

            flash('✅ Séance ajoutée avec succès !', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Erreur : {e}', 'danger')

        return redirect(url_for('main.ajouter_seance'))

    # === GET : Afficher le formulaire ===
    affectations = Affectation.query.filter_by(actif=True).order_by(
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
            filtrer_chevauchements_creneau(Seance.query.join(
                Creneau, Seance.id_creneau == Creneau.id_creneau
            ).filter(
                Seance.id_seance != seance.id_seance,
                Seance.id_annee == seance.id_annee,
                Seance.jour == jour,
                Seance.id_salle == id_salle,
                Seance.statut != 'ANNULEE'
            ), creneau_demande), semaine_type
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
        professeur_occupe = filtrer_semaines_compatibles(
            filtrer_chevauchements_creneau(Seance.query.join(Affectation).join(
                Creneau, Seance.id_creneau == Creneau.id_creneau
            ).filter(
                Seance.id_seance != seance.id_seance,
                Seance.id_annee == seance.id_annee,
                Seance.jour == jour,
                Affectation.id_professeur == affectation.id_professeur,
                Seance.statut != 'ANNULEE'
            ), creneau_demande), semaine_type
        ).first()
        if professeur_occupe:
            conflits.append('Le professeur est déjà occupé à ce créneau.')

        conflit_etudiants = verifier_conflit_etudiants(filtrer_semaines_compatibles(
            filtrer_chevauchements_creneau(Seance.query.join(Affectation).join(
                Creneau, Seance.id_creneau == Creneau.id_creneau
            ).filter(
                Seance.id_seance != seance.id_seance,
                Seance.id_annee == seance.id_annee,
                Seance.jour == jour,
                Seance.statut != 'ANNULEE'
            ), creneau_demande), semaine_type), affectation)
        if conflit_etudiants:
            public = 'La section' if affectation.type_enseignement == 'CM' else 'Le groupe'
            conflits.append(f'{public} est déjà occupé à ce créneau.')

        conflit_capacite = verifier_capacite_salle(affectation, id_salle)
        if conflit_capacite:
            salle, effectif = conflit_capacite
            conflits.append(
                f'Cette salle est trop petite (capacité : {salle.capacite}, effectif : {effectif}).'
            )

        ok, message = verifier_indisponibilite(
            db.session, seance.id_annee, affectation.id_professeur,
            jour, id_creneau
        )
        if not ok:
            conflits.append(f'Indisponibilité : {message}')

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

        try:
            seance.jour = jour
            seance.id_creneau = id_creneau
            seance.id_salle = id_salle
            seance.semaine_type = semaine_type
            nouvelle_valeur = f"Jour: {seance.jour}, Créneau: {seance.id_creneau}, Salle: {seance.id_salle}"
            historique = Historique(
                utilisateur='Administrateur',
                action='MODIFICATION',
                type_objet='SEANCE',
                id_objet=seance.id_seance,
                ancienne_valeur=ancienne_valeur,
                nouvelle_valeur=nouvelle_valeur,
                date_heure=datetime.utcnow(),
                ip_adresse=request.remote_addr
            )
            db.session.add(historique)
            db.session.commit()
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


@main.route('/seance/<int:id_seance>/annuler', methods=['POST'])
def annuler_seance(id_seance):
    """Annule une séance et journalise le changement dans une transaction."""
    refus = administrateur_requis()
    if refus:
        return refus
    seance = Seance.query.get_or_404(id_seance)
    if seance.statut == 'ANNULEE':
        flash('Cette séance est déjà annulée.', 'info')
        return redirect(url_for('main.modifier_seance', id_seance=id_seance))

    try:
        ancien_statut = seance.statut
        seance.statut = 'ANNULEE'
        db.session.add(Historique(
            utilisateur=session.get('admin_username') or 'Administrateur',
            action='ANNULATION',
            type_objet='SEANCE',
            id_objet=id_seance,
            ancienne_valeur=f'Statut: {ancien_statut}',
            nouvelle_valeur='Statut: ANNULEE',
            ip_adresse=request.remote_addr,
        ))
        db.session.commit()
        flash('Séance annulée avec succès. Elle reste conservée.', 'success')
    except Exception:
        db.session.rollback()
        flash('Impossible d’annuler la séance. Aucune modification enregistrée.', 'danger')
    return redirect(url_for('main.modifier_seance', id_seance=id_seance))


@main.route('/seance/<int:id_seance>/supprimer', methods=['POST'])
def supprimer_seance(id_seance):
    """Supprimer une séance existante."""
    seance = Seance.query.get_or_404(id_seance)
    ancienne_valeur = (f"Affectation: {seance.id_affectation}, Jour: {seance.jour}, "
                       f"Créneau: {seance.id_creneau}, Salle: {seance.id_salle}")
    ip_adresse = request.remote_addr
    try:
        historique = Historique(
            utilisateur='Administrateur',
            action='SUPPRESSION',
            type_objet='SEANCE',
            id_objet=id_seance,
            ancienne_valeur=ancienne_valeur,
            date_heure=datetime.utcnow(),
            ip_adresse=ip_adresse
        )
        db.session.add(historique)
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
    annees_list = AnneeUniversitaire.query.order_by(
        AnneeUniversitaire.date_debut.desc()
    ).all()
    annee_id, aucune_annee_active = determiner_annee_consultation()

    def lire_id_filtre(nom):
        valeur = request.args.get(nom, '').strip()
        if not valeur:
            return None
        try:
            return int(valeur)
        except ValueError:
            return -1

    niveau_id = lire_id_filtre('niveau_id')
    section_id = lire_id_filtre('section_id')
    groupe_id = lire_id_filtre('groupe_id')
    professeur_id = lire_id_filtre('professeur_id')
    matiere_id = lire_id_filtre('matiere_id')
    salle_id = lire_id_filtre('salle_id')
    type_enseignement = request.args.get('type_enseignement', '').strip().upper()

    query = (Seance.query
             .join(Affectation, Seance.id_affectation == Affectation.id_affectation)
             .join(Section, Affectation.id_section == Section.id_section)
             .join(Niveau, Section.id_niveau == Niveau.id_niveau)
             .outerjoin(Groupe, Affectation.id_groupe == Groupe.id_groupe)
             .join(Professeur, Affectation.id_professeur == Professeur.id_professeur)
             .join(Matiere, Affectation.id_matiere == Matiere.id_matiere)
             .join(Salle, Seance.id_salle == Salle.id_salle)
             .filter(Seance.statut != 'ANNULEE')
             .options(
                 joinedload(Seance.affectation).joinedload(Affectation.professeur),
                 joinedload(Seance.affectation).joinedload(Affectation.matiere),
                 joinedload(Seance.affectation).joinedload(Affectation.section).joinedload(
                     Section.niveau
                 ).load_only(Niveau.id_niveau, Niveau.libelle),
                 joinedload(Seance.affectation).joinedload(Affectation.groupe),
                 joinedload(Seance.salle),
                 joinedload(Seance.creneau),
             ))
    if aucune_annee_active:
        query = query.filter(Seance.id_seance.is_(None))
    elif annee_id is not None:
        query = query.filter(Seance.id_annee == annee_id)
    if niveau_id is not None:
        query = query.filter(Section.id_niveau == niveau_id)
    if section_id is not None:
        query = query.filter(Affectation.id_section == section_id)
    if groupe_id is not None:
        query = query.filter(Affectation.id_groupe == groupe_id)
    if professeur_id is not None:
        query = query.filter(Affectation.id_professeur == professeur_id)
    if matiere_id is not None:
        query = query.filter(Affectation.id_matiere == matiere_id)
    if salle_id is not None:
        query = query.filter(Seance.id_salle == salle_id)
    if type_enseignement in {'CM', 'TD', 'TP'}:
        query = query.filter(Affectation.type_enseignement == type_enseignement)
    elif type_enseignement:
        query = query.filter(Affectation.type_enseignement == '__INVALIDE__')
    seances = query.all()
    
    planning = []
    for seance in seances:
        affectation = seance.affectation
        if affectation:
            prof = affectation.professeur
            matiere = affectation.matiere
            section = affectation.section
            salle = seance.salle
            creneau = seance.creneau
            
            planning.append({
                'id_seance': seance.id_seance,
                'prof': f"{prof.prenom} {prof.nom}" if prof else "Inconnu",
                'matiere': matiere.nom_matiere if matiere else "Inconnu",
                'niveau': section.niveau.libelle if section and section.niveau else "Inconnu",
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
    vue = request.args.get('vue', 'liste').strip().lower()
    if vue not in {'liste', 'grille'}:
        vue = 'liste'
    jours_grille = list(JOURS.items())
    creneaux_grille = sorted({s.creneau for s in seances if s.creneau}, key=lambda c: (c.heure_debut, c.heure_fin))
    grille = {}
    for item in planning:
        creneau = next((s.creneau for s in seances if s.id_seance == item['id_seance']), None)
        if creneau:
            numero = next((n for n, lib in JOURS.items() if lib == item['jour']), None)
            grille.setdefault(creneau.id_creneau, {}).setdefault(numero, []).append(item)
    
    return render_template(
        'emploi_du_temps.html',
        planning=planning,
        annees=annees_list,
        annee_id=annee_id,
        aucune_annee_active=aucune_annee_active,
        niveaux=db.session.execute(
            db.text(
                'SELECT id_niveau, libelle FROM tbl_niveaux '
                'ORDER BY libelle'
            )
        ).mappings().all(),
        sections=Section.query.order_by(Section.libelle).all(),
        groupes=Groupe.query.order_by(Groupe.nom_groupe).all(),
        professeurs=Professeur.query.order_by(Professeur.nom, Professeur.prenom).all(),
        matieres=Matiere.query.order_by(Matiere.nom_matiere).all(),
        salles=Salle.query.order_by(Salle.nom_salle).all(),
        niveau_id=niveau_id,
        section_id=section_id,
        groupe_id=groupe_id,
        professeur_id=professeur_id,
        matiere_id=matiere_id,
        salle_id=salle_id,
        type_enseignement=type_enseignement,
        vue=vue,
        jours_grille=jours_grille,
        creneaux_grille=creneaux_grille,
        grille=grille,
    )

@main.route('/professeurs')
def professeurs():
    """Lister les professeurs et leur charge pour une année donnée."""
    refus = administrateur_requis()
    if refus:
        return refus
    annees_list = AnneeUniversitaire.query.order_by(
        AnneeUniversitaire.date_debut.desc()
    ).all()
    annee_id, aucune_annee_active = determiner_annee_consultation()
    professeurs_list = Professeur.query.options(
        selectinload(Professeur.affectations).selectinload(Affectation.seances)
    ).order_by(Professeur.nom, Professeur.prenom).all()
    charges = {
        professeur.id_professeur: professeur.calculer_charge(annee_id)
        for professeur in professeurs_list
    }
    return render_template(
        'professeurs.html',
        professeurs=professeurs_list,
        charges=charges,
        annees=annees_list,
        annee_id=annee_id,
        aucune_annee_active=aucune_annee_active,
    )


@main.route('/professeurs/<int:id_professeur>/affectations')
def affectations_professeur(id_professeur):
    """Consulter les affectations d'un professeur."""
    professeur = Professeur.query.get_or_404(id_professeur)
    annees_list = AnneeUniversitaire.query.order_by(
        AnneeUniversitaire.date_debut.desc()
    ).all()
    annee_id, aucune_annee_active = determiner_annee_consultation()
    if annee_id is None:
        affectations_list = []
    else:
        affectations_list = Affectation.query.filter_by(
            id_professeur=id_professeur,
            id_annee=annee_id,
        ).options(
            joinedload(Affectation.annee),
            joinedload(Affectation.matiere),
            joinedload(Affectation.section).joinedload(Section.niveau),
            joinedload(Affectation.groupe),
            selectinload(Affectation.seances),
        ).order_by(
            Affectation.id_section,
            Affectation.semestre,
            Affectation.type_enseignement,
            Affectation.id_groupe
        ).all()
    charge = professeur.calculer_charge(annee_id, affectations_list)

    return render_template(
        'affectations_professeur.html',
        professeur=professeur,
        affectations=affectations_list,
        charge=charge,
        annees=annees_list,
        annee_id=annee_id,
        aucune_annee_active=aucune_annee_active,
    )


@main.route('/professeurs/<int:id_professeur>/emploi-du-temps')
def emploi_du_temps_professeur(id_professeur):
    """Afficher l'emploi du temps individuel, sans modifier les séances."""
    professeur = Professeur.query.get_or_404(id_professeur)
    annees_disponibles = AnneeUniversitaire.query.order_by(
        AnneeUniversitaire.date_debut.desc()
    ).all()
    annee_id, aucune_annee_active = determiner_annee_consultation()

    query = Seance.query.join(Affectation).filter(
        Affectation.id_professeur == id_professeur,
        Seance.statut != 'ANNULEE'
    )
    if aucune_annee_active:
        query = query.filter(Seance.id_seance.is_(None))
    elif annee_id is not None:
        query = query.filter(Seance.id_annee == annee_id)

    seances = query.options(
        joinedload(Seance.affectation).joinedload(Affectation.annee),
        joinedload(Seance.affectation).joinedload(Affectation.matiere),
        joinedload(Seance.affectation).joinedload(Affectation.section).joinedload(
            Section.niveau
        ).load_only(Niveau.id_niveau, Niveau.code_niveau, Niveau.libelle),
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
    annee_selectionnee = (AnneeUniversitaire.query.get(annee_id)
                          if annee_id and annee_id > 0 else None)

    return render_template(
        'emploi_du_temps_professeur.html',
        professeur=professeur,
        seances=seances,
        jours_affiches=jours_affiches,
        creneaux=creneaux,
        annees_disponibles=annees_disponibles,
        annee_id=annee_id,
        annee_selectionnee=annee_selectionnee,
        aucune_annee_active=aucune_annee_active
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
    salles_list = sorted(Salle.query.all(), key=cle_tri_naturel_salle)
    return render_template('salles.html', salles=salles_list)


@main.route('/ajouter_salle', methods=['GET', 'POST'])
def ajouter_salle():
    """Ajouter une salle"""
    if request.method == 'POST':
        code_salle = request.form.get('code_salle', '').strip()
        batiment = request.form.get('batiment', '').strip()
        definition = SALLES_OFFICIELLES.get(code_salle)

        if definition is None:
            flash('❌ Le code doit appartenir au référentiel officiel des salles.', 'danger')
            return redirect(url_for('main.ajouter_salle'))

        nom_salle = definition['nom']
        type_salle = definition['type']

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

    codes_existants = {
        code for code, in db.session.query(Salle.code_salle).all()
    }
    return render_template(
        'ajouter_salle.html',
        salles_officielles=SALLES_OFFICIELLES,
        codes_existants=codes_existants,
    )


@main.route('/salle/<int:id_salle>/modifier', methods=['GET', 'POST'])
def modifier_salle(id_salle):
    """Modifier une salle"""
    salle = Salle.query.get_or_404(id_salle)

    if request.method == 'POST':
        ancienne_valeur = f"Code: {salle.code_salle}, Nom: {salle.nom_salle}, Capacité: {salle.capacite}"

        code_salle = request.form.get('code_salle', '').strip()
        nom_salle = request.form.get('nom_salle', '').strip()
        type_salle = request.form.get('type_salle', '').strip()
        definition = SALLES_OFFICIELLES.get(code_salle)
        salle_initialement_officielle = salle.code_salle in SALLES_OFFICIELLES

        if salle_initialement_officielle and definition is None:
            flash('Une salle officielle doit conserver un code du référentiel.', 'danger')
            return redirect(url_for('main.modifier_salle', id_salle=id_salle))
        if definition:
            nom_salle = definition['nom']
            type_salle = definition['type']
        elif (not code_salle or not nom_salle or
              (type_salle not in TYPES_SALLE and type_salle != salle.type_salle)):
            flash('❌ Code, nom et type de salle valides sont obligatoires !', 'danger')
            return redirect(url_for('main.modifier_salle', id_salle=id_salle))

        code_deja_utilise = Salle.query.filter(
            Salle.code_salle == code_salle,
            Salle.id_salle != salle.id_salle
        ).first()
        if code_deja_utilise:
            flash(f'❌ La salle {code_salle} existe déjà !', 'danger')
            return redirect(url_for('main.modifier_salle', id_salle=id_salle))

        try:
            capacite = convertir_capacite_salle(request.form.get('capacite'))
        except ValueError as exc:
            flash(f'❌ {exc}', 'danger')
            return redirect(url_for('main.modifier_salle', id_salle=id_salle))

        salle.code_salle = code_salle
        salle.nom_salle = nom_salle
        salle.type_salle = type_salle
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

    types_salle = list(TYPES_SALLE)
    if salle.type_salle not in types_salle:
        types_salle.append(salle.type_salle)
    return render_template(
        'modifier_salle.html',
        salle=salle,
        types_salle=types_salle,
        salles_officielles=SALLES_OFFICIELLES,
        codes_existants={
            code for code, in db.session.query(Salle.code_salle).filter(
                Salle.id_salle != salle.id_salle
            ).all()
        },
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
    ).all()

    return render_template('groupes.html', groupes=groupes_list)


@main.route('/ajouter_groupe', methods=['GET', 'POST'])
def ajouter_groupe():
    """Ajouter un groupe"""
    if request.method == 'POST':
        id_section = request.form.get('id_section', type=int)
        code_groupe = request.form.get('code_groupe', '').strip()
        nom_groupe = request.form.get('nom_groupe', '').strip()
        effectif_texte = request.form.get('effectif', '').strip()

        # Vérifications
        if not id_section or not code_groupe or not nom_groupe:
            flash('❌ La section, le code et le nom sont obligatoires !', 'danger')
            return redirect(url_for('main.ajouter_groupe'))
        if Section.query.get(id_section) is None:
            flash('❌ La section sélectionnée est invalide !', 'danger')
            return redirect(url_for('main.ajouter_groupe'))
        try:
            effectif = int(effectif_texte) if effectif_texte else None
        except ValueError:
            flash('❌ L\'effectif doit être un nombre entier !', 'danger')
            return redirect(url_for('main.ajouter_groupe'))
        if effectif is not None and effectif < 0:
            flash('❌ L\'effectif ne peut pas être négatif !', 'danger')
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
            effectif=effectif,
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

        id_section = request.form.get('id_section', type=int)
        code_groupe = request.form.get('code_groupe', '').strip()
        nom_groupe = request.form.get('nom_groupe', '').strip()
        effectif_texte = request.form.get('effectif', '').strip()

        if not id_section or not code_groupe or not nom_groupe:
            flash('❌ La section, le code et le nom sont obligatoires !', 'danger')
            return redirect(url_for('main.modifier_groupe', id_groupe=id_groupe))
        if Section.query.get(id_section) is None:
            flash('❌ La section sélectionnée est invalide !', 'danger')
            return redirect(url_for('main.modifier_groupe', id_groupe=id_groupe))
        try:
            effectif = int(effectif_texte) if effectif_texte else None
        except ValueError:
            flash('❌ L\'effectif doit être un nombre entier !', 'danger')
            return redirect(url_for('main.modifier_groupe', id_groupe=id_groupe))
        if effectif is not None and effectif < 0:
            flash('❌ L\'effectif ne peut pas être négatif !', 'danger')
            return redirect(url_for('main.modifier_groupe', id_groupe=id_groupe))
        if Groupe.query.filter(
            Groupe.id_section == id_section,
            Groupe.code_groupe == code_groupe,
            Groupe.id_groupe != id_groupe
        ).first():
            flash(f'❌ Le groupe {code_groupe} existe déjà dans cette section !', 'danger')
            return redirect(url_for('main.modifier_groupe', id_groupe=id_groupe))

        if (id_section != groupe.id_section and
                Affectation.query.filter_by(id_groupe=id_groupe).first()):
            flash(
                'Impossible de déplacer ce groupe vers une autre section car '
                'il est déjà utilisé dans des affectations.',
                'danger'
            )
            return redirect(url_for('main.modifier_groupe', id_groupe=id_groupe))

        groupe.id_section = id_section
        groupe.code_groupe = code_groupe
        groupe.nom_groupe = nom_groupe
        groupe.effectif = effectif
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

    sections = Section.query.filter(or_(
        Section.actif.is_(True),
        Section.id_section == groupe.id_section
    )).all()
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
    annees = AnneeUniversitaire.query.order_by(
        AnneeUniversitaire.date_debut.desc()
    ).all()
    annee_id, aucune_annee_active = determiner_annee_consultation()
    query = Indisponibilite.query
    if aucune_annee_active:
        query = query.filter(Indisponibilite.id_indisponibilite.is_(None))
    elif annee_id is not None:
        query = query.filter(Indisponibilite.id_annee == annee_id)
    indispos = query.order_by(
        Indisponibilite.jour,
        Indisponibilite.id_creneau
    ).all()
    return render_template(
        'indisponibilites.html',
        indispos=indispos,
        annees=annees,
        annee_id=annee_id,
        aucune_annee_active=aucune_annee_active,
        JOURS=JOURS
    )


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
            return redirect(url_for(
                'main.ajouter_indisponibilite', annee_id=id_annee
            ))

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
            return redirect(url_for('main.indisponibilites', annee_id=id_annee))
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Erreur : {e}', 'danger')

    annees = AnneeUniversitaire.query.order_by(
        AnneeUniversitaire.date_debut.desc()
    ).all()
    annee_id, aucune_annee_active = determiner_annee_consultation()
    professeurs = Professeur.query.filter_by(actif=True).all()
    creneaux = Creneau.query.order_by(Creneau.ordre).all()

    return render_template(
        'ajouter_indisponibilite.html',
        annees=annees,
        annee_id=annee_id,
        aucune_annee_active=aucune_annee_active,
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
    refus = administrateur_requis()
    if refus:
        return refus
    page = request.args.get('page', 1, type=int)
    per_page = 50

    historiques = Historique.query.order_by(
        Historique.date_heure.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)

    return render_template('historique.html', historiques=historiques)
