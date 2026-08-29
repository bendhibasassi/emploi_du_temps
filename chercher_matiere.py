# chercher_matiere.py

from sqlalchemy import create_engine
from config import DATABASE_URI
from sqlalchemy.orm import sessionmaker
from app.models import Matiere
import os

engine = create_engine(DATABASE_URI)
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
