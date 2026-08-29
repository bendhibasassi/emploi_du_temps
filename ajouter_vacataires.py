# ajouter_vacataires.py

from sqlalchemy import create_engine
from config import DATABASE_URI
from sqlalchemy.orm import sessionmaker
from app.models import Professeur
import os

print("👨‍🏫 Ajout de vacataires supplémentaires...")

engine = create_engine(DATABASE_URI)
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
