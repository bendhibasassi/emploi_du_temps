# app/routes.py
import io
import hashlib

import pandas as pd
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from app import db
from app.models import (
    Professeur, Matiere, Section, Salle, Creneau, 
    Affectation, Seance, AnneeUniversitaire, Indisponibilite, Historique
)
from datetime import datetime


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
    """Page d'accueil"""
    annees = AnneeUniversitaire.query.all()
    professeurs = Professeur.query.all()
    matieres = Matiere.query.all()
    sections = Section.query.all()
    salles = Salle.query.all()
    seances = Seance.query.all()
    
    return render_template('index.html',
        annees=annees,
        professeurs=professeurs,
        matieres=matieres,
        sections=sections,
        salles=salles,
        seances=seances
    )

@main.route('/ajouter_seance', methods=['GET', 'POST'])
def ajouter_seance():
    """Ajouter une séance avec création automatique d'affectation"""
    if request.method == 'POST':
        id_annee = request.form.get('id_annee', type=int)
        id_professeur = request.form.get('id_professeur', type=int)
        id_matiere = request.form.get('id_matiere', type=int)
        id_section = request.form.get('id_section', type=int)
        jour = request.form.get('jour', type=int)
        id_creneau = request.form.get('id_creneau', type=int)
        id_salle = request.form.get('id_salle', type=int)
        semaine_type = request.form.get('semaine_type', 'TOUTES')
        type_enseignement = request.form.get('type_enseignement', 'CM')

        # === VÉRIFICATIONS ===
        conflits = []

        # Vérifier que tous les champs sont remplis
        if not all([id_annee, id_professeur, id_matiere, id_section, jour, id_creneau, id_salle]):
            flash('❌ Tous les champs sont obligatoires !', 'danger')
            return redirect(url_for('main.ajouter_seance'))

        # Vérifier si une affectation existe déjà, sinon la créer
        affectation = Affectation.query.filter_by(
            id_annee=id_annee,
            id_professeur=id_professeur,
            id_matiere=id_matiere,
            id_section=id_section
        ).first()

        if affectation is None:
            affectation = Affectation(
                id_annee=id_annee,
                id_professeur=id_professeur,
                id_matiere=id_matiere,
                id_section=id_section,
                semestre=1,
                type_enseignement=type_enseignement,
                nb_seances_semaine=1,
                duree_seance_minutes=90,
                actif=True
            )
            db.session.add(affectation)
            db.session.flush()
            flash('✅ Affectation créée automatiquement !', 'info')

        # 1. Vérifier la salle
        salle_occupee = Seance.query.filter_by(
            id_annee=id_annee,
            jour=jour,
            id_creneau=id_creneau,
            id_salle=id_salle
        ).first()
        if salle_occupee:
            salle = Salle.query.get(id_salle)
            conflits.append(f"❌ La salle {salle.nom_salle} est déjà occupée à ce créneau !")

        # 2. Vérifier le professeur
        prof_occupe = Seance.query.join(
            Affectation, Seance.id_affectation == Affectation.id_affectation
        ).filter(
            Seance.id_annee == id_annee,
            Seance.jour == jour,
            Seance.id_creneau == id_creneau,
            Affectation.id_professeur == id_professeur
        ).first()
        if prof_occupe:
            prof = Professeur.query.get(id_professeur)
            conflits.append(f"❌ Le professeur {prof.prenom} {prof.nom} est déjà occupé !")

        # 3. Vérifier la section
        section_occupee = Seance.query.join(
            Affectation, Seance.id_affectation == Affectation.id_affectation
        ).filter(
            Seance.id_annee == id_annee,
            Seance.jour == jour,
            Seance.id_creneau == id_creneau,
            Affectation.id_section == id_section
        ).first()
        if section_occupee:
            section = Section.query.get(id_section)
            conflits.append(f"❌ La section {section.libelle} est déjà occupée !")

        # 4. Vérifier l'indisponibilité du professeur
        ok, message = verifier_indisponibilite(
            db.session, id_annee, id_professeur, jour, id_creneau
        )
        if not ok:
            conflits.append(f"❌ Indisponibilité : {message}")

        # 5. Vérifier la capacité de la salle
        salle = Salle.query.get(id_salle)
        section = Section.query.get(id_section)
        if salle and section and salle.capacite < section.effectif:
            conflits.append(f"❌ Salle trop petite ! Capacité: {salle.capacite}, Effectif: {section.effectif}")

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
    annees = AnneeUniversitaire.query.all()
    professeurs = Professeur.query.filter_by(actif=True).all()
    matieres = Matiere.query.filter_by(actif=True).all()
    sections = Section.query.filter_by(actif=True).all()
    creneaux = Creneau.query.order_by(Creneau.ordre).all()
    salles = Salle.query.filter_by(actif=True).all()

    return render_template('ajouter_seance.html',
        annees=annees,
        professeurs=professeurs,
        matieres=matieres,
        sections=sections,
        creneaux=creneaux,
        salles=salles,
        JOURS=JOURS
    )


