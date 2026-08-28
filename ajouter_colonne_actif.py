# ajouter_colonne_actif.py
from sqlalchemy import create_engine, text, inspect
import os

print("🔧 Ajout de la colonne 'actif' à tbl_indisponibilites...")

DB_PATH = os.path.join(os.path.dirname(__file__), "emploi_du_temps.db")
engine = create_engine(f"sqlite:///{DB_PATH}")

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
