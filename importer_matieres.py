# importer_matieres.py
"""
Script d'import des matières
Licence Droit public 2025/2026 + Master Droit administratif 2026/2027
"""
from sqlalchemy import create_engine
from config import DATABASE_URI
from sqlalchemy.orm import sessionmaker
from app.models import Matiere, Niveau
import os

print("=" * 60)
print("📚 IMPORT DES MATIÈRES")
print("=" * 60)

engine = create_engine(DATABASE_URI)
Session = sessionmaker(bind=engine)
session = Session()

# === Récupérer les niveaux ===
print("\n🔍 Récupération des niveaux...")
niveaux = {}
for niveau in session.query(Niveau).all():
    niveaux[niveau.code_niveau] = niveau
    print(f"   ✅ {niveau.code_niveau} : {niveau.libelle} (ID: {niveau.id_niveau})")

# === Définition des matières ===
matieres_data = []

# L1 - S1
matieres_data.extend([
    {'nom': 'مدخل إلى القانون 1', 'code': 'LDP-S1-01', 'niveau_code': 'L1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': True},
    {'nom': 'قانون دستوري 1', 'code': 'LDP-S1-02', 'niveau_code': 'L1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': True},
    {'nom': 'تنظيم قضائي 1', 'code': 'LDP-S1-03', 'niveau_code': 'L1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': True},
    {'nom': 'منهجية العلوم القانونية 1', 'code': 'LDP-S1-04', 'niveau_code': 'L1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': False},
    {'nom': 'تاريخ النظم القانونية', 'code': 'LDP-S1-05', 'niveau_code': 'L1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': False},
    {'nom': 'المجتمع الدولي', 'code': 'LDP-S1-06', 'niveau_code': 'L1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': False},
    {'nom': 'لغة إنجليزية', 'code': 'LDP-S1-07', 'niveau_code': 'L1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': False},
])

# L1 - S2
matieres_data.extend([
    {'nom': 'مدخل إلى القانون 2', 'code': 'LDP-S2-01', 'niveau_code': 'L1', 'semestre': 'S2', 'avec_cm': True, 'avec_td': True},
    {'nom': 'قانون دستوري 2', 'code': 'LDP-S2-02', 'niveau_code': 'L1', 'semestre': 'S2', 'avec_cm': True, 'avec_td': True},
    {'nom': 'تنظيم قضائي 2', 'code': 'LDP-S2-03', 'niveau_code': 'L1', 'semestre': 'S2', 'avec_cm': True, 'avec_td': True},
    {'nom': 'منهجية العلوم القانونية 2', 'code': 'LDP-S2-04', 'niveau_code': 'L1', 'semestre': 'S2', 'avec_cm': True, 'avec_td': False},
    {'nom': 'مدخل إلى الشريعة الإسلامية', 'code': 'LDP-S2-05', 'niveau_code': 'L1', 'semestre': 'S2', 'avec_cm': True, 'avec_td': False},
    {'nom': 'اقتصاد سياسي', 'code': 'LDP-S2-06', 'niveau_code': 'L1', 'semestre': 'S2', 'avec_cm': True, 'avec_td': False},
    {'nom': 'لغة إنجليزية', 'code': 'LDP-S2-07', 'niveau_code': 'L1', 'semestre': 'S2', 'avec_cm': True, 'avec_td': False},
])

