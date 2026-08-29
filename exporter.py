# exporter.py
import pandas as pd
from sqlalchemy import create_engine
from config import DATABASE_URI

print("📊 Affichage de l'emploi du temps...")

engine = create_engine(DATABASE_URI)

# Requête SQL pour tout afficher
query = """
SELECT 
    p.nom as Professeur,
    p.prenom as Prenom,
    m.nom_matiere as Matiere,
    sec.code_section as Section,
    CASE s.jour
        WHEN 1 THEN 'Lundi'
        WHEN 2 THEN 'Mardi'
        WHEN 3 THEN 'Mercredi'
        WHEN 4 THEN 'Jeudi'
        WHEN 5 THEN 'Vendredi'
        WHEN 6 THEN 'Samedi'
        WHEN 7 THEN 'Dimanche'
    END as Jour,
    c.heure_debut as Debut,
    c.heure_fin as Fin,
    sa.code_salle as Salle,
    sa.capacite as Capacite
FROM tbl_seances s
JOIN tbl_affectations a ON a.id_affectation = s.id_affectation
JOIN tbl_professeurs p ON p.id_professeur = a.id_professeur
JOIN tbl_matieres m ON m.id_matiere = a.id_matiere
JOIN tbl_sections sec ON sec.id_section = a.id_section
JOIN tbl_creneaux c ON c.id_creneau = s.id_creneau
JOIN tbl_salles sa ON sa.id_salle = s.id_salle
ORDER BY s.jour, c.ordre
"""

df = pd.read_sql(query, engine)

if df.empty:
    print("⚠️ Aucune séance trouvée !")
else:
    print("\n📋 Emploi du temps actuel :")
    print("=" * 80)
    print(df.to_string(index=False))
    print("=" * 80)
    
    # Sauvegarde en Excel
    df.to_excel("emploi_du_temps.xlsx", index=False)
    print("\n✅ Emploi du temps exporté dans 'emploi_du_temps.xlsx'")