# chercher_matiere.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models_scripts import Matiere
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "emploi_du_temps.db")
engine = create_engine(f"sqlite:///{DB_PATH}")
Session = sessionmaker(bind=engine)
session = Session()

# Chercher les matières contenant "لغة" ou "الإنجليزية"
resultats = session.query(Matiere).filter(
    Matiere.nom_matiere.contains('لغة')
).all()

if resultats:
    print("📋 Matières contenant 'لغة' :")
    for m in resultats:
        print(f"   - {m.nom_matiere} (Niveau: {m.id_niveau})")
else:
    print("❌ Aucune matière contenant 'لغة' trouvée")

session.close()
