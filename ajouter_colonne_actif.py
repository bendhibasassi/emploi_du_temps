# ajouter_colonne_actif.py
from sqlalchemy import create_engine, text, inspect
from config import DATABASE_URI
import os

print("🔧 Ajout de la colonne 'actif' à tbl_indisponibilites...")

engine = create_engine(DATABASE_URI)

# Vérifier si la colonne existe déjà
inspector = inspect(engine)
columns = [col['name'] for col in inspector.get_columns('tbl_indisponibilites')]

if 'actif' in columns:
    print("✅ La colonne 'actif' existe déjà !")
else:
    # Ajouter la colonne
    with engine.connect() as conn:
        conn.execute(text("""
            ALTER TABLE tbl_indisponibilites
            ADD COLUMN actif BOOLEAN DEFAULT 1
        """))
        conn.commit()
        print("✅ Colonne 'actif' ajoutée avec succès !")

    # Vérifier
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('tbl_indisponibilites')]
    print(f"📋 Colonnes actuelles : {columns}")
