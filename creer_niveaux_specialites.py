# creer_niveaux_specialites.py
"""
Script pour créer des niveaux spécifiques par spécialité
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models_scripts import Niveau
import os

print("=" * 70)
print("📚 CRÉATION DES NIVEAUX PAR SPÉCIALITÉ")
print("=" * 70)

DB_PATH = os.path.join(os.path.dirname(__file__), "emploi_du_temps.db")
engine = create_engine(f"sqlite:///{DB_PATH}")
Session = sessionmaker(bind=engine)
session = Session()

# === Niveaux à créer ===
niveaux_data = [
    # L3
    {'code': 'L3-PRIV', 'libelle': 'L3 Droit privé', 'cycle': 'LICENCE', 'specialite': 'Droit privé', 'annee_etude': '3ème année'},
    {'code': 'L3-PUB', 'libelle': 'L3 Droit public', 'cycle': 'LICENCE', 'specialite': 'Droit public', 'annee_etude': '3ème année'},

    # Masters Droit pénal
    {'code': 'M1-PEN', 'libelle': 'M1 Droit pénal', 'cycle': 'MASTER', 'specialite': 'Droit pénal', 'annee_etude': '1ère année Master'},
    {'code': 'M2-PEN', 'libelle': 'M2 Droit pénal', 'cycle': 'MASTER', 'specialite': 'Droit pénal', 'annee_etude': '2ème année Master'},

    # Masters Droit international
    {'code': 'M1-INT', 'libelle': 'M1 Droit international', 'cycle': 'MASTER', 'specialite': 'Droit international', 'annee_etude': '1ère année Master'},
    {'code': 'M2-INT', 'libelle': 'M2 Droit international', 'cycle': 'MASTER', 'specialite': 'Droit international', 'annee_etude': '2ème année Master'},

    # Masters Gouvernance
    {'code': 'M1-GOUV', 'libelle': 'M1 Gouvernance', 'cycle': 'MASTER', 'specialite': 'Gouvernance', 'annee_etude': '1ère année Master'},
    {'code': 'M2-GOUV', 'libelle': 'M2 Gouvernance', 'cycle': 'MASTER', 'specialite': 'Gouvernance', 'annee_etude': '2ème année Master'},

    # Masters Droit des affaires
    {'code': 'M1-AFF', 'libelle': 'M1 Droit des affaires', 'cycle': 'MASTER', 'specialite': 'Droit des affaires', 'annee_etude': '1ère année Master'},
    {'code': 'M2-AFF', 'libelle': 'M2 Droit des affaires', 'cycle': 'MASTER', 'specialite': 'Droit des affaires', 'annee_etude': '2ème année Master'},

    # Masters Droit immobilier
    {'code': 'M1-IMMO', 'libelle': 'M1 Droit immobilier', 'cycle': 'MASTER', 'specialite': 'Droit immobilier', 'annee_etude': '1ère année Master'},
    {'code': 'M2-IMMO', 'libelle': 'M2 Droit immobilier', 'cycle': 'MASTER', 'specialite': 'Droit immobilier', 'annee_etude': '2ème année Master'},

    # Masters Droit des contrats
    {'code': 'M1-CONT', 'libelle': 'M1 Droit des contrats', 'cycle': 'MASTER', 'specialite': 'Droit des contrats', 'annee_etude': '1ère année Master'},
    {'code': 'M2-CONT', 'libelle': 'M2 Droit des contrats', 'cycle': 'MASTER', 'specialite': 'Droit des contrats', 'annee_etude': '2ème année Master'},

    # Masters Droit administratif
    {'code': 'M1-ADMIN', 'libelle': 'M1 Droit administratif', 'cycle': 'MASTER', 'specialite': 'Droit administratif', 'annee_etude': '1ère année Master'},
]

compteur = 0
for data in niveaux_data:
    existing = session.query(Niveau).filter_by(code_niveau=data['code']).first()
    if existing:
        print(f"   ℹ️ Déjà existant : {data['code']} - {data['libelle']}")
        continue

    niveau = Niveau(
        code_niveau=data['code'],
        libelle=data['libelle'],
        cycle=data['cycle'],
        specialite=data['specialite'],
        annee_etude=data['annee_etude'],
        actif=True
    )
    session.add(niveau)
    compteur += 1
    print(f"   ✅ Créé : {data['code']} - {data['libelle']}")

session.commit()
print(f"\n📊 Résultat : {compteur} niveaux créés")
print("=" * 70)
session.close()
