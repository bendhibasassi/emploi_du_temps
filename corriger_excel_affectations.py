# corriger_excel_affectations.py
"""
Script pour corriger les libellés du fichier Excel des affectations
afin qu'ils correspondent exactement à ceux de la base de données
"""
import pandas as pd
import os

print("=" * 70)
print("🔧 CORRECTION DU FICHIER EXCEL DES AFFECTATIONS")
print("=" * 70)

# === 1. Charger le fichier Excel ===
file_path = "Affectations_professeurs_matieres_sections_2025-2026.xlsx"
if not os.path.exists(file_path):
    print(f"❌ Fichier '{file_path}' non trouvé !")
    exit()

df = pd.read_excel(file_path, sheet_name="Affectations")
print(f"\n📊 {len(df)} lignes chargées")

# === 2. Définir les corrections ===

# --- Corrections des sections ---
corrections_sections = {
    # L3 - Arabe vers Français
    'الفصيلة أ – L3 Droit privé': 'Section A – L3 Droit privé',
    'الفصيلة ب – L3 Droit privé': 'Section B – L3 Droit privé',
    'الفصيلة أ – L3 Droit public': 'Section A – L3 Droit public',
    'الفصيلة ب – L3 Droit public': 'Section B – L3 Droit public',

    # Masters - Noms longs vers noms courts
    'Section unique – M1 Droit international public': 'Section unique – M1 Droit international',
    'Section unique – M2 Droit international public': 'Section unique – M2 Droit international',
    'Section unique – M1 Gouvernance et lutte contre la corruption': 'Section unique – M1 Gouvernance',
    'Section unique – M2 Gouvernance et lutte contre la corruption': 'Section unique – M2 Gouvernance',
    'Section unique – M1 Droit foncier': 'Section unique – M1 Droit immobilier',
    'Section unique – M2 Droit foncier': 'Section unique – M2 Droit immobilier',
    'Section unique – M1 Droit des contrats et responsabilité': 'Section unique – M1 Droit des contrats',
    'Section unique – M2 Droit des contrats et responsabilité': 'Section unique – M2 Droit des contrats',
}

# --- Corrections des spécialités dans les sections (si nécessaire) ---
# (déjà couvert par les corrections de sections)

# --- Corrections des noms de matières ---
corrections_matieres = {
    'اللغة الأجنبية': 'لغة أجنبية (الإنجليزية) 2',  # M2 Droit des affaires - S2
}

# === 3. Appliquer les corrections ===
print("\n🔍 Application des corrections...")

# Compter les modifications
modifications_sections = 0
modifications_matieres = 0

# 3.1 Corriger les sections
for ancien, nouveau in corrections_sections.items():
    mask = df['Section'] == ancien
    if mask.any():
        count = mask.sum()
        df.loc[mask, 'Section'] = nouveau
        modifications_sections += count
        print(f"   ✅ Section: '{ancien}' → '{nouveau}' ({count} lignes)")

# 3.2 Corriger les matières
for ancien, nouveau in corrections_matieres.items():
    mask = df['Matière'] == ancien
    if mask.any():
        count = mask.sum()
        df.loc[mask, 'Matière'] = nouveau
        modifications_matieres += count
        print(f"   ✅ Matière: '{ancien}' → '{nouveau}' ({count} lignes)")

# === 4. Vérifier les valeurs restantes ===
print("\n🔍 Vérification des valeurs restantes...")

# Vérifier les sections uniques après correction
sections_uniques = df['Section'].unique()
print(f"\n📋 Sections dans le fichier corrigé ({len(sections_uniques)}):")
for s in sections_uniques:
    print(f"   - {s}")

# Vérifier les matières uniques
matieres_uniques = df['Matière'].unique()
print(f"\n📋 Matières dans le fichier corrigé (extrait):")
for m in matieres_uniques[:20]:
    print(f"   - {m}")

# === 5. Sauvegarder le fichier corrigé ===
output_path = "Affectations_corrigees.xlsx"
with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
    df.to_excel(writer, sheet_name="Affectations", index=False)

    # Ajouter une feuille Notes
    notes_df = pd.DataFrame({
        'Information': ['Source', 'Corrections appliquées', 'Date'],
        'Valeur': ['Emplois du temps 2025/2026', 'Libellés adaptés à la base de données', pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')]
    })
    notes_df.to_excel(writer, sheet_name="Notes", index=False)

print(f"\n✅ Fichier corrigé sauvegardé : {output_path}")

# === 6. Statistiques ===
print("\n📊 RÉSUMÉ :")
print(f"   Lignes totales : {len(df)}")
print(f"   Sections corrigées : {modifications_sections}")
print(f"   Matières corrigées : {modifications_matieres}")
print("=" * 70)

print("\n🔎 Vérifie le fichier 'Affectations_corrigees.xlsx' avant de relancer l'import.")