# L2 - S3
matieres_data.extend([
    {'nom': 'قانون مدني 1', 'code': 'LDP-S3-01', 'niveau_code': 'L2', 'semestre': 'S3', 'avec_cm': True, 'avec_td': True},
    {'nom': 'قانون جنائي عام', 'code': 'LDP-S3-02', 'niveau_code': 'L2', 'semestre': 'S3', 'avec_cm': True, 'avec_td': True},
    {'nom': 'قانون إداري 1', 'code': 'LDP-S3-03', 'niveau_code': 'L2', 'semestre': 'S3', 'avec_cm': True, 'avec_td': True},
    {'nom': 'قانون تجاري 1', 'code': 'LDP-S3-04', 'niveau_code': 'L2', 'semestre': 'S3', 'avec_cm': True, 'avec_td': True},
    {'nom': 'تقنيات البحث العلمي', 'code': 'LDP-S3-05', 'niveau_code': 'L2', 'semestre': 'S3', 'avec_cm': True, 'avec_td': False},
    {'nom': 'قانون دولي عام', 'code': 'LDP-S3-06', 'niveau_code': 'L2', 'semestre': 'S3', 'avec_cm': True, 'avec_td': False},
    {'nom': 'قانون الأسرة', 'code': 'LDP-S3-07', 'niveau_code': 'L2', 'semestre': 'S3', 'avec_cm': True, 'avec_td': False},
    {'nom': 'لغة إنجليزية', 'code': 'LDP-S3-08', 'niveau_code': 'L2', 'semestre': 'S3', 'avec_cm': True, 'avec_td': False},
])

# L2 - S4
matieres_data.extend([
    {'nom': 'قانون مدني 2', 'code': 'LDP-S4-01', 'niveau_code': 'L2', 'semestre': 'S4', 'avec_cm': True, 'avec_td': True},
    {'nom': 'قانون الإجراءات الجزائية', 'code': 'LDP-S4-02', 'niveau_code': 'L2', 'semestre': 'S4', 'avec_cm': True, 'avec_td': True},
    {'nom': 'قانون الإجراءات المدنية والإدارية', 'code': 'LDP-S4-03', 'niveau_code': 'L2', 'semestre': 'S4', 'avec_cm': True, 'avec_td': True},
    {'nom': 'قانون إداري 2', 'code': 'LDP-S4-04', 'niveau_code': 'L2', 'semestre': 'S4', 'avec_cm': True, 'avec_td': True},
    {'nom': 'تطبيقات الذكاء الاصطناعي في البحث العلمي', 'code': 'LDP-S4-05', 'niveau_code': 'L2', 'semestre': 'S4', 'avec_cm': True, 'avec_td': False},
    {'nom': 'قانون العمل', 'code': 'LDP-S4-06', 'niveau_code': 'L2', 'semestre': 'S4', 'avec_cm': True, 'avec_td': False},
    {'nom': 'حقوق الإنسان', 'code': 'LDP-S4-07', 'niveau_code': 'L2', 'semestre': 'S4', 'avec_cm': True, 'avec_td': False},
    {'nom': 'لغة إنجليزية', 'code': 'LDP-S4-08', 'niveau_code': 'L2', 'semestre': 'S4', 'avec_cm': True, 'avec_td': False},
])

# L3 - S5
matieres_data.extend([
    {'nom': 'القرارات والعقود الإدارية', 'code': 'LDP-S5-01', 'niveau_code': 'L3', 'semestre': 'S5', 'avec_cm': True, 'avec_td': True},
    {'nom': 'الوظيفة العمومية', 'code': 'LDP-S5-02', 'niveau_code': 'L3', 'semestre': 'S5', 'avec_cm': True, 'avec_td': True},
    {'nom': 'قانون دبلوماسي وقنصلي', 'code': 'LDP-S5-03', 'niveau_code': 'L3', 'semestre': 'S5', 'avec_cm': True, 'avec_td': True},
    {'nom': 'مقاولاتية', 'code': 'LDP-S5-04', 'niveau_code': 'L3', 'semestre': 'S5', 'avec_cm': True, 'avec_td': False},
    {'nom': 'قانون جنائي خاص', 'code': 'LDP-S5-05', 'niveau_code': 'L3', 'semestre': 'S5', 'avec_cm': True, 'avec_td': False},
    {'nom': 'قانون دولي إنساني', 'code': 'LDP-S5-06', 'niveau_code': 'L3', 'semestre': 'S5', 'avec_cm': True, 'avec_td': False},
    {'nom': 'مالية عامة', 'code': 'LDP-S5-07', 'niveau_code': 'L3', 'semestre': 'S5', 'avec_cm': True, 'avec_td': False},
    {'nom': 'لغة إنجليزية', 'code': 'LDP-S5-08', 'niveau_code': 'L3', 'semestre': 'S5', 'avec_cm': True, 'avec_td': False},
])

