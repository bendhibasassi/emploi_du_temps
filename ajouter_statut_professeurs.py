# ajouter_statut_professeurs.py

from sqlalchemy import create_engine, text, inspect
from config import DATABASE_URI
import os

print("🔧 Ajout des colonnes statut, peut_cm, peut_td, peut_tp à tbl_professeurs...")

engine = create_engine(DATABASE_URI)

inspector = inspect(engine)
columns = [col['name'] for col in inspector.get_columns('tbl_professeurs')]

with engine.connect() as conn:
    # Ajouter chaque colonne si elle n'existe pas
    if 'statut' not in columns:
        conn.execute(text("ALTER TABLE tbl_professeurs ADD COLUMN statut VARCHAR(20) DEFAULT 'Permanent'"))
        print("   ✅ Colonne 'statut' ajoutée")
    else:
        print("   ℹ️ Colonne 'statut' existe déjà")

    if 'peut_cm' not in columns:
        conn.execute(text("ALTER TABLE tbl_professeurs ADD COLUMN peut_cm BOOLEAN DEFAULT 1"))
        print("   ✅ Colonne 'peut_cm' ajoutée")
    else:
        print("   ℹ️ Colonne 'peut_cm' existe déjà")

    if 'peut_td' not in columns:
        conn.execute(text("ALTER TABLE tbl_professeurs ADD COLUMN peut_td BOOLEAN DEFAULT 1"))
        print("   ✅ Colonne 'peut_td' ajoutée")
    else:
        print("   ℹ️ Colonne 'peut_td' existe déjà")

    if 'peut_tp' not in columns:
        conn.execute(text("ALTER TABLE tbl_professeurs ADD COLUMN peut_tp BOOLEAN DEFAULT 0"))
        print("   ✅ Colonne 'peut_tp' ajoutée")
    else:
        print("   ℹ️ Colonne 'peut_tp' existe déjà")

    conn.commit()

print("\n✅ Mise à jour terminée !")
