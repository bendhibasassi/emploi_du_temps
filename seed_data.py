# seed_data.py - Version professionnelle et réexécutable
import os
from datetime import date, time
from sqlalchemy import create_engine
from config import DATABASE_URI
from sqlalchemy.orm import sessionmaker
from app import db
from app.models import (
    AnneeUniversitaire, Niveau, Section, Professeur,
    Matiere, Salle, Creneau, Affectation, Indisponibilite
)

print("🌱 Ajout des données de test...")

# Chemin absolu pour éviter les surprises
engine = create_engine(DATABASE_URI)

# Crée les tables si elles n'existent pas
db.metadata.create_all(engine)

Session = sessionmaker(bind=engine)

# Utilisation d'un contexte pour fermer proprement
with Session() as session:
    try:
        # 1. Année universitaire (vérification d'existence)
        annee = session.query(AnneeUniversitaire).filter_by(libelle="2025-2026").first()
        if annee is None:
            # Désactiver les autres années
            session.query(AnneeUniversitaire).update({"active": False})
            
            annee = AnneeUniversitaire(
                libelle="2025-2026",
                date_debut=date(2025, 9, 1),
                date_fin=date(2026, 6, 30),
                active=True
            )
            session.add(annee)
            session.flush()
            print(f"✅ Année ajoutée : {annee.libelle} (ID: {annee.id_annee})")
        else:
            print(f"ℹ️ Année déjà existante : {annee.libelle} (ID: {annee.id_annee})")

        # 2. Niveau
        niveau = session.query(Niveau).filter_by(code_niveau="L1").first()
        if niveau is None:
            niveau = Niveau(
                code_niveau="L1",
                cycle="LICENCE",
                specialite="Droit",
                annee_etude="1ère année",
                libelle="Licence 1 Droit"
            )
            session.add(niveau)
            session.flush()
            print(f"✅ Niveau ajouté : {niveau.libelle} (ID: {niveau.id_niveau})")
        else:
            print(f"ℹ️ Niveau déjà existant : {niveau.libelle}")

        # 3. Section
        section = session.query(Section).filter_by(
            id_niveau=niveau.id_niveau, 
            code_section="L1-A"
        ).first()
        
        if section is None:
            section = Section(
                id_niveau=niveau.id_niveau,
                code_section="L1-A",
                libelle="Licence 1 Droit - Groupe A",
                effectif=45
            )
            session.add(section)
            session.flush()
            print(f"✅ Section ajoutée : {section.libelle} (ID: {section.id_section})")
        else:
            print(f"ℹ️ Section déjà existante : {section.libelle}")

        # 4. Professeurs
        profs_data = [
            {"nom": "Dupont", "prenom": "Jean", "grade": "Maître de conférences", "email": "jean.dupont@univ.fr"},
            {"nom": "Martin", "prenom": "Sophie", "grade": "Professeur des universités", "email": "sophie.martin@univ.fr"},
        ]
        
        professeurs = {}
        for data in profs_data:
            prof = session.query(Professeur).filter_by(email=data["email"]).first()
            if prof is None:
                prof = Professeur(**data)
                session.add(prof)
                session.flush()
                print(f"✅ Professeur ajouté : {prof.prenom} {prof.nom} (ID: {prof.id_professeur})")
            else:
                print(f"ℹ️ Professeur déjà existant : {prof.prenom} {prof.nom}")
            professeurs[data["email"]] = prof

        prof_jean = professeurs["jean.dupont@univ.fr"]
        prof_sophie = professeurs["sophie.martin@univ.fr"]

        # 5. Matière
        matiere = session.query(Matiere).filter_by(code_matiere="DROIT101").first()
        if matiere is None:
            matiere = Matiere(
                code_matiere="DROIT101",
                nom_matiere="Introduction au droit"
            )
            session.add(matiere)
            session.flush()
            print(f"✅ Matière ajoutée : {matiere.nom_matiere} (ID: {matiere.id_matiere})")
        else:
            print(f"ℹ️ Matière déjà existante : {matiere.nom_matiere}")

        # 6. Salle
        salle = session.query(Salle).filter_by(code_salle="A101").first()
        if salle is None:
            salle = Salle(
                code_salle="A101",
                nom_salle="Amphi A",
                type_salle="AMPHI",
                capacite=100,
                batiment="Bâtiment A"
            )
            session.add(salle)
            session.flush()
            print(f"✅ Salle ajoutée : {salle.nom_salle} (ID: {salle.id_salle})")
        else:
            print(f"ℹ️ Salle déjà existante : {salle.nom_salle}")

        # 7. Créneaux horaires (vérifier s'ils existent déjà)
        creneaux_data = [
            (time(8, 0), time(9, 30), 1),
            (time(9, 30), time(11, 0), 2),
            (time(11, 0), time(12, 30), 3),
            (time(13, 0), time(14, 30), 4),
            (time(14, 30), time(16, 0), 5),
        ]
        
        for debut, fin, ordre in creneaux_data:
            creneau = session.query(Creneau).filter_by(ordre=ordre).first()
            if creneau is None:
                creneau = Creneau(heure_debut=debut, heure_fin=fin, ordre=ordre)
                session.add(creneau)
        session.flush()
        print(f"✅ {len(creneaux_data)} créneaux horaires vérifiés/ajoutés")

        # 8. Affectations (pour les 2 professeurs)
        affectations_crees = 0
        for email, prof in professeurs.items():
            affectation = session.query(Affectation).filter_by(
                id_annee=annee.id_annee,
                id_professeur=prof.id_professeur,
                id_matiere=matiere.id_matiere,
                id_section=section.id_section
            ).first()
            
            if affectation is None:
                type_cours = "CM" if email == "jean.dupont@univ.fr" else "TD"
                affectation = Affectation(
                    id_annee=annee.id_annee,
                    id_professeur=prof.id_professeur,
                    id_matiere=matiere.id_matiere,
                    id_section=section.id_section,
                    semestre=1,
                    type_enseignement=type_cours,
                    nb_seances_semaine=2 if type_cours == "CM" else 1,
                    duree_seance_minutes=90
                )
                session.add(affectation)
                session.flush()
                affectations_crees += 1
                print(f"✅ Affectation créée : {prof.prenom} {prof.nom} -> {matiere.nom_matiere} (ID: {affectation.id_affectation})")
            else:
                print(f"ℹ️ Affectation déjà existante pour {prof.prenom} {prof.nom}")

        # 9. Indisponibilités
        print("\n📋 Ajout des indisponibilités...")

        indispos_data = [
            # Pour Jean Dupont
            (prof_jean.id_professeur, 2, 1, "INTERDIT", "Cours de sport le mardi matin"),
            (prof_jean.id_professeur, 5, 4, "EVITER", "Réunion le vendredi après-midi"),
            # Pour Sophie Martin
            (prof_sophie.id_professeur, 3, 2, "PREFERE", "Disponible le mercredi matin"),
        ]

        for id_prof, jour, id_creneau, type_contrainte, commentaire in indispos_data:
            existing = session.query(Indisponibilite).filter_by(
                id_annee=annee.id_annee,
                id_professeur=id_prof,
                jour=jour,
                id_creneau=id_creneau
            ).first()

            if existing is None:
                indispo = Indisponibilite(
                    id_annee=annee.id_annee,
                    id_professeur=id_prof,
                    jour=jour,
                    id_creneau=id_creneau,
                    type_contrainte=type_contrainte,
                    commentaire=commentaire,
                    actif=True
                )
                session.add(indispo)
                print(f"   ✅ Indisponibilité : {type_contrainte} pour ID {id_prof} - {commentaire}")
            else:
                print(f"   ℹ️ Indisponibilité déjà existante pour ID {id_prof}")

        session.flush()

        # Validation finale
        session.commit()
        
        print("\n" + "="*50)
        print("🎉 DONNÉES DE TEST VÉRIFIÉES/AJOUTÉES !")
        print("="*50)
        print(f"📊 Récapitulatif :")
        print(f"   - Année universitaire : {annee.libelle} ({'active' if annee.active else 'inactive'})")
        print(f"   - Niveau : {niveau.libelle}")
        print(f"   - Section : {section.libelle} ({section.effectif} étudiants)")
        print(f"   - Professeurs : {len(professeurs)} professeurs")
        print(f"   - Matière : {matiere.nom_matiere}")
        print(f"   - Salle : {salle.nom_salle} ({salle.capacite} places)")
        print(f"   - Créneaux : {len(creneaux_data)} horaires")
        print(f"   - Affectations : {affectations_crees} nouvelles, les autres déjà existantes")
        print("="*50)
        
    except Exception as e:
        session.rollback()
        print(f"❌ Erreur : {e}")
        raise
