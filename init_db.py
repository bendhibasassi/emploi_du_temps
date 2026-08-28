# init_db.py
from models_scripts import Base
from sqlalchemy import create_engine

print("🚀 Création de la base de données...")

# Crée la base (un simple fichier)
engine = create_engine("sqlite:///emploi_du_temps.db", echo=True)

# Crée toutes les tables
Base.metadata.create_all(engine)

print("✅ Base de données 'emploi_du_temps.db' créée avec succès !")