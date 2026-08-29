# remplacer_professeurs.py
"""
Script pour nettoyer et remplacer la liste des professeurs
"""
from sqlalchemy import create_engine
from config import DATABASE_URI
from sqlalchemy.orm import sessionmaker
from app.models import Professeur
import os

print("=" * 60)
print("👨‍🏫 REMPLACEMENT DE LA LISTE DES PROFESSEURS")
print("=" * 60)

engine = create_engine(DATABASE_URI)
Session = sessionmaker(bind=engine)
session = Session()

# === 1. Supprimer tous les professeurs existants ===
print("\n🗑️ Suppression des professeurs existants...")
count = session.query(Professeur).delete()
session.commit()
print(f"   ✅ {count} professeurs supprimés")

# === 2. Nouvelle liste des professeurs ===
professeurs_data = [
    # Professeurs permanents - Licence
    {'nom': 'BENALI', 'prenom': 'Ahmed', 'grade': 'Professeur', 'email': 'ahmed.benali@univ.dz', 'actif': True},
    {'nom': 'ZOHRA', 'prenom': 'Fatima', 'grade': 'Professeur', 'email': 'fatima.zohra@univ.dz', 'actif': True},
    {'nom': 'SLIMANI', 'prenom': 'Mohamed', 'grade': 'Professeur', 'email': 'mohamed.slimani@univ.dz', 'actif': True},
    {'nom': 'BENSAID', 'prenom': 'Nadia', 'grade': 'Professeur', 'email': 'nadia.bensaid@univ.dz', 'actif': True},
    {'nom': 'MELLAH', 'prenom': 'Karim', 'grade': 'Maître de conférences', 'email': 'karim.mellah@univ.dz', 'actif': True},
    {'nom': 'BELKACEM', 'prenom': 'Samira', 'grade': 'Maître de conférences', 'email': 'samira.belkacem@univ.dz', 'actif': True},
    {'nom': 'BOUHALI', 'prenom': 'Rachid', 'grade': 'Maître de conférences', 'email': 'rachid.bouhali@univ.dz', 'actif': True},
    {'nom': 'CHERIF', 'prenom': 'Yamina', 'grade': 'Maître de conférences', 'email': 'yamina.cherif@univ.dz', 'actif': True},
    {'nom': 'BENYAHIA', 'prenom': 'Hakim', 'grade': 'Maître de conférences', 'email': 'hakim.benyahia@univ.dz', 'actif': True},
    {'nom': 'HADJ', 'prenom': 'Malika', 'grade': 'Maître de conférences', 'email': 'malika.hadj@univ.dz', 'actif': True},
    {'nom': 'GHERBI', 'prenom': 'Tarek', 'grade': 'Maître de conférences', 'email': 'tarek.gherbi@univ.dz', 'actif': True},
    {'nom': 'MEKKAOUI', 'prenom': 'Saida', 'grade': 'Maître de conférences', 'email': 'saida.mekkaoui@univ.dz', 'actif': True},
    {'nom': 'AIT', 'prenom': 'Noureddine', 'grade': 'Maître de conférences', 'email': 'noureddine.ait@univ.dz', 'actif': True},
    {'nom': 'BENZINA', 'prenom': 'Farida', 'grade': 'Maître de conférences', 'email': 'farida.benzina@univ.dz', 'actif': True},
    
    # Professeurs permanents - Master
    {'nom': 'MOKHTARI', 'prenom': 'Larbi', 'grade': 'Professeur', 'email': 'larbi.mokhtari@univ.dz', 'actif': True},
    {'nom': 'FERHAT', 'prenom': 'Zohra', 'grade': 'Professeur', 'email': 'zohra.ferhat@univ.dz', 'actif': True},
    {'nom': 'BELHADJ', 'prenom': 'Ahmed', 'grade': 'Professeur', 'email': 'ahmed.belhadj@univ.dz', 'actif': True},
    {'nom': 'KADRI', 'prenom': 'Mustapha', 'grade': 'Maître de conférences', 'email': 'mustapha.kadri@univ.dz', 'actif': True},
    {'nom': 'MEHDAOUI', 'prenom': 'Nora', 'grade': 'Maître de conférences', 'email': 'nora.mehdaoui@univ.dz', 'actif': True},
    {'nom': 'OUHAB', 'prenom': 'Salim', 'grade': 'Maître de conférences', 'email': 'salim.ouhab@univ.dz', 'actif': True},
    {'nom': 'LOUNI', 'prenom': 'Fatma', 'grade': 'Maître de conférences', 'email': 'fatma.louni@univ.dz', 'actif': True},
    {'nom': 'MESSAOUD', 'prenom': 'Djamel', 'grade': 'Maître de conférences', 'email': 'djamel.messaoud@univ.dz', 'actif': True},
    {'nom': 'AIT', 'prenom': 'Samia', 'grade': 'Maître de conférences', 'email': 'samia.ait@univ.dz', 'actif': True},
    {'nom': 'BOURAS', 'prenom': 'Hamid', 'grade': 'Maître de conférences', 'email': 'hamid.bouras@univ.dz', 'actif': True},
    
    # Vacataires
    {'nom': 'AMRANI', 'prenom': 'Mohamed', 'grade': 'Vacataire', 'email': 'mohamed.amrani@univ.dz', 'actif': True},
    {'nom': 'DAHMANI', 'prenom': 'Fatima', 'grade': 'Vacataire', 'email': 'fatima.dahmani@univ.dz', 'actif': True},
    {'nom': 'BEDDOU', 'prenom': 'Ali', 'grade': 'Vacataire', 'email': 'ali.beddou@univ.dz', 'actif': True},
    {'nom': 'HAMIDI', 'prenom': 'Karima', 'grade': 'Vacataire', 'email': 'karima.hamidi@univ.dz', 'actif': True},
    {'nom': 'SAIDI', 'prenom': 'Abdallah', 'grade': 'Vacataire', 'email': 'abdallah.saidi@univ.dz', 'actif': True},
    {'nom': 'KHELIFI', 'prenom': 'Nadia', 'grade': 'Vacataire', 'email': 'nadia.khelifi@univ.dz', 'actif': True},
    {'nom': 'AMOKRANE', 'prenom': 'Mohamed', 'grade': 'Vacataire', 'email': 'mohamed.amokrane@univ.dz', 'actif': True},
    {'nom': 'BOUKRAA', 'prenom': 'Khadija', 'grade': 'Vacataire', 'email': 'khadija.boukraa@univ.dz', 'actif': True},
    {'nom': 'CHERIF', 'prenom': 'Nabil', 'grade': 'Vacataire', 'email': 'nabil.cherif@univ.dz', 'actif': True},
    {'nom': 'BENYAHIA', 'prenom': 'Fadila', 'grade': 'Vacataire', 'email': 'fadila.benyahia@univ.dz', 'actif': True},
    {'nom': 'HADJ', 'prenom': 'Youssef', 'grade': 'Vacataire', 'email': 'youssef.hadj@univ.dz', 'actif': True},
    {'nom': 'LARBI', 'prenom': 'Assia', 'grade': 'Vacataire', 'email': 'assia.larbi@univ.dz', 'actif': True},
    {'nom': 'BOUROUIS', 'prenom': 'Rachid', 'grade': 'Vacataire', 'email': 'rachid.bourouis@univ.dz', 'actif': True},
    {'nom': 'MEBARKI', 'prenom': 'Djamila', 'grade': 'Vacataire', 'email': 'djamila.mebarki@univ.dz', 'actif': True},
    {'nom': 'HARCHI', 'prenom': 'Kamel', 'grade': 'Vacataire', 'email': 'kamel.harchi@univ.dz', 'actif': True},
    {'nom': 'BOUHALI', 'prenom': 'Samira', 'grade': 'Vacataire', 'email': 'samira.bouhali@univ.dz', 'actif': True},
    {'nom': 'MELLAH', 'prenom': 'Mourad', 'grade': 'Vacataire', 'email': 'mourad.mellah@univ.dz', 'actif': True},
    {'nom': 'BENZID', 'prenom': 'Fatima', 'grade': 'Vacataire', 'email': 'fatima.benzid@univ.dz', 'actif': True},
    {'nom': 'KEDDAD', 'prenom': 'Amar', 'grade': 'Vacataire', 'email': 'amar.keddad@univ.dz', 'actif': True},
    {'nom': 'BOUCHERIT', 'prenom': 'Hakima', 'grade': 'Vacataire', 'email': 'hakima.boucherit@univ.dz', 'actif': True},
    {'nom': 'BELKAID', 'prenom': 'Sofiane', 'grade': 'Vacataire', 'email': 'sofiane.belkaid@univ.dz', 'actif': True},
    {'nom': 'HAMMICHE', 'prenom': 'Nadira', 'grade': 'Vacataire', 'email': 'nadira.hammiche@univ.dz', 'actif': True},
    {'nom': 'RAMDANI', 'prenom': 'Abdelkader', 'grade': 'Vacataire', 'email': 'abdelkader.ramdani@univ.dz', 'actif': True},
    {'nom': 'MEKNASSI', 'prenom': 'Zahia', 'grade': 'Vacataire', 'email': 'zahia.meknassi@univ.dz', 'actif': True},
    {'nom': 'FERHAT', 'prenom': 'Miloud', 'grade': 'Vacataire', 'email': 'miloud.ferhat@univ.dz', 'actif': True},
    {'nom': 'BENABDELAZIZ', 'prenom': 'Feriel', 'grade': 'Vacataire', 'email': 'feriel.benabdelaziz@univ.dz', 'actif': True},
    {'nom': 'ZIANE', 'prenom': 'Abdelhamid', 'grade': 'Vacataire', 'email': 'abdelhamid.ziane@univ.dz', 'actif': True},
    {'nom': 'BOUKHRIS', 'prenom': 'Samia', 'grade': 'Vacataire', 'email': 'samia.boukhris@univ.dz', 'actif': True},
    {'nom': 'DEBBAH', 'prenom': 'Abdelmalek', 'grade': 'Vacataire', 'email': 'abdelmalek.debbah@univ.dz', 'actif': True},
    {'nom': 'OUAHED', 'prenom': 'Karima', 'grade': 'Vacataire', 'email': 'karima.ouahed@univ.dz', 'actif': True},
    {'nom': 'KHELLAF', 'prenom': 'Farouk', 'grade': 'Vacataire', 'email': 'farouk.khellaf@univ.dz', 'actif': True},
    {'nom': 'BENKHELIFA', 'prenom': 'Leila', 'grade': 'Vacataire', 'email': 'leila.benkhelifa@univ.dz', 'actif': True},
    {'nom': 'DJABRI', 'prenom': 'Mounir', 'grade': 'Vacataire', 'email': 'mounir.djabri@univ.dz', 'actif': True},
    {'nom': 'AISSAOUI', 'prenom': 'Fatma', 'grade': 'Vacataire', 'email': 'fatma.aissaoui@univ.dz', 'actif': True},
]

# === 3. Importer les professeurs ===
print("\n📥 Import des professeurs...")
compteur = 0

for data in professeurs_data:
    # Vérifier si l'email existe déjà
    existing = session.query(Professeur).filter_by(email=data['email']).first()
    if existing:
        print(f"   ℹ️ Déjà existant : {data['prenom']} {data['nom']} ({data['email']})")
        continue
    
    professeur = Professeur(**data)
    session.add(professeur)
    compteur += 1
    print(f"   ✅ Ajouté : {data['prenom']} {data['nom']} ({data['grade']})")

session.commit()
print(f"\n📊 Résumé : {compteur} professeurs ajoutés")
print("=" * 60)
session.close()
