# ajouter_niveaux.py

from sqlalchemy import create_engine
from config import DATABASE_URI
from sqlalchemy.orm import sessionmaker
from app.models import Niveau
import os

print("📋 Ajout des niveaux...")

engine = create_engine(DATABASE_URI)
Session = sessionmaker(bind=engine)
session = Session()

niveaux_data = [
    {'code': 'L1', 'libelle': 'Licence 1 Droit public', 'cycle': 'LICENCE', 'specialite': 'Droit public', 'annee_etude': '1ère année'},
    {'code': 'L2', 'libelle': 'Licence 2 Droit public', 'cycle': 'LICENCE', 'specialite': 'Droit public', 'annee_etude': '2ème année'},
    {'code': 'L3', 'libelle': 'Licence 3 Droit public', 'cycle': 'LICENCE', 'specialite': 'Droit public', 'annee_etude': '3ème année'},
    {'code': 'M1', 'libelle': 'Master 1 Droit administratif', 'cycle': 'MASTER', 'specialite': 'Droit public', 'annee_etude': '1ère année Master'},
    {'code': 'M2', 'libelle': 'Master 2 Droit administratif', 'cycle': 'MASTER', 'specialite': 'Droit public', 'annee_etude': '2ème année Master'},
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
    print(f"   ✅ Ajouté : {data['code']} - {data['libelle']}")

session.commit()
print(f"\n📊 Résultat : {compteur} niveaux ajoutés")
session.close()
