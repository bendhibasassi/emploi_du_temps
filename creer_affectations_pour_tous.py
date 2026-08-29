# creer_affectations_pour_tous.py
import os

from sqlalchemy import create_engine
from config import DATABASE_URI
from sqlalchemy.orm import sessionmaker

from app.models import Professeur, Matiere, Section, Affectation, AnneeUniversitaire

print("📋 Création des affectations pour tous les professeurs...")

engine = create_engine(DATABASE_URI)
Session = sessionmaker(bind=engine)

with Session() as session:
    # Récupérer l'année active
    annee = session.query(AnneeUniversitaire).filter_by(active=True).first()
    if annee is None:
        print("❌ Aucune année active trouvée !")
        raise SystemExit(1)

    # Récupérer la première matière et section
    matiere = session.query(Matiere).first()
    section = session.query(Section).first()

    if matiere is None or section is None:
        print("❌ Matière ou section manquante !")
        raise SystemExit(1)

    professeurs = session.query(Professeur).filter_by(actif=True).all()
    print(f"👨‍🏫 {len(professeurs)} professeurs trouvés")

    compteur = 0
    for prof in professeurs:
        # Vérifier si une affectation existe déjà
        affectation = session.query(Affectation).filter_by(
            id_annee=annee.id_annee,
            id_professeur=prof.id_professeur,
            id_matiere=matiere.id_matiere,
            id_section=section.id_section
        ).first()

        if affectation is None:
            affectation = Affectation(
                id_annee=annee.id_annee,
                id_professeur=prof.id_professeur,
                id_matiere=matiere.id_matiere,
                id_section=section.id_section,
                semestre=1,
                type_enseignement="CM",
                nb_seances_semaine=1,
                duree_seance_minutes=90,
                actif=True
            )
            session.add(affectation)
            compteur += 1
            print(f"   ✅ Affectation créée pour {prof.prenom} {prof.nom}")

    session.commit()

print(f"✅ {compteur} affectations créées avec succès !")
