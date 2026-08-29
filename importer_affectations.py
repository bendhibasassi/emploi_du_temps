# importer_affectations.py
"""
Script pour importer les affectations depuis un fichier Excel
"""
import pandas as pd
from sqlalchemy import create_engine
from config import DATABASE_URI
from sqlalchemy.orm import sessionmaker
from app.models import Professeur, Matiere, Section, Affectation, AnneeUniversitaire
import os

print("=" * 70)
print("📚 IMPORT DES AFFECTATIONS")
print("=" * 70)

# === 1. Connexion à la base ===
engine = create_engine(DATABASE_URI)
Session = sessionmaker(bind=engine)
session = Session()

# === 2. Récupérer l'année universitaire ===
annee = session.query(AnneeUniversitaire).filter_by(active=True).first()
if not annee:
    print("❌ Aucune année universitaire active trouvée !")
    exit()

print(f"📅 Année universitaire : {annee.libelle} (ID: {annee.id_annee})")

# === 3. Charger le fichier Excel ===
file_path = "Affectations_corrigees.xlsx"
try:
    df = pd.read_excel(file_path, sheet_name="Affectations")
except FileNotFoundError:
    print(f"❌ Fichier '{file_path}' non trouvé !")
    exit()
except Exception as e:
    print(f"❌ Erreur de lecture : {e}")
    exit()

print(f"\n📊 {len(df)} lignes trouvées dans le fichier")

# === 4. Supprimer les anciennes affectations ===
print("\n🗑️ Suppression des affectations existantes...")
count = session.query(Affectation).delete()
session.commit()
print(f"   ✅ {count} affectations supprimées")

# === 5. Importer les nouvelles affectations ===
print("\n📥 Import des affectations...")
compteur_ajoutees = 0
compteur_erreurs = 0

for index, row in df.iterrows():
    prof_nom = str(row['Professeur']).strip()
    matiere_nom = str(row['Matière']).strip()
    section_nom = str(row['Section']).strip()
    type_enseignement = str(row['Type (CM/TD)']).strip().upper()
    semestre = str(row['Semestre']).strip()

    # Rechercher le professeur
    prof = session.query(Professeur).filter_by(nom=prof_nom).first()
    if not prof:
        print(f"   ⚠️ Ligne {index+2}: Professeur '{prof_nom}' non trouvé")
        compteur_erreurs += 1
        continue

    # Rechercher la matière
    matiere = session.query(Matiere).filter_by(nom_matiere=matiere_nom).first()
    if not matiere:
        print(f"   ⚠️ Ligne {index+2}: Matière '{matiere_nom}' non trouvée")
        compteur_erreurs += 1
        continue

    # Rechercher la section
    section = session.query(Section).filter_by(libelle=section_nom).first()
    if not section:
        print(f"   ⚠️ Ligne {index+2}: Section '{section_nom}' non trouvée")
        compteur_erreurs += 1
        continue

    # Créer l'affectation
    affectation = Affectation(
        id_annee=annee.id_annee,
        id_professeur=prof.id_professeur,
        id_matiere=matiere.id_matiere,
        id_section=section.id_section,
        semestre=int(semestre.replace('S', '')) if semestre.startswith('S') else 1,
        type_enseignement=type_enseignement,
        nb_seances_semaine=1 if type_enseignement == 'TD' else 2,
        duree_seance_minutes=90,
        actif=True
    )
    session.add(affectation)
    compteur_ajoutees += 1
    print(f"   ✅ Ajoutée : {prof.nom} → {matiere.nom_matiere} → {section.libelle} ({type_enseignement})")

# === 6. Valider ===
session.commit()
print(f"\n📊 Résumé :")
print(f"   Affectations ajoutées : {compteur_ajoutees}")
print(f"   Erreurs : {compteur_erreurs}")
print("=" * 70)
session.close()
