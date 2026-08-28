# corriger_permissions_professeurs.py
"""
Correction des permissions pour les professeurs permanents et vacataires
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models_scripts import Professeur
import os

print("=" * 60)
print("🔧 CORRECTION DES PERMISSIONS DES PROFESSEURS")
print("=" * 60)

DB_PATH = os.path.join(os.path.dirname(__file__), "emploi_du_temps.db")
engine = create_engine(f"sqlite:///{DB_PATH}")
Session = sessionmaker(bind=engine)
session = Session()

# === 1. Récupérer tous les professeurs ===
total = session.query(Professeur).count()
print(f"\n📊 Total professeurs dans la base : {total}")

# === 2. Mettre à jour les permanents ===
print("\n🔄 Mise à jour des professeurs permanents...")
permanents = session.query(Professeur).filter_by(statut='Permanent').all()

compteur_permanents = 0
for prof in permanents:
    prof.peut_cm = True
    prof.peut_td = True
    prof.peut_tp = True
    compteur_permanents += 1
    print(f"   ✅ {prof.nom} → CM: Oui, TD: Oui, TP: Oui")

print(f"   {compteur_permanents} permanents mis à jour")

# === 3. Mettre à jour les vacataires ===
print("\n🔄 Mise à jour des vacataires...")
vacataires = session.query(Professeur).filter_by(statut='Vacataire').all()

compteur_vacataires = 0
for prof in vacataires:
    prof.peut_cm = False
    prof.peut_td = True
    prof.peut_tp = False
    compteur_vacataires += 1
    print(f"   ✅ {prof.nom} → CM: Non, TD: Oui, TP: Non")

print(f"   {compteur_vacataires} vacataires mis à jour")

# === 4. Valider les modifications ===
session.commit()

# === 5. Statistiques finales ===
print("\n📊 STATISTIQUES FINALES :")
print("-" * 40)

perm_total = session.query(Professeur).filter_by(statut='Permanent').count()
vac_total = session.query(Professeur).filter_by(statut='Vacataire').count()

print(f"   Total : {total}")
print(f"   Permanents : {perm_total} (CM + TD + TP)")
print(f"   Vacataires : {vac_total} (TD uniquement)")

# Vérifier les permissions
print("\n🔍 VÉRIFICATION DES PERMISSIONS :")
perm_cm = session.query(Professeur).filter(
    Professeur.statut == 'Permanent',
    Professeur.peut_cm == True
).count()

perm_td = session.query(Professeur).filter(
    Professeur.statut == 'Permanent',
    Professeur.peut_td == True
).count()

vac_td = session.query(Professeur).filter(
    Professeur.statut == 'Vacataire',
    Professeur.peut_td == True
).count()

print(f"   Permanents avec CM : {perm_cm}")
print(f"   Permanents avec TD : {perm_td}")
print(f"   Vacataires avec TD : {vac_td}")

print("\n" + "=" * 60)
session.close()
