# verifier_libelles.py

from sqlalchemy import create_engine
from config import DATABASE_URI
from sqlalchemy.orm import sessionmaker
from app.models import Niveau, Section, Matiere, Professeur
import os

print("=" * 70)
print("🔍 VÉRIFICATION DES LIBELLÉS EXACTS")
print("=" * 70)

engine = create_engine(DATABASE_URI)
Session = sessionmaker(bind=engine)
session = Session()

print("\n📋 SECTIONS :")
for s in session.query(Section).all():
    niveau = session.query(Niveau).filter_by(id_niveau=s.id_niveau).first()
    print(f"   {s.libelle} (Niveau: {niveau.code_niveau if niveau else '?'})")

print("\n📋 MATIÈRES :")
for m in session.query(Matiere).limit(20).all():
    print(f"   {m.nom_matiere}")

print("\n📋 PROFESSEURS (extrait) :")
for p in session.query(Professeur).limit(20).all():
    print(f"   {p.nom}")

session.close()