def verifier_conflits_seance(seance, jour, id_creneau, id_salle):
    """Vérifie les conflits d'une séance, en excluant la séance modifiée."""
    conflits = []

    salle_occupee = Seance.query.filter(
        Seance.id_seance != seance.id_seance,
        Seance.id_annee == seance.id_annee,
        Seance.jour == jour,
        Seance.id_creneau == id_creneau,
        Seance.id_salle == id_salle,
        Seance.semaine_type == seance.semaine_type,
        Seance.statut != 'ANNULEE'
    ).first()
    if salle_occupee:
        conflits.append('Cette salle est déjà occupée à ce créneau.')

    affectation = Affectation.query.get(seance.id_affectation)
    if affectation:
        professeur_occupe = Seance.query.join(Affectation).filter(
            Seance.id_seance != seance.id_seance,
            Seance.id_annee == seance.id_annee,
            Seance.jour == jour,
            Seance.id_creneau == id_creneau,
            Seance.semaine_type == seance.semaine_type,
            Affectation.id_professeur == affectation.id_professeur,
            Seance.statut != 'ANNULEE'
        ).first()
        if professeur_occupe:
            conflits.append('Le professeur est déjà occupé à ce créneau.')

        section_occupee = Seance.query.join(Affectation).filter(
            Seance.id_seance != seance.id_seance,
            Seance.id_annee == seance.id_annee,
            Seance.jour == jour,
            Seance.id_creneau == id_creneau,
            Seance.semaine_type == seance.semaine_type,
            Affectation.id_section == affectation.id_section,
            Seance.statut != 'ANNULEE'
        ).first()
        if section_occupee:
            conflits.append('La section est déjà occupée à ce créneau.')

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

        if jour not in JOURS or not Creneau.query.get(id_creneau) or not Salle.query.get(id_salle):
            flash('❌ Jour, créneau ou salle invalide.', 'danger')
            return redirect(url_for('main.modifier_seance', id_seance=id_seance))

        conflits = verifier_conflits_seance(seance, jour, id_creneau, id_salle)
        if conflits:
            flash('❌ ' + ' '.join(conflits), 'danger')
            return redirect(url_for('main.modifier_seance', id_seance=id_seance))

        try:
            seance.jour = jour
            seance.id_creneau = id_creneau
            seance.id_salle = id_salle
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
    salles = Salle.query.order_by(Salle.nom_salle).all()
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
                'jour': JOURS.get(seance.jour, "Inconnu"),
                'debut': creneau.heure_debut.strftime('%H:%M') if creneau else "???",
                'fin': creneau.heure_fin.strftime('%H:%M') if creneau else "???",
                'salle': salle.nom_salle if salle else "Inconnu",
                'capacite': salle.capacite if salle else 0
            })
    
    planning = sorted(planning, key=lambda x: (list(JOURS.values()).index(x['jour']) if x['jour'] in JOURS.values() else 99, x['debut']))
    
    return render_template('emploi_du_temps.html', planning=planning)

