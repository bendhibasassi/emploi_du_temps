# ajouter_salles.py
import os

from sqlalchemy import create_engine
from config import DATABASE_URI
from sqlalchemy.orm import sessionmaker

from app.models import Salle

print("🏫 Ajout de salles...")

engine = create_engine(DATABASE_URI)
Session = sessionmaker(bind=engine)

salles = [
    {"code_salle": "A101", "nom_salle": "Amphi A", "type_salle": "AMPHI", "capacite": 100, "batiment": "Bâtiment A"},
    {"code_salle": "A102", "nom_salle": "Amphi B", "type_salle": "AMPHI", "capacite": 80, "batiment": "Bâtiment A"},
    {"code_salle": "B201", "nom_salle": "Salle B201", "type_salle": "SALLE", "capacite": 30, "batiment": "Bâtiment B"},
    {"code_salle": "B202", "nom_salle": "Salle B202", "type_salle": "SALLE", "capacite": 25, "batiment": "Bâtiment B"},
    {"code_salle": "C301", "nom_salle": "Labo C301", "type_salle": "LABO", "capacite": 20, "batiment": "Bâtiment C"},
    {"code_salle": "D401", "nom_salle": "TD D401", "type_salle": "TD", "capacite": 15, "batiment": "Bâtiment D"},
]

with Session() as session:
    compteur = 0
    for data in salles:
        existing = session.query(Salle).filter_by(code_salle=data["code_salle"]).first()
        if existing is None:
            salle = Salle(**data)
            session.add(salle)
            compteur += 1
            print(f"   ✅ Salle ajoutée : {data['nom_salle']} ({data['capacite']} places)")
        else:
            print(f"   ℹ️ Salle déjà existante : {data['nom_salle']}")

    session.commit()

print(f"✅ {compteur} salles ajoutées avec succès !")
