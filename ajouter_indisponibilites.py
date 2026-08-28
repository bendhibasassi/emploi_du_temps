# ajouter_indisponibilites.py
from sqlalchemy import create_engine, text, inspect
import os

print("📋 Création de la table tbl_indisponibilites...")

DB_PATH = os.path.join(os.path.dirname(__file__), "emploi_du_temps.db")
engine = create_engine(f"sqlite:///{DB_PATH}")

inspector = inspect(engine)

if 'tbl_indisponibilites' in inspector.get_table_names():
    print("✅ La table existe déjà !")
    
    # Vérifier si la colonne 'actif' existe
    columns = [col['name'] for col in inspector.get_columns('tbl_indisponibilites')]
    if 'actif' not in columns:
        print("🔧 Ajout de la colonne 'actif'...")
        with engine.connect() as conn:
            conn.execute(text("""
                ALTER TABLE tbl_indisponibilites
                ADD COLUMN actif BOOLEAN DEFAULT 1
            """))
            conn.commit()
            print("✅ Colonne 'actif' ajoutée !")
    else:
        print("✅ La colonne 'actif' existe déjà !")
else:
    print("🔧 Création de la table...")
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE tbl_indisponibilites (
                id_indisponibilite INTEGER PRIMARY KEY AUTOINCREMENT,
                id_annee INTEGER NOT NULL,
                id_professeur INTEGER NOT NULL,
                jour INTEGER NOT NULL,
                id_creneau INTEGER NOT NULL,
                type_contrainte VARCHAR(15) NOT NULL DEFAULT 'INTERDIT',
                commentaire VARCHAR(500),
                actif BOOLEAN DEFAULT 1,
                FOREIGN KEY (id_annee) REFERENCES tbl_annees_univ (id_annee),
                FOREIGN KEY (id_professeur) REFERENCES tbl_professeurs (id_professeur),
                FOREIGN KEY (id_creneau) REFERENCES tbl_creneaux (id_creneau),
                UNIQUE (id_annee, id_professeur, jour, id_creneau)
            )
        """))
        conn.commit()
        print("✅ Table créée avec succès !")
