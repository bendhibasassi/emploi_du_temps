# importer_sections_complet.py
"""
Script pour importer toutes les sections avec les nouveaux niveaux
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models_scripts import Section, Niveau
import os

print("=" * 70)
print("📋 IMPORT COMPLET DES SECTIONS")
print("=" * 70)

DB_PATH = os.path.join(os.path.dirname(__file__), "emploi_du_temps.db")
engine = create_engine(f"sqlite:///{DB_PATH}")
Session = sessionmaker(bind=engine)
session = Session()

# === Récupérer les niveaux ===
print("\n🔍 Récupération des niveaux...")
niveaux = {}
for niveau in session.query(Niveau).all():
    niveaux[niveau.code_niveau] = niveau
    print(f"   ✅ {niveau.code_niveau} : {niveau.libelle}")

# === Définition des sections ===
sections_data = [
    # L3
    {'niveau_code': 'L3-PRIV', 'code': 'A', 'libelle': 'Section A – L3 Droit privé', 'effectif': 45},
    {'niveau_code': 'L3-PRIV', 'code': 'B', 'libelle': 'Section B – L3 Droit privé', 'effectif': 40},
    {'niveau_code': 'L3-PUB', 'code': 'A', 'libelle': 'Section A – L3 Droit public', 'effectif': 50},
    {'niveau_code': 'L3-PUB', 'code': 'B', 'libelle': 'Section B – L3 Droit public', 'effectif': 45},

    # M1 Droit pénal
    {'niveau_code': 'M1-PEN', 'code': 'U', 'libelle': 'Section unique – M1 Droit pénal', 'effectif': 25},
    {'niveau_code': 'M2-PEN', 'code': 'U', 'libelle': 'Section unique – M2 Droit pénal', 'effectif': 20},

    # M1 Droit international
    {'niveau_code': 'M1-INT', 'code': 'U', 'libelle': 'Section unique – M1 Droit international', 'effectif': 25},
    {'niveau_code': 'M2-INT', 'code': 'U', 'libelle': 'Section unique – M2 Droit international', 'effectif': 20},

    # M1 Gouvernance
    {'niveau_code': 'M1-GOUV', 'code': 'U', 'libelle': 'Section unique – M1 Gouvernance', 'effectif': 20},
    {'niveau_code': 'M2-GOUV', 'code': 'U', 'libelle': 'Section unique – M2 Gouvernance', 'effectif': 15},

    # M1 Droit des affaires
    {'niveau_code': 'M1-AFF', 'code': 'U', 'libelle': 'Section unique – M1 Droit des affaires', 'effectif': 25},
    {'niveau_code': 'M2-AFF', 'code': 'U', 'libelle': 'Section unique – M2 Droit des affaires', 'effectif': 20},

    # M1 Droit immobilier
    {'niveau_code': 'M1-IMMO', 'code': 'U', 'libelle': 'Section unique – M1 Droit immobilier', 'effectif': 20},
    {'niveau_code': 'M2-IMMO', 'code': 'U', 'libelle': 'Section unique – M2 Droit immobilier', 'effectif': 15},

    # M1 Droit des contrats
    {'niveau_code': 'M1-CONT', 'code': 'U', 'libelle': 'Section unique – M1 Droit des contrats', 'effectif': 20},
    {'niveau_code': 'M2-CONT', 'code': 'U', 'libelle': 'Section unique – M2 Droit des contrats', 'effectif': 15},

    # M1 Droit administratif
    {'niveau_code': 'M1-ADMIN', 'code': 'U', 'libelle': 'Section unique – M1 Droit administratif', 'effectif': 25},
]

# === Import ===
print("\n📥 Import des sections...")
compteur_ajoutees = 0
compteur_existantes = 0

for data in sections_data:
    niveau = niveaux.get(data['niveau_code'])
    if not niveau:
        print(f"   ⚠️ Niveau {data['niveau_code']} non trouvé pour {data['libelle']}")
        continue

    existing = session.query(Section).filter_by(
        id_niveau=niveau.id_niveau,
        code_section=data['code']
    ).first()

    if existing:
        print(f"   ℹ️ Déjà existante : {data['code']} - {data['libelle']}")
        compteur_existantes += 1
        continue

    section = Section(
        id_niveau=niveau.id_niveau,
        code_section=data['code'],
        libelle=data['libelle'],
        effectif=data['effectif'],
        actif=True
    )
    session.add(section)
    compteur_ajoutees += 1
    print(f"   ✅ Ajoutée : {data['code']} - {data['libelle']} ({data['effectif']} étudiants)")

session.commit()

# === Statistiques ===
total = session.query(Section).count()
print(f"\n📊 Résumé :")
print(f"   Sections ajoutées : {compteur_ajoutees}")
print(f"   Sections déjà existantes : {compteur_existantes}")
print(f"   Total sections : {total}")
print("=" * 70)
session.close()
