# test_db.py
from sqlalchemy import create_engine
from config import DATABASE_URI
from sqlalchemy.orm import sessionmaker
from app.models import Professeur, Matiere, Salle, Seance, Affectation, Section, Creneau, AnneeUniversitaire

engine = create_engine(DATABASE_URI)
Session = sessionmaker(bind=engine)
session = Session()

print("=" * 50)
print("📊 VÉRIFICATION DE LA BASE DE DONNÉES")
print("=" * 50)

prof_count = session.query(Professeur).count()
matiere_count = session.query(Matiere).count()
salle_count = session.query(Salle).count()
seance_count = session.query(Seance).count()
affectation_count = session.query(Affectation).count()
section_count = session.query(Section).count()
annee_count = session.query(AnneeUniversitaire).count()

print(f"👨‍🏫 Professeurs : {prof_count}")
print(f"📚 Matières : {matiere_count}")
print(f"🏫 Salles : {salle_count}")
print(f"📅 Séances : {seance_count}")
print(f"📋 Affectations : {affectation_count}")
print(f"🎓 Sections : {section_count}")
print(f"📆 Années : {annee_count}")
print("=" * 50)

if prof_count == 0:
    print("⚠️ La base est VIDE !")
    print("   Exécute : python seed_data.py")
    print("   Puis : python ajouter_seance.py")
else:
    print("✅ La base contient des données !")
    print("   👉 Le problème vient probablement des modèles Flask.")
    print("   Regarde dans app/models.py et app/__init__.py")
