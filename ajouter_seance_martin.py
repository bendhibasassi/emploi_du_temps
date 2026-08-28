# ajouter_seance_martin.py
from models_scripts import (
    Seance, Affectation, Professeur, Matiere, 
    Section, Salle, Creneau
)
from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker

print("📅 Ajout d'une séance pour Sophie Martin...")

engine = create_engine("sqlite:///emploi_du_temps.db")
Session = sessionmaker(bind=engine)

def verifier_conflits(session, id_annee, id_affectation, jour, id_creneau, id_salle):
    erreurs = []
    
    affectation = session.query(Affectation).filter_by(id_affectation=id_affectation).first()
    if affectation is None:
        return False, ["❌ L'affectation n'existe pas !"]
    
    prof = session.query(Professeur).filter_by(id_professeur=affectation.id_professeur).first()
    section = session.query(Section).filter_by(id_section=affectation.id_section).first()
    salle = session.query(Salle).filter_by(id_salle=id_salle).first()
    
    if salle is None:
        erreurs.append("❌ La salle n'existe pas !")
    elif salle.capacite < section.effectif:
        erreurs.append(f"❌ Salle trop petite ! Capacité: {salle.capacite}, Effectif: {section.effectif}")
    
    # Professeur occupé ?
    prof_occupe = session.query(Seance).join(
        Affectation, Seance.id_affectation == Affectation.id_affectation
    ).filter(
        and_(
            Seance.id_annee == id_annee,
            Seance.jour == jour,
            Seance.id_creneau == id_creneau,
            Affectation.id_professeur == affectation.id_professeur,
            Seance.statut != "ANNULEE"
        )
    ).first()
    if prof_occupe:
        erreurs.append(f"❌ Professeur {prof.prenom} {prof.nom} déjà occupé !")
    
    # Section occupée ?
    section_occupee = session.query(Seance).join(
        Affectation, Seance.id_affectation == Affectation.id_affectation
    ).filter(
        and_(
            Seance.id_annee == id_annee,
            Seance.jour == jour,
            Seance.id_creneau == id_creneau,
            Affectation.id_section == affectation.id_section,
            Seance.statut != "ANNULEE"
        )
    ).first()
    if section_occupee:
        erreurs.append(f"❌ Section {section.libelle} déjà occupée !")
    
    # Salle occupée ?
    salle_occupee = session.query(Seance).filter(
        and_(
            Seance.id_annee == id_annee,
            Seance.jour == jour,
            Seance.id_creneau == id_creneau,
            Seance.id_salle == id_salle,
            Seance.statut != "ANNULEE"
        )
    ).first()
    if salle_occupee:
        erreurs.append(f"❌ Salle {salle.nom_salle} déjà réservée !")
    
    return len(erreurs) == 0, erreurs

with Session() as session:
    try:
        # ===== PARAMÈTRES POUR SOPHIE MARTIN =====
        id_annee = 1              # Année 2025-2026
        id_affectation = 2        # Sophie Martin (ID 2)
        jour = 3                  # Mercredi
        id_creneau = 2            # 09:30 - 11:00
        id_salle = 1              # Amphi A
        semaine_type = "TOUTES"
        # =========================================
        
        # Récupère les informations pour l'affichage
        affectation = session.query(Affectation).filter_by(id_affectation=id_affectation).first()
        if affectation is None:
            print("❌ Affectation introuvable !")
            print("   IDs disponibles : 1 = Dupont, 2 = Martin")
            exit()
        
        prof = session.query(Professeur).filter_by(id_professeur=affectation.id_professeur).first()
        matiere = session.query(Matiere).filter_by(id_matiere=affectation.id_matiere).first()
        section = session.query(Section).filter_by(id_section=affectation.id_section).first()
        salle = session.query(Salle).filter_by(id_salle=id_salle).first()
        creneau = session.query(Creneau).filter_by(id_creneau=id_creneau).first()
        
        print(f"\n📚 Détails du cours à placer :")
        print(f"   - Professeur : {prof.prenom} {prof.nom}")
        print(f"   - Matière : {matiere.nom_matiere}")
        print(f"   - Section : {section.libelle} ({section.effectif} étudiants)")
        print(f"   - Salle : {salle.nom_salle} ({salle.capacite} places)")
        print(f"   - Jour : {['Lundi','Mardi','Mercredi','Jeudi','Vendredi','Samedi','Dimanche'][jour-1]}")
        print(f"   - Horaire : {creneau.heure_debut} - {creneau.heure_fin}")
        
        # Vérification des conflits
        print("\n🔍 Vérification des conflits...")
        ok, erreurs = verifier_conflits(session, id_annee, id_affectation, jour, id_creneau, id_salle)
        
        if not ok:
            print("\n❌ CONFLITS DÉTECTÉS :")
            for erreur in erreurs:
                print(f"   {erreur}")
            print("\n⚠️ Séance NON ajoutée !")
            exit()
        
        print("✅ Aucun conflit détecté !")
        
        # Ajout de la séance
        seance = Seance(
            id_annee=id_annee,
            id_affectation=id_affectation,
            jour=jour,
            id_creneau=id_creneau,
            id_salle=id_salle,
            semaine_type=semaine_type,
            statut="PROPOSEE"
        )
        session.add(seance)
        session.commit()
        
        print("\n" + "="*50)
        print("✅ SÉANCE AJOUTÉE AVEC SUCCÈS !")
        print("="*50)
        print(f"📋 Récapitulatif :")
        print(f"   - Professeur : {prof.prenom} {prof.nom}")
        print(f"   - Matière : {matiere.nom_matiere}")
        print(f"   - Section : {section.libelle}")
        print(f"   - Jour : {['Lundi','Mardi','Mercredi','Jeudi','Vendredi','Samedi','Dimanche'][jour-1]}")
        print(f"   - Horaire : {creneau.heure_debut} - {creneau.heure_fin}")
        print(f"   - Salle : {salle.nom_salle} ({salle.capacite} places)")
        print("="*50)
        
    except Exception as e:
        session.rollback()
        print(f"❌ Erreur inattendue : {e}")
        