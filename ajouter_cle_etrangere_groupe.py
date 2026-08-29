# ajouter_cle_etrangere_groupe.py

import sqlite3
from config import DATABASE_PATH
import os



print("🔧 Ajout de la clé étrangère id_groupe → tbl_groupes...")

# Connexion à la base
conn = sqlite3.connect(DATABASE_PATH)
cursor = conn.cursor()

# === DÉSACTIVER TEMPORAIREMENT LES CLÉS ÉTRANGÈRES ===
cursor.execute("PRAGMA foreign_keys = OFF")

# Démarrer la transaction
cursor.execute("BEGIN TRANSACTION")

try:
    # 1. Vérifier la structure actuelle
    cursor.execute("PRAGMA table_info(tbl_affectations)")
    columns = cursor.fetchall()
    print("\n📋 Colonnes actuelles de tbl_affectations :")
    for col in columns:
        print(f"   - {col[1]} ({col[2]})")

    # 2. Créer une nouvelle table avec la clé étrangère
    print("\n📋 Création d'une nouvelle table avec la clé étrangère...")
    cursor.execute("""
    CREATE TABLE tbl_affectations_new (
        id_affectation INTEGER NOT NULL,
        id_annee INTEGER NOT NULL,
        id_professeur INTEGER NOT NULL,
        id_matiere INTEGER NOT NULL,
        id_section INTEGER NOT NULL,
        semestre INTEGER NOT NULL,
        type_enseignement VARCHAR(10) NOT NULL,
        nb_seances_semaine INTEGER,
        duree_seance_minutes INTEGER,
        volume_total_minutes INTEGER,
        priorite INTEGER,
        actif BOOLEAN,
        id_groupe INTEGER,
        PRIMARY KEY (id_affectation),
        FOREIGN KEY (id_annee) REFERENCES tbl_annees_univ (id_annee),
        FOREIGN KEY (id_professeur) REFERENCES tbl_professeurs (id_professeur),
        FOREIGN KEY (id_matiere) REFERENCES tbl_matieres (id_matiere),
        FOREIGN KEY (id_section) REFERENCES tbl_sections (id_section),
        FOREIGN KEY (id_groupe) REFERENCES tbl_groupes (id_groupe)
    )
    """)

    # 3. Copier les données
    print("📋 Copie des données...")
    cursor.execute("""
    INSERT INTO tbl_affectations_new (
        id_affectation, id_annee, id_professeur, id_matiere, id_section,
        semestre, type_enseignement, nb_seances_semaine, duree_seance_minutes,
        volume_total_minutes, priorite, actif, id_groupe
    )
    SELECT
        id_affectation, id_annee, id_professeur, id_matiere, id_section,
        semestre, type_enseignement, nb_seances_semaine, duree_seance_minutes,
        volume_total_minutes, priorite, actif, id_groupe
    FROM tbl_affectations
    """)

    # 4. Vérifier le nombre de lignes copiées
    cursor.execute("SELECT COUNT(*) FROM tbl_affectations")
    old_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tbl_affectations_new")
    new_count = cursor.fetchone()[0]
    print(f"   ✅ {old_count} lignes copiées (vérification : {new_count})")

    # 5. Supprimer l'ancienne table (contrainte désactivée)
    print("📋 Suppression de l'ancienne table...")
    cursor.execute("DROP TABLE tbl_affectations")

    # 6. Renommer la nouvelle table
    print("📋 Renommage de la nouvelle table...")
    cursor.execute("ALTER TABLE tbl_affectations_new RENAME TO tbl_affectations")

    # 7. Valider la transaction
    cursor.execute("COMMIT")
    print("✅ Transaction validée !")

except Exception as e:
    # En cas d'erreur, annuler tout
    cursor.execute("ROLLBACK")
    print(f"❌ Erreur : {e}")

finally:
    # === RÉACTIVER LES CLÉS ÉTRANGÈRES ===
    cursor.execute("PRAGMA foreign_keys = ON")
    conn.close()

# === VÉRIFICATION FINALE ===
print("\n📋 Vérification de la nouvelle structure...")
conn = sqlite3.connect(DATABASE_PATH)
cursor = conn.cursor()

cursor.execute("PRAGMA foreign_key_list(tbl_affectations)")
foreign_keys = cursor.fetchall()
print("   Clés étrangères dans tbl_affectations :")
for fk in foreign_keys:
    print(f"      - {fk[3]} → {fk[2]}({fk[4]})")

cursor.execute("SELECT COUNT(*) FROM tbl_affectations")
count = cursor.fetchone()[0]
print(f"\n✅ Table tbl_affectations recréée avec {count} lignes")

conn.close()
print("\n🎉 Clé étrangère ajoutée avec succès !")
