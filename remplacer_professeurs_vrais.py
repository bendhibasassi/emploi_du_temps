# remplacer_professeurs_vrais.py
"""
Script pour remplacer la liste des professeurs par la vraie liste du département
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models_scripts import Professeur
import os

print("=" * 60)
print("👨‍🏫 REMPLACEMENT PAR LA VRAIE LISTE DES PROFESSEURS")
print("=" * 60)

DB_PATH = os.path.join(os.path.dirname(__file__), "emploi_du_temps.db")
engine = create_engine(f"sqlite:///{DB_PATH}")
Session = sessionmaker(bind=engine)
session = Session()

# === 1. Supprimer tous les professeurs existants ===
print("\n🗑️ Suppression des professeurs existants...")
count = session.query(Professeur).delete()
session.commit()
print(f"   ✅ {count} professeurs supprimés")

# === 2. Nouvelle liste des professeurs (vrais noms) ===
professeurs_data = [
    {'nom': 'التجاني عبد القهار', 'prenom': '', 'grade': 'Professeur', 'email': None, 'actif': True},
    {'nom': 'الدح عبد المالك', 'prenom': '', 'grade': 'Professeur', 'email': None, 'actif': True},
    {'nom': 'النحوي سليمان', 'prenom': '', 'grade': 'Professeur', 'email': None, 'actif': True},
    {'nom': 'لحاق عيسى', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'خضراوي الهادي', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'عيمور راضية', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'يوسفي مباركة', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'بن عرفة نذير', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'بن قسمية العربي', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'طويسات عائشة', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'خضرون عطاء الله', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'يخلف عبد القادر', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'بن قويدر الطاهر', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'بوفاتح أحمد', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'قريبيز مراد', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'ملياني عبد الرحمن حميد', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'بن عطية لخضر', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'بن الغويني عبد الحميد', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'عبيدي محمد', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'بوعيشة بوغفالة', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'غريبي محمد', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'جقيدل رابح', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'بن ذهيبة رباب', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'لكحل عائشة', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'ديدوني بلقاسم', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'بن صالح محمد الحاج عيسى', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'التاج عطاء الله', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'بركات بهية', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'بوقرين عبد الحليم', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'شويرب جيلالي', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'بطيمي حسين', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'الفحلة مديحة', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'ملياني عبد الوهاب', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'ذيب محمد', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'رابحي لخضر', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'بلحسن حسام الدين لحسن', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'قوق أم الخير', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'برطال عبد القادر', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'زديك الطاهر', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'سعودي علي', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'خطوي مسعود', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'عكوش حنان', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'طهاري حنان', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'غريبي يحي', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'مسعودي لمين', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'بلكعيبات مراد', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'رزق الله العري بن مهيدي', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'عكاكة فاطمة الزهراء', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'غريبي عطاء الله', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'بوناصر إيمان', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'دمانة محمد', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'سعودي سعيد', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'زوبيري بن قويدر', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'أولاد العيد الطاهر', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'النوعي أحمد', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'بن جلول مصطفى', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'عمران عائشة', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
    {'nom': 'بن الزوبير عمر', 'prenom': '', 'grade': 'Maître de conférences', 'email': None, 'actif': True},
]

# === 3. Importer les professeurs ===
print("\n📥 Import des professeurs...")
compteur = 0

for data in professeurs_data:
    # Vérifier si le nom existe déjà (pour éviter les doublons)
    existing = session.query(Professeur).filter_by(nom=data['nom']).first()
    if existing:
        print(f"   ℹ️ Déjà existant : {data['nom']}")
        continue
    
    professeur = Professeur(**data)
    session.add(professeur)
    compteur += 1
    print(f"   ✅ Ajouté : {data['nom']} ({data['grade']})")

session.commit()
print(f"\n📊 Résumé : {compteur} professeurs ajoutés")
print("=" * 60)
session.close()