@main.route('/professeurs')
def professeurs():
    """Lister les professeurs"""
    professeurs = Professeur.query.all()
    return render_template('professeurs.html', professeurs=professeurs)

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
        ancienne_valeur = (f"Nom: {professeur.nom}, Prénom: {professeur.prenom or ''}, "
                           f"Grade: {professeur.grade or ''}, Email: {professeur.email or ''}")
        professeur.nom = request.form.get('nom', professeur.nom).strip()
        professeur.prenom = request.form.get('prenom', professeur.prenom or '').strip()
        professeur.grade = request.form.get('grade', professeur.grade or '').strip()
        professeur.email = request.form.get('email', professeur.email or '').strip()
        professeur.telephone = request.form.get('telephone', professeur.telephone or '').strip()
        professeur.actif = request.form.get('actif') == 'on'

        try:
            nouvelle_valeur = (f"Nom: {professeur.nom}, Prénom: {professeur.prenom or ''}, "
                              f"Grade: {professeur.grade or ''}, Email: {professeur.email or ''}")
            ajouter_historique(
                utilisateur='Administrateur',
                action='MODIFICATION',
                type_objet='PROFESSEUR',
                id_objet=professeur.id_professeur,
                ancienne_valeur=ancienne_valeur,
                nouvelle_valeur=nouvelle_valeur,
                ip=request.remote_addr
            )
            db.session.commit()
            flash(f'✅ Professeur {professeur.prenom} {professeur.nom} modifié avec succès !', 'success')
            return redirect(url_for('main.professeurs'))
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Erreur lors de la modification : {e}', 'danger')

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
        nom_salle = request.form.get('nom_salle', '').strip()
        type_salle = request.form.get('type_salle', '').strip()
        capacite = request.form.get('capacite', type=int)
        batiment = request.form.get('batiment', '').strip()

        if not code_salle or not nom_salle or not capacite:
            flash('❌ Les champs Code, Nom et Capacité sont obligatoires !', 'danger')
            return redirect(url_for('main.ajouter_salle'))

        if capacite < 1:
            flash('❌ La capacité doit être supérieure à 0 !', 'danger')
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

    return render_template('ajouter_salle.html')


@main.route('/salle/<int:id_salle>/modifier', methods=['GET', 'POST'])
def modifier_salle(id_salle):
    """Modifier une salle"""
    salle = Salle.query.get_or_404(id_salle)

    if request.method == 'POST':
        ancienne_valeur = f"Code: {salle.code_salle}, Nom: {salle.nom_salle}, Capacité: {salle.capacite}"

        salle.code_salle = request.form.get('code_salle', salle.code_salle).strip()
        salle.nom_salle = request.form.get('nom_salle', salle.nom_salle).strip()
        salle.type_salle = request.form.get('type_salle', salle.type_salle).strip()
        salle.capacite = request.form.get('capacite', type=int) or salle.capacite
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

    return render_template('modifier_salle.html', salle=salle)


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


# ============ MATIERES ============

@main.route('/matieres')
def matieres():
    """Liste des matières"""
    matieres_list = Matiere.query.filter_by(actif=True).all()
    return render_template('matieres.html', matieres=matieres_list)


@main.route('/ajouter_matiere', methods=['GET', 'POST'])
def ajouter_matiere():
    """Ajouter une matière"""
    if request.method == 'POST':
        code_matiere = request.form.get('code_matiere', '').strip()
        nom_matiere = request.form.get('nom_matiere', '').strip()

        # Vérifications
        if not code_matiere or not nom_matiere:
            flash('❌ Les champs Code et Nom sont obligatoires !', 'danger')
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
                nouvelle_valeur=f"Code: {code_matiere}, Nom: {nom_matiere}",
                ip=request.remote_addr
            )

            flash(f'✅ Matière {nom_matiere} ajoutée avec succès !', 'success')
            return redirect(url_for('main.matieres'))
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Erreur : {e}', 'danger')

    return render_template('ajouter_matiere.html')


@main.route('/matiere/<int:id_matiere>/modifier', methods=['GET', 'POST'])
def modifier_matiere(id_matiere):
    """Modifier une matière"""
    matiere = Matiere.query.get_or_404(id_matiere)

    if request.method == 'POST':
        ancienne_valeur = f"Code: {matiere.code_matiere}, Nom: {matiere.nom_matiere}"

        matiere.code_matiere = request.form.get('code_matiere', matiere.code_matiere).strip()
        matiere.nom_matiere = request.form.get('nom_matiere', matiere.nom_matiere).strip()
        matiere.actif = request.form.get('actif') == 'on'

        try:
            db.session.commit()

            nouvelle_valeur = f"Code: {matiere.code_matiere}, Nom: {matiere.nom_matiere}"

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

    return render_template('modifier_matiere.html', matiere=matiere)


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
