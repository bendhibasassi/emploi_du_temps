# app/routes.py
import io

import pandas as pd
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from app import db
from app.models import (
    Professeur, Matiere, Section, Salle, Creneau, 
    Affectation, Seance, AnneeUniversitaire
)
from datetime import datetime

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
    """Ajouter une séance avec vérification des conflits"""
    if request.method == 'POST':
        id_annee = request.form.get('id_annee', type=int)
        id_affectation = request.form.get('id_affectation', type=int)
        jour = request.form.get('jour', type=int)
        id_creneau = request.form.get('id_creneau', type=int)
        id_salle = request.form.get('id_salle', type=int)
        semaine_type = request.form.get('semaine_type', 'TOUTES')
        
        # Vérification des conflits (simplifiée)
        conflits = []
        
        # Vérifier la salle
        seance_salle = Seance.query.filter_by(
            id_annee=id_annee,
            jour=jour,
            id_creneau=id_creneau,
            id_salle=id_salle
        ).first()
        if seance_salle:
            conflits.append("❌ Cette salle est déjà occupée à ce créneau !")
        
        # Vérifier le professeur via l'affectation
        affectation = Affectation.query.get(id_affectation)
        if affectation:
            seance_prof = Seance.query.join(
                Affectation, Seance.id_affectation == Affectation.id_affectation
            ).filter(
                Seance.id_annee == id_annee,
                Seance.jour == jour,
                Seance.id_creneau == id_creneau,
                Affectation.id_professeur == affectation.id_professeur
            ).first()
            if seance_prof:
                prof = Professeur.query.get(affectation.id_professeur)
                conflits.append(f"❌ Le professeur {prof.prenom} {prof.nom} est déjà occupé !")
        
        if conflits:
            flash('\n'.join(conflits), 'danger')
        else:
            # Ajout de la séance
            seance = Seance(
                id_annee=id_annee,
                id_affectation=id_affectation,
                jour=jour,
                id_creneau=id_creneau,
                id_salle=id_salle,
                semaine_type=semaine_type,
                statut="PROPOSEE"
            )
            db.session.add(seance)
            db.session.commit()
            flash('✅ Séance ajoutée avec succès !', 'success')
        
        return redirect(url_for('main.ajouter_seance'))
    
    # GET : Afficher le formulaire
    annees = AnneeUniversitaire.query.all()
    affectations = Affectation.query.all()
    creneaux = Creneau.query.order_by(Creneau.ordre).all()
    salles = Salle.query.all()
    
    # Récupérer les détails pour l'affichage
    affectations_detail = []
    for aff in affectations:
        prof = Professeur.query.get(aff.id_professeur)
        matiere = Matiere.query.get(aff.id_matiere)
        section = Section.query.get(aff.id_section)
        affectations_detail.append({
            'id': aff.id_affectation,
            'prof': f"{prof.prenom} {prof.nom}" if prof else "Inconnu",
            'matiere': matiere.nom_matiere if matiere else "Inconnu",
            'section': section.libelle if section else "Inconnu"
        })
    
    return render_template('ajouter_seance.html',
        annees=annees,
        affectations=affectations_detail,
        creneaux=creneaux,
        salles=salles,
        JOURS=JOURS
    )

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
        professeur.nom = request.form.get('nom', professeur.nom).strip()
        professeur.prenom = request.form.get('prenom', professeur.prenom or '').strip()
        professeur.grade = request.form.get('grade', professeur.grade or '').strip()
        professeur.email = request.form.get('email', professeur.email or '').strip()
        professeur.telephone = request.form.get('telephone', professeur.telephone or '').strip()
        professeur.actif = request.form.get('actif') == 'on'

        try:
            db.session.commit()
            flash(f'✅ Professeur {professeur.prenom} {professeur.nom} modifié avec succès !', 'success')
            return redirect(url_for('main.professeurs'))
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Erreur lors de la modification : {e}', 'danger')

    return render_template('modifier_professeur.html', professeur=professeur)


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