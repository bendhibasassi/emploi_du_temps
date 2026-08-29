# mettre_a_jour_professeurs.py

from sqlalchemy import create_engine
from config import DATABASE_URI
from sqlalchemy.orm import sessionmaker
from app.models import Professeur
import os

print("🔄 Mise à jour des professeurs avec leurs statuts...")

engine = create_engine(DATABASE_URI)
Session = sessionmaker(bind=engine)
session = Session()

# Statut par défaut pour les professeurs existants
# Si le nom contient "Vacataire" ou "Vac.", on le considère comme vacataire
vacataires = session.query(Professeur).filter(
    (Professeur.nom.contains('Vacataire')) |
    (Professeur.nom.contains('Vac.')) |
    (Professeur.grade == 'Vacataire')
).all()

for prof in vacataires:
    prof.statut = 'Vacataire'
    prof.peut_cm = False
    prof.peut_td = True
    prof.peut_tp = False
    print(f"   ✅ {prof.nom} → Vacataire (TD uniquement)")

# Les autres sont des permanents
permanents = session.query(Professeur).filter(
    (Professeur.statut.is_(None)) |
    (Professeur.statut == '')
).all()

for prof in permanents:
    # Exclure les vacataires déjà traités
    if prof not in vacataires:
        prof.statut = 'Permanent'
        prof.peut_cm = True
        prof.peut_td = True
        prof.peut_tp = True
        print(f"   ✅ {prof.nom} → Permanent (CM + TD + TP)")

session.commit()

# Statistiques
total = session.query(Professeur).count()
vac_count = session.query(Professeur).filter_by(statut='Vacataire').count()
perm_count = session.query(Professeur).filter_by(statut='Permanent').count()

print(f"\n📊 Statistiques :")
print(f"   Total professeurs : {total}")
print(f"   Permanents : {perm_count}")
print(f"   Vacataires : {vac_count}")
print("=" * 40)
session.close()