# L3 - S6
matieres_data.extend([
    {'nom': 'منازعات إدارية', 'code': 'LDP-S6-01', 'niveau_code': 'L3', 'semestre': 'S6', 'avec_cm': True, 'avec_td': True},
    {'nom': 'قانون عام اقتصادي', 'code': 'LDP-S6-02', 'niveau_code': 'L3', 'semestre': 'S6', 'avec_cm': True, 'avec_td': True},
    {'nom': 'حريات عامة', 'code': 'LDP-S6-03', 'niveau_code': 'L3', 'semestre': 'S6', 'avec_cm': True, 'avec_td': True},
    {'nom': 'ملتقى', 'code': 'LDP-S6-04', 'niveau_code': 'L3', 'semestre': 'S6', 'avec_cm': True, 'avec_td': False},
    {'nom': 'البيئة والتنمية المستدامة', 'code': 'LDP-S6-05', 'niveau_code': 'L3', 'semestre': 'S6', 'avec_cm': True, 'avec_td': False},
    {'nom': 'قانون جنائي دولي', 'code': 'LDP-S6-06', 'niveau_code': 'L3', 'semestre': 'S6', 'avec_cm': True, 'avec_td': False},
    {'nom': 'قانون جبائي', 'code': 'LDP-S6-07', 'niveau_code': 'L3', 'semestre': 'S6', 'avec_cm': True, 'avec_td': False},
    {'nom': 'لغة إنجليزية', 'code': 'LDP-S6-08', 'niveau_code': 'L3', 'semestre': 'S6', 'avec_cm': True, 'avec_td': False},
])

