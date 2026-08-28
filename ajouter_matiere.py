# ajouter_matiere.py
from models_scripts import Matiere, Affectation, AnneeUniversitaire, Section, Professeur
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

print("📚 Ajout d'une nouvelle matière...")

engine = create_engine("sqlite:///emploi_du_temps.db")
Session = sessionmaker(bind=engine)

with Session() as session:
    # Nouvelle matière
    matiere = Matiere(
        code_matiere="DROIT102",
        nom_matiere="Droit des contrats"
    )
    session.add(matiere)
    session.commit()
    print(f"✅ Matière ajoutée : {matiere.nom_matiere} (ID: {matiere.id_matiere})")