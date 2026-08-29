# importer_sections.py
"""
Script pour importer les sections (L3 A/B + Masters section unique)
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models_scripts import Section, Niveau
import os

print("=" * 70)
print("📋 IMPORT DES SECTIONS")
print("=" * 70)

DB_PATH = os.path.join(os.path.dirname(__file__), "emploi_du_temps.db")
engine = create_engine(f"sqlite:///{DB_PATH}")
Session = sessionmaker(bind=engine)
session = Session()

# === 1. Récupérer les niveaux ===
print("\n🔍 Récupération des niveaux...")
niveaux = {}
for niveau in session.query(Niveau).all():
    niveaux[niveau.code_niveau] = niveau
    print(f"   ✅ {niveau.code_niveau} : {niveau.libelle} (ID: {niveau.id_niveau})")

# === 2. Définition des sections ===
sections_data = [
    # L3 Droit privé (ID_Niveau = 1)
    {'niveau_code': 'L3', 'code': 'A', 'libelle': 'الفصيلة أ – L3 Droit privé', 'effectif': 45},
    {'niveau_code': 'L3', 'code': 'B', 'libelle': 'الفصيلة ب – L3 Droit privé', 'effectif': 40},

    # L3 Droit public (ID_Niveau = 2)
    {'niveau_code': 'L3', 'code': 'A', 'libelle': 'الفصيلة أ – L3 Droit public', 'effectif': 50},
    {'niveau_code': 'L3', 'code': 'B', 'libelle': 'الفصيلة ب – L3 Droit public', 'effectif': 45},

    # M1 Droit pénal (ID_Niveau = 3)
    {'niveau_code': 'M1', 'code': 'U', 'libelle': 'Section unique – M1 Droit pénal', 'effectif': 25},

    # M2 Droit pénal (ID_Niveau = 4)
    {'niveau_code': 'M2', 'code': 'U', 'libelle': 'Section unique – M2 Droit pénal', 'effectif': 20},

    # M1 Droit international (ID_Niveau = 5)
    {'niveau_code': 'M1', 'code': 'U', 'libelle': 'Section unique – M1 Droit international', 'effectif': 25},

    # M2 Droit international (ID_Niveau = 6)
    {'niveau_code': 'M2', 'code': 'U', 'libelle': 'Section unique – M2 Droit international', 'effectif': 20},

    # M1 Gouvernance (ID_Niveau = 7)
    {'niveau_code': 'M1', 'code': 'U', 'libelle': 'Section unique – M1 Gouvernance', 'effectif': 20},

    # M2 Gouvernance (ID_Niveau = 8)
    {'niveau_code': 'M2', 'code': 'U', 'libelle': 'Section unique – M2 Gouvernance', 'effectif': 15},

    # M1 Droit des affaires (ID_Niveau = 9)
    {'niveau_code': 'M1', 'code': 'U', 'libelle': 'Section unique – M1 Droit des affaires', 'effectif': 25},

    # M2 Droit des affaires (ID_Niveau = 10)
    {'niveau_code': 'M2', 'code': 'U', 'libelle': 'Section unique – M2 Droit des affaires', 'effectif': 20},

    # M1 Droit immobilier (ID_Niveau = 11)
    {'niveau_code': 'M1', 'code': 'U', 'libelle': 'Section unique – M1 Droit immobilier', 'effectif': 20},

    # M2 Droit immobilier (ID_Niveau = 12)
    {'niveau_code': 'M2', 'code': 'U', 'libelle': 'Section unique – M2 Droit immobilier', 'effectif': 15},

    # M1 Droit des contrats (ID_Niveau = 13)
    {'niveau_code': 'M1', 'code': 'U', 'libelle': 'Section unique – M1 Droit des contrats', 'effectif': 20},

    # M2 Droit des contrats (ID_Niveau = 14)
    {'niveau_code': 'M2', 'code': 'U', 'libelle': 'Section unique – M2 Droit des contrats', 'effectif': 15},

    # M1 Droit administratif (ID_Niveau = 15)
    {'niveau_code': 'M1', 'code': 'U', 'libelle': 'Section unique – M1 Droit administratif', 'effectif': 25},
]

# === 3. Import des sections ===
print("\n📥 Import des sections...")
compteur_ajoutees = 0
compteur_existantes = 0
compteur_erreurs = 0

for data in sections_data:
    niveau = niveaux.get(data['niveau_code'])
    if not niveau:
        print(f"   ⚠️ Niveau {data['niveau_code']} non trouvé pour {data['libelle']}")
        compteur_erreurs += 1
        continue

    # Vérifier si la section existe déjà
    existing = session.query(Section).filter_by(
        id_niveau=niveau.id_niveau,
        code_section=data['code']
    ).first()

    if existing:
        print(f"   ℹ️ Déjà existante : {data['code']} - {data['libelle']}")
        compteur_existantes += 1
        continue

    # Créer la section
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

# === 4. Statistiques ===
total = session.query(Section).count()
print(f"\n📊 Résumé :")
print(f"   Sections ajoutées : {compteur_ajoutees}")
print(f"   Sections déjà existantes : {compteur_existantes}")
print(f"   Erreurs : {compteur_erreurs}")
print(f"   Total sections dans la base : {total}")
print("=" * 70)
session.close()