# Master Droit administratif - S1
matieres_data.extend([
    {'nom': 'النظام القانوني للمرفق العام', 'code': 'MDA-S1-01', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': True},
    {'nom': 'العقود الإدارية', 'code': 'MDA-S1-02', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': True},
    {'nom': 'القضاء الإداري', 'code': 'MDA-S1-03', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': True},
    {'nom': 'منهجية تحرير الوثائق القانونية والقضائية', 'code': 'MDA-S1-04', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': True},
    {'nom': 'الأملاك الوطنية وتهيئة الإقليم', 'code': 'MDA-S1-05', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': False},
    {'nom': 'التسيير العمومي الحديث', 'code': 'MDA-S1-06', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': False},
    {'nom': 'لغة أجنبية (الإنجليزية) 1', 'code': 'MDA-S1-07', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': False},
    {'nom': 'البرمجة', 'code': 'MDA-S1-08', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': False},
])

# Master Droit administratif - S2
matieres_data.extend([
    {'nom': 'سلطات وآليات الضبط الإداري', 'code': 'MDA-S2-01', 'niveau_code': 'M1', 'semestre': 'S2', 'avec_cm': True, 'avec_td': True},
    {'nom': 'قانون الصفقات العمومية', 'code': 'MDA-S2-02', 'niveau_code': 'M1', 'semestre': 'S2', 'avec_cm': True, 'avec_td': True},
    {'nom': 'القضاء الإداري الاستعجالي', 'code': 'MDA-S2-03', 'niveau_code': 'M1', 'semestre': 'S2', 'avec_cm': True, 'avec_td': True},
    {'nom': 'أخلاقيات البحث العلمي', 'code': 'MDA-S2-04', 'niveau_code': 'M1', 'semestre': 'S2', 'avec_cm': True, 'avec_td': True},
    {'nom': 'قانون التعمير وحماية البيئة', 'code': 'MDA-S2-05', 'niveau_code': 'M1', 'semestre': 'S2', 'avec_cm': True, 'avec_td': False},
    {'nom': 'الميزانية والمحاسبة العمومية', 'code': 'MDA-S2-06', 'niveau_code': 'M1', 'semestre': 'S2', 'avec_cm': True, 'avec_td': False},
    {'nom': 'لغة أجنبية (الإنجليزية) 2', 'code': 'MDA-S2-07', 'niveau_code': 'M1', 'semestre': 'S2', 'avec_cm': True, 'avec_td': False},
    {'nom': 'الذكاء الاصطناعي', 'code': 'MDA-S2-08', 'niveau_code': 'M1', 'semestre': 'S2', 'avec_cm': True, 'avec_td': False},
])

# Master Droit administratif - S3
matieres_data.extend([
    {'nom': 'السلطات الإدارية المستقلة', 'code': 'MDA-S3-01', 'niveau_code': 'M2', 'semestre': 'S3', 'avec_cm': True, 'avec_td': True},
    {'nom': 'المسؤولية الإدارية', 'code': 'MDA-S3-02', 'niveau_code': 'M2', 'semestre': 'S3', 'avec_cm': True, 'avec_td': True},
    {'nom': 'المنازعات الإدارية الخاصة', 'code': 'MDA-S3-03', 'niveau_code': 'M2', 'semestre': 'S3', 'avec_cm': True, 'avec_td': True},
    {'nom': 'منهجية إعداد مذكرة', 'code': 'MDA-S3-04', 'niveau_code': 'M2', 'semestre': 'S3', 'avec_cm': True, 'avec_td': True},
    {'nom': 'الجماعات المحلية', 'code': 'MDA-S3-05', 'niveau_code': 'M2', 'semestre': 'S3', 'avec_cm': True, 'avec_td': False},
    {'nom': 'الشفافية ومكافحة الفساد', 'code': 'MDA-S3-06', 'niveau_code': 'M2', 'semestre': 'S3', 'avec_cm': True, 'avec_td': False},
    {'nom': 'لغة أجنبية (الإنجليزية) 3', 'code': 'MDA-S3-07', 'niveau_code': 'M2', 'semestre': 'S3', 'avec_cm': True, 'avec_td': False},
    {'nom': 'البرمجيات الحرة والمصادر المفتوحة', 'code': 'MDA-S3-08', 'niveau_code': 'M2', 'semestre': 'S3', 'avec_cm': True, 'avec_td': False},
])

# Master Droit administratif - S4 (projet/mémoire)
matieres_data.extend([
    {'nom': 'ملتقى', 'code': 'MDA-S4-01', 'niveau_code': 'M2', 'semestre': 'S4', 'avec_cm': True, 'avec_td': False},
    {'nom': 'مذكرة نهاية الدراسة', 'code': 'MDA-S4-02', 'niveau_code': 'M2', 'semestre': 'S4', 'avec_cm': True, 'avec_td': False},
])

# === Import ===
print("\n📥 Import des matières...")
compteur = 0
ignores = 0

for data in matieres_data:
    niveau = niveaux.get(data['niveau_code'])
    if not niveau:
        print(f"   ⚠️ Niveau {data['niveau_code']} non trouvé pour {data['nom']}")
        ignores += 1
        continue
    
    existing = session.query(Matiere).filter_by(
        code_matiere=data['code']
    ).first()
    
    if existing:
        print(f"   ℹ️ Déjà existante : {data['code']} - {data['nom']}")
        ignores += 1
        continue
    
    matiere = Matiere(
        code_matiere=data['code'],
        nom_matiere=data['nom'],
        id_niveau=niveau.id_niveau,
        semestre=data['semestre'],
        avec_cm=data['avec_cm'],
        avec_td=data['avec_td'],
        actif=True
    )
    session.add(matiere)
    compteur += 1
    print(f"   ✅ Ajoutée : {data['code']} - {data['nom']} ({data['niveau_code']} - {data['semestre']})")

session.commit()
print(f"\n📊 Résumé : {compteur} matières ajoutées, {ignores} ignorées")
print("=" * 60)
session.close()
