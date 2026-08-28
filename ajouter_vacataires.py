# ajouter_vacataires.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models_scripts import Professeur
import os

print("👨‍🏫 Ajout de vacataires supplémentaires...")

DB_PATH = os.path.join(os.path.dirname(__file__), "emploi_du_temps.db")
engine = create_engine(f"sqlite:///{DB_PATH}")
Session = sessionmaker(bind=engine)
session = Session()

# Liste des vacataires supplémentaires
vacataires_data = [
    {'nom': 'بن عودة محمد', 'prenom': '', 'grade': 'Vacataire', 'email': None, 'statut': 'Vacataire', 'peut_cm': False, 'peut_td': True, 'peut_tp': False},
    {'nom': 'بوخاري فاطمة', 'prenom': '', 'grade': 'Vacataire', 'email': None, 'statut': 'Vacataire', 'peut_cm': False, 'peut_td': True, 'peut_tp': False},
    {'nom': 'بلقاسمي نورالدين', 'prenom': '', 'grade': 'Vacataire', 'email': None, 'statut': 'Vacataire', 'peut_cm': False, 'peut_td': True, 'peut_tp': False},
    {'nom': 'حاتم سامية', 'prenom': '', 'grade': 'Vacataire', 'email': None, 'statut': 'Vacataire', 'peut_cm': False, 'peut_td': True, 'peut_tp': False},
    {'nom': 'ربيعي عبد الحميد', 'prenom': '', 'grade': 'Vacataire', 'email': None, 'statut': 'Vacataire', 'peut_cm': False, 'peut_td': True, 'peut_tp': False},
    {'nom': 'زراوي إيمان', 'prenom': '', 'grade': 'Vacataire', 'email': None, 'statut': 'Vacataire', 'peut_cm': False, 'peut_td': True, 'peut_tp': False},
]

compteur = 0
for data in vacataires_data:
    existing = session.query(Professeur).filter_by(nom=data['nom']).first()
    if existing:
        print(f"   ℹ️ Déjà existant : {data['nom']}")
        continue

    professeur = Professeur(**data)
    session.add(professeur)
    compteur += 1
    print(f"   ✅ Ajouté : {data['nom']} (Vacataire)")

session.commit()
print(f"\n📊 Résultat : {compteur} vacataires ajoutés")
session.close()
