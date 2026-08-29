# verifier_matieres_107.py
"""
Script pour vérifier et ajouter les 107 matières du document
"""
from sqlalchemy import create_engine
from config import DATABASE_URI
from sqlalchemy.orm import sessionmaker
from app.models import Matiere, Niveau
import os

print("=" * 70)
print("📚 VÉRIFICATION DES 107 MATIÈRES DU DOCUMENT")
print("=" * 70)

engine = create_engine(DATABASE_URI)
Session = sessionmaker(bind=engine)
session = Session()

# === Récupérer les niveaux ===
print("\n🔍 Récupération des niveaux...")
niveaux = {}
for niveau in session.query(Niveau).all():
    niveaux[niveau.code_niveau] = niveau
    print(f"   ✅ {niveau.code_niveau} : {niveau.libelle} (ID: {niveau.id_niveau})")

# === Liste des 107 matières (ID 1 à 107) ===
matieres_data = [
    # L3 Droit privé (IDs 1-8)
    {'nom': 'القانون المقارن', 'niveau_code': 'L3', 'semestre': 'S5', 'avec_cm': True, 'avec_td': True},
    {'nom': 'القانون الدولي الخاص', 'niveau_code': 'L3', 'semestre': 'S5', 'avec_cm': True, 'avec_td': True},
    {'nom': 'طرق الإثبات والتنفيذ', 'niveau_code': 'L3', 'semestre': 'S5', 'avec_cm': True, 'avec_td': True},
    {'nom': 'الشركات التجارية', 'niveau_code': 'L3', 'semestre': 'S5', 'avec_cm': True, 'avec_td': True},
    {'nom': 'عقود خاصة', 'niveau_code': 'L3', 'semestre': 'S5', 'avec_cm': True, 'avec_td': True},
    {'nom': 'مواريث', 'niveau_code': 'L3', 'semestre': 'S5', 'avec_cm': True, 'avec_td': True},
    {'nom': 'جرائم الفساد', 'niveau_code': 'L3', 'semestre': 'S5', 'avec_cm': True, 'avec_td': True},
    {'nom': 'مصطلحات قانونية', 'niveau_code': 'L3', 'semestre': 'S5', 'avec_cm': True, 'avec_td': False},
    # L3 Droit public (IDs 9-16)
    {'nom': 'القانون المقارن', 'niveau_code': 'L3', 'semestre': 'S5', 'avec_cm': True, 'avec_td': True},
    {'nom': 'الوظيفة العامة', 'niveau_code': 'L3', 'semestre': 'S5', 'avec_cm': True, 'avec_td': True},
    {'nom': 'قانون العلاقات الدولية', 'niveau_code': 'L3', 'semestre': 'S5', 'avec_cm': True, 'avec_td': True},
    {'nom': 'القرارات والعقود الإدارية', 'niveau_code': 'L3', 'semestre': 'S5', 'avec_cm': True, 'avec_td': True},
    {'nom': 'المالية العامة', 'niveau_code': 'L3', 'semestre': 'S5', 'avec_cm': True, 'avec_td': True},
    {'nom': 'القانون الدولي الإنساني', 'niveau_code': 'L3', 'semestre': 'S5', 'avec_cm': True, 'avec_td': True},
    {'nom': 'قانون البيئة والتنمية المستدامة', 'niveau_code': 'L3', 'semestre': 'S5', 'avec_cm': True, 'avec_td': True},
    {'nom': 'مصطلحات قانونية', 'niveau_code': 'L3', 'semestre': 'S5', 'avec_cm': True, 'avec_td': False},
    # M1 Droit pénal (IDs 17-23)
    {'nom': 'قانون الإجراءات الجزائية', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': True},
    {'nom': 'القانون الجنائي الخاص 1', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': True},
    {'nom': 'جرائم الفساد ومكافحته 1', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': True},
    {'nom': 'منهجية البحث العلمي 1', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': False},
    {'nom': 'الإثبات الجنائي', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': True},
    {'nom': 'الجرائم الأسرية', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': True},
    {'nom': 'مصطلحات قانونية', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': False},
    # M2 Droit pénal (IDs 24-30)
    {'nom': 'القانون الجنائي للمخدرات', 'niveau_code': 'M2', 'semestre': 'S3', 'avec_cm': True, 'avec_td': True},
    {'nom': 'القانون الجنائي للأعمال', 'niveau_code': 'M2', 'semestre': 'S3', 'avec_cm': True, 'avec_td': True},
    {'nom': 'الجرائم المعلوماتية', 'niveau_code': 'M2', 'semestre': 'S3', 'avec_cm': True, 'avec_td': True},
    {'nom': 'منهجية إعداد مذكرة', 'niveau_code': 'M2', 'semestre': 'S3', 'avec_cm': True, 'avec_td': False},
    {'nom': 'العدالة الجنائية الدولية', 'niveau_code': 'M2', 'semestre': 'S3', 'avec_cm': True, 'avec_td': True},
    {'nom': 'الفقه الجنائي الإسلامي', 'niveau_code': 'M2', 'semestre': 'S3', 'avec_cm': True, 'avec_td': True},
    {'nom': 'مصطلحات قانونية', 'niveau_code': 'M2', 'semestre': 'S3', 'avec_cm': True, 'avec_td': False},
    # M1 Droit international public (IDs 31-37)
    {'nom': 'منهجية البحث العلمي 1', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': False},
    {'nom': 'تاريخ العلاقات الدولية', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': True},
    {'nom': 'تنازع الاختصاص القضائي الدولي', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': True},
    {'nom': 'القانون الدولي للبيئة', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': True},
    {'nom': 'المعاهدات الدولية', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': True},
    {'nom': 'القانون الدولي الإنساني ومسؤولية الحماية', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': True},
    {'nom': 'مصطلحات قانونية', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': False},
    # M2 Droit international public (IDs 38-44)
    {'nom': 'القانون الأوروبي', 'niveau_code': 'M2', 'semestre': 'S3', 'avec_cm': True, 'avec_td': True},
    {'nom': 'منهجية إعداد مذكرة', 'niveau_code': 'M2', 'semestre': 'S3', 'avec_cm': True, 'avec_td': False},
    {'nom': 'المسؤولية الدولية', 'niveau_code': 'M2', 'semestre': 'S3', 'avec_cm': True, 'avec_td': True},
    {'nom': 'التحكيم الدولي', 'niveau_code': 'M2', 'semestre': 'S3', 'avec_cm': True, 'avec_td': True},
    {'nom': 'قانون البحار', 'niveau_code': 'M2', 'semestre': 'S3', 'avec_cm': True, 'avec_td': True},
    {'nom': 'النظام القانوني للاستثمار الدولي', 'niveau_code': 'M2', 'semestre': 'S3', 'avec_cm': True, 'avec_td': True},
    {'nom': 'مصطلحات قانونية', 'niveau_code': 'M2', 'semestre': 'S3', 'avec_cm': True, 'avec_td': False},
    # M1 Gouvernance (IDs 45-54)
    {'nom': 'اتفاقيات مكافحة الفساد', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': True},
    {'nom': 'قانون مكافحة الفساد', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': True},
    {'nom': 'الحكم الراشد', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': True},
    {'nom': 'قانون المؤسسة الناشئة', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': True},
    {'nom': 'الإجرام المالي والاقتصادي', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': True},
    {'nom': 'منهجية البحث العلمي', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': False},
    {'nom': 'الرقابة على دستورية القوانين', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': True},
    {'nom': 'التدابير الوقائية من الفساد', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': True},
    {'nom': 'حوكمة الصفقات العمومية', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': True},
    {'nom': 'مصطلحات قانونية', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': False},
    # M2 Gouvernance (IDs 55-64)
    {'nom': 'جرائم تبييض الأموال', 'niveau_code': 'M2', 'semestre': 'S3', 'avec_cm': True, 'avec_td': True},
    {'nom': 'الإدارة الإلكترونية', 'niveau_code': 'M2', 'semestre': 'S3', 'avec_cm': True, 'avec_td': True},
    {'nom': 'المكافحة الإجرائية للفساد', 'niveau_code': 'M2', 'semestre': 'S3', 'avec_cm': True, 'avec_td': True},
    {'nom': 'المحاكمة العادلة', 'niveau_code': 'M2', 'semestre': 'S3', 'avec_cm': True, 'avec_td': True},
    {'nom': 'نزاهة وشفافية الانتخابات', 'niveau_code': 'M2', 'semestre': 'S3', 'avec_cm': True, 'avec_td': True},
    {'nom': 'النظام القانوني الدولي لاسترداد الأموال', 'niveau_code': 'M2', 'semestre': 'S3', 'avec_cm': True, 'avec_td': True},
    {'nom': 'حقوق المؤلف والسرقة العلمية', 'niveau_code': 'M2', 'semestre': 'S3', 'avec_cm': True, 'avec_td': True},
    {'nom': 'منهجية إعداد مذكرة ماستر', 'niveau_code': 'M2', 'semestre': 'S3', 'avec_cm': True, 'avec_td': False},
    {'nom': 'الأمن السيبراني', 'niveau_code': 'M2', 'semestre': 'S3', 'avec_cm': True, 'avec_td': True},
    {'nom': 'مصطلحات قانونية', 'niveau_code': 'M2', 'semestre': 'S3', 'avec_cm': True, 'avec_td': False},
    # M1 Droit des affaires (IDs 65-72)
    {'nom': 'التحكيم التجاري', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': True},
    {'nom': 'قانون المنافسة', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': True},
    {'nom': 'منازعات تجارية', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': True},
    {'nom': 'عقود الأعمال', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': True},
    {'nom': 'تحرير الرسائل والعرائض', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': False},
    {'nom': 'منهجية البحث العلمي 2', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': False},
    {'nom': 'مسؤولية الناقل', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': True},
    {'nom': 'مصطلحات قانونية', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': False},
    # M2 Droit des affaires (IDs 73-79)
    {'nom': 'مسؤولية مسيري الشركات', 'niveau_code': 'M2', 'semestre': 'S2', 'avec_cm': True, 'avec_td': True},
    {'nom': 'قانون الممارسات التجارية', 'niveau_code': 'M2', 'semestre': 'S2', 'avec_cm': True, 'avec_td': True},
    {'nom': 'التجارة الإلكترونية', 'niveau_code': 'M2', 'semestre': 'S2', 'avec_cm': True, 'avec_td': True},
    {'nom': 'قانون الملكية الصناعية', 'niveau_code': 'M2', 'semestre': 'S2', 'avec_cm': True, 'avec_td': True},
    {'nom': 'منهجية إعداد البحوث', 'niveau_code': 'M2', 'semestre': 'S2', 'avec_cm': True, 'avec_td': False},
    {'nom': 'قانون الجمارك', 'niveau_code': 'M2', 'semestre': 'S2', 'avec_cm': True, 'avec_td': True},
    {'nom': 'مصطلحات قانونية', 'niveau_code': 'M2', 'semestre': 'S2', 'avec_cm': True, 'avec_td': False},
    # M1 Droit immobilier (IDs 80-86)
    {'nom': 'قانون الأملاك الوطنية', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': True},
    {'nom': 'قانون العمران والمدينة', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': True},
    {'nom': 'طرق اكتساب الملكية', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': True},
    {'nom': 'التوثيق والشهر العقاريين', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': True},
    {'nom': 'قانون الساحل', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': True},
    {'nom': 'منهجية البحث العلمي 1', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': False},
    {'nom': 'مصطلحات قانونية', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': False},
    # M2 Droit immobilier (IDs 87-93)
    {'nom': 'حقوق الامتياز', 'niveau_code': 'M2', 'semestre': 'S2', 'avec_cm': True, 'avec_td': True},
    {'nom': 'حماية الملكية العقارية', 'niveau_code': 'M2', 'semestre': 'S2', 'avec_cm': True, 'avec_td': True},
    {'nom': 'المنازعات العقارية', 'niveau_code': 'M2', 'semestre': 'S2', 'avec_cm': True, 'avec_td': True},
    {'nom': 'منهجية إعداد مذكرة', 'niveau_code': 'M2', 'semestre': 'S2', 'avec_cm': True, 'avec_td': False},
    {'nom': 'حماية المستهلك العقاري', 'niveau_code': 'M2', 'semestre': 'S2', 'avec_cm': True, 'avec_td': True},
    {'nom': 'العقار البيئي', 'niveau_code': 'M2', 'semestre': 'S2', 'avec_cm': True, 'avec_td': True},
    {'nom': 'مصطلحات قانونية', 'niveau_code': 'M2', 'semestre': 'S2', 'avec_cm': True, 'avec_td': False},
    # M1 Droit des contrats (IDs 94-100)
    {'nom': 'التأمينات الشخصية', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': True},
    {'nom': 'منهجية البحث العلمي 1', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': False},
    {'nom': 'نظام التعويض', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': True},
    {'nom': 'المسؤولية العقدية', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': True},
    {'nom': 'الشكلية في العقود', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': True},
    {'nom': 'التحكيم التجاري', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': True},
    {'nom': 'مصطلحات قانونية', 'niveau_code': 'M1', 'semestre': 'S1', 'avec_cm': True, 'avec_td': False},
    # M2 Droit des contrats (IDs 101-107)
    {'nom': 'التأمينات العينية', 'niveau_code': 'M2', 'semestre': 'S2', 'avec_cm': True, 'avec_td': True},
    {'nom': 'قانون مكافحة الفساد', 'niveau_code': 'M2', 'semestre': 'S2', 'avec_cm': True, 'avec_td': True},
    {'nom': 'النظام القانوني للشركات', 'niveau_code': 'M2', 'semestre': 'S2', 'avec_cm': True, 'avec_td': True},
    {'nom': 'المسؤولية الطبية', 'niveau_code': 'M2', 'semestre': 'S2', 'avec_cm': True, 'avec_td': True},
    {'nom': 'عقود التبرعات', 'niveau_code': 'M2', 'semestre': 'S2', 'avec_cm': True, 'avec_td': True},
    {'nom': 'منهجية إعداد مذكرة', 'niveau_code': 'M2', 'semestre': 'S2', 'avec_cm': True, 'avec_td': False},
    {'nom': 'مصطلحات قانونية', 'niveau_code': 'M2', 'semestre': 'S2', 'avec_cm': True, 'avec_td': False},
]

# === Vérifier et ajouter ===
print("\n📥 Vérification des matières...")
compteur_ajoutees = 0
compteur_existantes = 0
compteur_erreurs = 0

for data in matieres_data:
    niveau = niveaux.get(data['niveau_code'])
    if not niveau:
        print(f"   ⚠️ Niveau {data['niveau_code']} non trouvé pour {data['nom']}")
        compteur_erreurs += 1
        continue
    
    # Vérifier si la matière existe déjà
    existing = session.query(Matiere).filter_by(
        nom_matiere=data['nom'],
        id_niveau=niveau.id_niveau
    ).first()
    
    if existing:
        print(f"   ℹ️ Déjà existante : {data['nom']} ({data['niveau_code']})")
        compteur_existantes += 1
        continue
    
    # Ajouter la matière
    code = f"{data['niveau_code']}-{data['semestre']}-{compteur_ajoutees+1:03d}"
    matiere = Matiere(
        code_matiere=code,
        nom_matiere=data['nom'],
        id_niveau=niveau.id_niveau,
        semestre=data['semestre'],
        avec_cm=data['avec_cm'],
        avec_td=data['avec_td'],
        actif=True
    )
    session.add(matiere)
    compteur_ajoutees += 1
    print(f"   ✅ Ajoutée : {data['nom']} ({data['niveau_code']} - {data['semestre']})")

session.commit()
print(f"\n📊 Résumé : {compteur_ajoutees} ajoutées, {compteur_existantes} déjà existantes, {compteur_erreurs} erreurs")
print("=" * 70)
session.close()
