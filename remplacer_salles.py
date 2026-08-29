# remplacer_salles.py
"""
Script pour remplacer la liste des salles par la liste officielle
(version avec conservation de l'historique)
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models_scripts import Salle
import os

print("=" * 60)
print("🏫 REMPLACEMENT DE LA LISTE DES SALLES")
print("=" * 60)

DB_PATH = os.path.join(os.path.dirname(__file__), "emploi_du_temps.db")
engine = create_engine(f"sqlite:///{DB_PATH}")
Session = sessionmaker(bind=engine)
session = Session()

# === 1. Désactiver les anciennes salles ===
print("\n🗑️ Désactivation des anciennes salles...")
anciennes = session.query(Salle).all()
for salle in anciennes:
    salle.actif = False
    print(f"   ℹ️ Désactivée : {salle.nom_salle}")

session.commit()
print(f"   ✅ {len(anciennes)} salles désactivées")

# === 2. Nouvelle liste des salles ===
salles_data = [
    {'code_salle': 'A1', 'nom_salle': 'مدرج A1', 'type_salle': 'AMPHI', 'capacite': 150, 'batiment': 'Amphithéâtre', 'actif': True},
    {'code_salle': 'A2', 'nom_salle': 'مدرج A2', 'type_salle': 'AMPHI', 'capacite': 150, 'batiment': 'Amphithéâtre', 'actif': True},
    {'code_salle': 'BIO2', 'nom_salle': 'مدرج BIO2', 'type_salle': 'AMPHI', 'capacite': 120, 'batiment': 'Amphithéâtre', 'actif': True},
    {'code_salle': 'DSP23', 'nom_salle': 'DSP23', 'type_salle': 'SALLE', 'capacite': 40, 'batiment': 'DSP', 'actif': True},
    {'code_salle': 'DSP24', 'nom_salle': 'DSP24', 'type_salle': 'SALLE', 'capacite': 40, 'batiment': 'DSP', 'actif': True},
    {'code_salle': 'حقوق2', 'nom_salle': 'حقوق 2', 'type_salle': 'SALLE', 'capacite': 35, 'batiment': 'Droit', 'actif': True},
    {'code_salle': 'حقوق4', 'nom_salle': 'حقوق 4', 'type_salle': 'SALLE', 'capacite': 35, 'batiment': 'Droit', 'actif': True},
    {'code_salle': 'حقوق5', 'nom_salle': 'حقوق 5', 'type_salle': 'SALLE', 'capacite': 30, 'batiment': 'Droit', 'actif': True},
    {'code_salle': 'حقوق6', 'nom_salle': 'حقوق 6', 'type_salle': 'SALLE', 'capacite': 30, 'batiment': 'Droit', 'actif': True},
    {'code_salle': 'حقوق7', 'nom_salle': 'حقوق 7', 'type_salle': 'SALLE', 'capacite': 30, 'batiment': 'Droit', 'actif': True},
]

# === 3. Vérifier et ajouter les nouvelles salles ===
print("\n📥 Ajout des nouvelles salles...")
compteur_ajoutees = 0
compteur_existantes = 0

for data in salles_data:
    existing = session.query(Salle).filter_by(code_salle=data['code_salle']).first()
    if existing:
        # Réactiver si désactivée
        existing.actif = True
        existing.nom_salle = data['nom_salle']
        existing.type_salle = data['type_salle']
        existing.capacite = data['capacite']
        existing.batiment = data['batiment']
        compteur_existantes += 1
        print(f"   🔄 Mise à jour : {data['nom_salle']} ({data['type_salle']}, {data['capacite']} places)")
    else:
        salle = Salle(**data)
        session.add(salle)
        compteur_ajoutees += 1
        print(f"   ✅ Ajoutée : {data['nom_salle']} ({data['type_salle']}, {data['capacite']} places)")

session.commit()

# === 4. Statistiques ===
total = session.query(Salle).count()
actives = session.query(Salle).filter_by(actif=True).count()

print(f"\n📊 Résumé :")
print(f"   Nouvelles salles ajoutées : {compteur_ajoutees}")
print(f"   Salles mises à jour : {compteur_existantes}")
print(f"   Total salles dans la base : {total}")
print(f"   Salles actives : {actives}")
print("=" * 60)
session.close()
