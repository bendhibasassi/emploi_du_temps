# generer_fichier_td.py
"""
Script pour générer un fichier Excel de base pour les TD
"""
import pandas as pd
import sys
from sqlalchemy import create_engine
from config import DATABASE_URI
from sqlalchemy.orm import sessionmaker
from app.models import (
    Professeur, Matiere, Niveau, Section, Groupe, Affectation,
    AnneeUniversitaire
)
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

print("=" * 70)
print("📊 GÉNÉRATION DU FICHIER EXCEL POUR LES TD")
print("=" * 70)

engine = create_engine(DATABASE_URI)
Session = sessionmaker(bind=engine)
session = Session()

# Récupérer les vacataires
vacataires = session.query(Professeur).filter_by(statut='Vacataire').all()
print(f"\n👨‍🏫 Vacataires disponibles : {len(vacataires)}")

# Récupérer les affectations CM existantes
affectations_cm = session.query(Affectation).all()
print(f"📚 Affectations CM existantes : {len(affectations_cm)}")

# Générer les lignes TD
td_data = []

for aff in affectations_cm:
    # Récupérer la matière, la section, le semestre
    matiere = session.query(Matiere).filter_by(id_matiere=aff.id_matiere).first()
    section = session.query(Section).filter_by(id_section=aff.id_section).first()
    niveau = session.query(Niveau).filter_by(id_niveau=section.id_niveau).first() if section else None

    if not matiere or not section:
        continue

    # Récupérer les groupes de cette section
    groupes = session.query(Groupe).filter_by(id_section=section.id_section, actif=True).all()

    if not groupes:
        continue

    # Pour chaque groupe, attribuer un vacataire (rotatif)
    for idx, groupe in enumerate(groupes):
        # Sélectionner un vacataire en rotation
        vacataire = vacataires[idx % len(vacataires)] if vacataires else None

        # Déterminer le semestre (conserver celui du CM)
        semestre = aff.semestre if aff.semestre else 1

        td_data.append({
            'Professeur': vacataire.nom if vacataire else '',
            'Matière': matiere.nom_matiere,
            'Section': section.libelle,
            'Groupe': groupe.code_groupe,
            'Semestre': f'S{semestre}',
            'Type': 'TD'
        })

# Créer le DataFrame
df = pd.DataFrame(td_data)

print(f"\n📊 {len(df)} lignes TD générées")

# Sauvegarder
output_path = "TD_a_remplir.xlsx"
with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
    df.to_excel(writer, sheet_name="TD", index=False)

    # Ajouter une feuille d'instructions
    instructions = pd.DataFrame({
        'Colonne': ['Professeur', 'Matière', 'Section', 'Groupe', 'Semestre', 'Type'],
        'Description': [
            'Nom du professeur (vacataire ou permanent)',
            'Nom exact de la matière (à vérifier dans la base)',
            'Nom exact de la section (à vérifier dans la base)',
            'Code du groupe (G1, G2, G3...)',
            'Semestre (S1, S2, S3, S5...)',
            'Toujours "TD"'
        ],
        'Exemple': [
            'بن عودة محمد',
            'دولت اداري',
            'Section A – L3 Droit public',
            'G1',
            'S5',
            'TD'
        ]
    })
    instructions.to_excel(writer, sheet_name="Instructions", index=False)

print(f"✅ Fichier généré : {output_path}")
print("\n📝 Instructions :")
print("   1. Ouvre le fichier 'TD_a_remplir.xlsx'")
print("   2. Vérifie/modifie les professeurs attribués")
print("   3. Supprime les lignes inutiles")
print("   4. Sauvegarde sous 'TD_import.xlsx'")
print("   5. Exécute le script d'import des TD")

session.close()
