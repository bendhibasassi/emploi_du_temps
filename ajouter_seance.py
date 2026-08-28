# ajouter_seance.py - Version avec vérification des conflits
from models_scripts import (
    Seance, Affectation, Professeur, Matiere, 
    Section, Salle, Creneau, AnneeUniversitaire
)
from sqlalchemy import create_engine, and_, or_
from sqlalchemy.orm import sessionmaker
from datetime import time, datetime

print("📅 Ajout d'une séance avec vérification des conflits...")

# Connexion à la base
engine = create_engine("sqlite:///emploi_du_temps.db")
Session = sessionmaker(bind=engine)

def verifier_conflits(session, id_annee, id_affectation, jour, id_creneau, id_salle):
    """
    Vérifie tous les conflits possibles avant d'ajouter une séance.
    Retourne (ok, liste_des_erreurs)
    """
    erreurs = []
    
    # Récupère l'affectation pour avoir le prof et la section
    affectation = session.query(Affectation).filter_by(id_affectation=id_affectation).first()
    if affectation is None:
        return False, ["❌ L'affectation n'existe pas !"]
    
    # Récupère les informations pour les messages
    prof = session.query(Professeur).filter_by(id_professeur=affectation.id_professeur).first()
    section = session.query(Section).filter_by(id_section=affectation.id_section).first()
    salle = session.query(Salle).filter_by(id_salle=id_salle).first()
    creneau = session.query(Creneau).filter_by(id_creneau=id_creneau).first()
    
    # 1. Vérification : La salle existe
    if salle is None:
        erreurs.append("❌ La salle n'existe pas !")
    else:
        # 2. Vérification : La capacité de la salle est suffisante
        if salle.capacite < section.effectif:
            erreurs.append(f"❌ Salle trop petite ! Capacité: {salle.capacite}, Effectif: {section.effectif}")
    
    # 3. Vérification : Le créneau existe
    if creneau is None:
        erreurs.append("❌ Le créneau horaire n'existe pas !")
    
    # 4. Vérification : Le professeur n'est pas déjà occupé
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
        prof_occupe_info = session.query(Professeur).filter_by(
            id_professeur=affectation.id_professeur
        ).first()
        erreurs.append(f"❌ Professeur {prof_occupe_info.prenom} {prof_occupe_info.nom} déjà occupé !")
    
    # 5. Vérification : La section n'est pas déjà occupée
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
        section_info = session.query(Section).filter_by(
            id_section=affectation.id_section
        ).first()
        erreurs.append(f"❌ Section {section_info.libelle} déjà occupée !")
    
    # 6. Vérification : La salle n'est pas déjà réservée
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
        salle_info = session.query(Salle).filter_by(id_salle=id_salle).first()
        erreurs.append(f"❌ Salle {salle_info.nom_salle} déjà réservée !")
    
    # 7. Vérification : Le professeur n'a pas d'indisponibilité (si la table existe)
    # À ajouter quand tbl_indisponibilites sera créée
    
    # Retourne le résultat
    if erreurs:
        return False, erreurs
    else:
        return True, []
    
def ajouter_seance():
    with Session() as session:
        try:
            # ===== PARAMÈTRES À MODIFIER =====
            id_annee = 1              # Année 2025-2026
            id_affectation = 2        # ID de l'affectation (Dupont ou Martin)
            jour = 3                  # 1=Lundi, 2=Mardi, ..., 7=Dimanche
            id_creneau = 2            # 1=8h, 2=9h30, 3=11h, 4=13h, 5=14h30
            id_salle = 1              # ID de la salle
            semaine_type = "TOUTES"   # "TOUTES", "PAIRE", "IMPAIRE"
            # =================================
            
            print("\n📖 Vérification des données...")
            
            # Récupère les informations pour l'affichage
            affectation = session.query(Affectation).filter_by(id_affectation=id_affectation).first()
            if affectation is None:
                print("❌ Affectation introuvable !")
                return
            
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
            
            # === VÉRIFICATION DES CONFLITS ===
            print("\n🔍 Vérification des conflits...")
            ok, erreurs = verifier_conflits(
                session, id_annee, id_affectation, 
                jour, id_creneau, id_salle
            )
            
            if not ok:
                print("\n❌ CONFLITS DÉTECTÉS :")
                for erreur in erreurs:
                    print(f"   {erreur}")
                print("\n⚠️ Séance NON ajoutée !")
                return
            
            print("✅ Aucun conflit détecté !")
            
            # === AJOUT DE LA SÉANCE ===
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
            
            # Affichage du résultat
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
            print(f"   - ID Séance : {seance.id_seance}")
            print("="*50)
            
        except Exception as e:
            session.rollback()
            print(f"❌ Erreur inattendue : {e}")

if __name__ == "__main__":
    ajouter_seance()