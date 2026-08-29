# ajouter_matiere.py
from app.models import Matiere, Affectation, AnneeUniversitaire, Section, Professeur
from sqlalchemy import create_engine
from config import DATABASE_URI
from sqlalchemy.orm import sessionmaker

print("📚 Ajout d'une nouvelle matière...")

engine = create_engine(DATABASE_URI)
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
