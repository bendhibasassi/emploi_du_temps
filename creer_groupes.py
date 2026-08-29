# creer_groupes.py
"""
Script pour créer automatiquement les groupes pour chaque section
en fonction du nombre de groupes souhaité
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models_scripts import Section, Groupe
import os

print("=" * 70)
print("👥 CRÉATION DES GROUPES PAR SECTION")
print("=" * 70)

DB_PATH = os.path.join(os.path.dirname(__file__), "emploi_du_temps.db")
engine = create_engine(f"sqlite:///{DB_PATH}")
Session = sessionmaker(bind=engine)
session = Session()

# === Définition du nombre de groupes par section ===
# Format : "nom_de_la_section": nombre_de_groupes
groupes_par_section = {
    # L3
    "Section A – L3 Droit privé": 2,
    "Section B – L3 Droit privé": 2,
    "Section A – L3 Droit public": 2,
    "Section B – L3 Droit public": 2,

    # Masters (généralement 1 ou 2 groupes selon effectif)
    "Section unique – M1 Droit pénal": 1,
    "Section unique – M2 Droit pénal": 1,
    "Section unique – M1 Droit international": 1,
    "Section unique – M2 Droit international": 1,
    "Section unique – M1 Gouvernance": 1,
    "Section unique – M2 Gouvernance": 1,
    "Section unique – M1 Droit des affaires": 1,
    "Section unique – M2 Droit des affaires": 1,
    "Section unique – M1 Droit immobilier": 1,
    "Section unique – M2 Droit immobilier": 1,
    "Section unique – M1 Droit des contrats": 1,
    "Section unique – M2 Droit des contrats": 1,
    "Section unique – M1 Droit administratif": 1,
}

print("\n🔍 Récupération des sections...")
sections = session.query(Section).all()

compteur_total = 0
compteur_ajoutes = 0
compteur_ignores = 0

for section in sections:
    # Chercher le nombre de groupes pour cette section
    nb_groupes = groupes_par_section.get(section.libelle, 0)

    if nb_groupes == 0:
        print(f"   ⚠️ Aucun groupe défini pour : {section.libelle}")
        compteur_ignores += 1
        continue

    print(f"\n📋 Section : {section.libelle}")
    print(f"   → {nb_groupes} groupe(s) à créer")

    # Calculer l'effectif par groupe
    effectif_par_groupe = section.effectif // nb_groupes if section.effectif and nb_groupes > 0 else 25

    # Créer les groupes
    for i in range(1, nb_groupes + 1):
        code = f"G{i}"
        nom = f"Groupe {i}"
        effectif = effectif_par_groupe

        # Vérifier si le groupe existe déjà
        existing = session.query(Groupe).filter_by(
            id_section=section.id_section,
            code_groupe=code
        ).first()

        if existing:
            print(f"      ℹ️ Groupe déjà existant : {code}")
            compteur_ignores += 1
            continue

        # Créer le groupe
        groupe = Groupe(
            id_section=section.id_section,
            code_groupe=code,
            nom_groupe=nom,
            effectif=effectif,
            actif=True
        )
        session.add(groupe)
        compteur_ajoutes += 1
        print(f"      ✅ Ajouté : {code} ({effectif} étudiants)")

    compteur_total += nb_groupes

session.commit()

print("\n" + "=" * 70)
print("📊 RÉSUMÉ :")
print(f"   Groupes ajoutés : {compteur_ajoutes}")
print(f"   Groupes ignorés (existants) : {compteur_ignores}")
print(f"   Total groupes créés : {compteur_total}")
print("=" * 70)
session.close()
