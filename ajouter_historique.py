# ajouter_historique.py
from sqlalchemy import create_engine, text, inspect
from config import DATABASE_URI
import os

print("📋 Création de la table tbl_historique...")

engine = create_engine(DATABASE_URI)

inspector = inspect(engine)

if 'tbl_historique' in inspector.get_table_names():
    print("✅ La table existe déjà !")
else:
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE tbl_historique (
                id_historique INTEGER PRIMARY KEY AUTOINCREMENT,
                utilisateur VARCHAR(100) NOT NULL DEFAULT 'Système',
                action VARCHAR(20) NOT NULL,
                type_objet VARCHAR(30) NOT NULL,
                id_objet INTEGER NOT NULL,
                ancienne_valeur TEXT,
                nouvelle_valeur TEXT,
                date_heure DATETIME DEFAULT CURRENT_TIMESTAMP,
                ip_adresse VARCHAR(45)
            )
        """))
        conn.commit()
        print("✅ Table tbl_historique créée avec succès !")
