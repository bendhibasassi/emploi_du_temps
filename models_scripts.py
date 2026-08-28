# models.py - Version simplifiée et fonctionnelle
from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean, 
    Date, Time, ForeignKey, CheckConstraint, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import date, time

Base = declarative_base()

class AnneeUniversitaire(Base):
    __tablename__ = "tbl_annees_univ"
    
    id_annee = Column(Integer, primary_key=True)
    libelle = Column(String(9), unique=True, nullable=False)
    date_debut = Column(Date, nullable=False)
    date_fin = Column(Date, nullable=False)
    active = Column(Boolean, default=False)

class Niveau(Base):
    __tablename__ = "tbl_niveaux"
    
    id_niveau = Column(Integer, primary_key=True)
    code_niveau = Column(String(30), unique=True, nullable=False)
    cycle = Column(String(20), nullable=False)
    specialite = Column(String(150), nullable=False)
    annee_etude = Column(String(10), nullable=False)
    libelle = Column(String(200), unique=True, nullable=False)
    actif = Column(Boolean, default=True)

class Section(Base):
    __tablename__ = "tbl_sections"
    
    id_section = Column(Integer, primary_key=True)
    id_niveau = Column(Integer, ForeignKey("tbl_niveaux.id_niveau"), nullable=False)
    code_section = Column(String(30), nullable=False)
    libelle = Column(String(150), nullable=False)
    effectif = Column(Integer, default=0)
    actif = Column(Boolean, default=True)
    
    __table_args__ = (
        UniqueConstraint("id_niveau", "code_section", name="uq_section_niveau_code"),
    )

class Professeur(Base):
    __tablename__ = "tbl_professeurs"
    
    id_professeur = Column(Integer, primary_key=True)
    nom = Column(String(100), nullable=False)
    prenom = Column(String(100))
    grade = Column(String(100))
    email = Column(String(254), unique=True)
    telephone = Column(String(30))
    actif = Column(Boolean, default=True)
    statut = Column(String(20), nullable=False, default='Permanent')
    peut_cm = Column(Boolean, default=True)
    peut_td = Column(Boolean, default=True)
    peut_tp = Column(Boolean, default=False)

class Matiere(Base):
    __tablename__ = "tbl_matieres"
    
    id_matiere = Column(Integer, primary_key=True)
    code_matiere = Column(String(30), unique=True, nullable=False)
    nom_matiere = Column(String(200), nullable=False)

    # === NOUVEAUX CHAMPS ===
    id_niveau = Column(Integer, ForeignKey('tbl_niveaux.id_niveau'), nullable=True)
    semestre = Column(String(10), nullable=True)
    avec_cm = Column(Boolean, default=True)
    avec_td = Column(Boolean, default=False)
    actif = Column(Boolean, default=True)

    # Relation
    niveau = relationship('Niveau', backref='matieres')

    def __repr__(self):
        return f"<Matiere {self.code_matiere} - {self.nom_matiere}>"

class Salle(Base):
    __tablename__ = "tbl_salles"
    
    id_salle = Column(Integer, primary_key=True)
    code_salle = Column(String(30), unique=True, nullable=False)
    nom_salle = Column(String(150), nullable=False)
    type_salle = Column(String(30), nullable=False)
    capacite = Column(Integer, nullable=False)
    batiment = Column(String(150))
    actif = Column(Boolean, default=True)

class Creneau(Base):
    __tablename__ = "tbl_creneaux"
    
    id_creneau = Column(Integer, primary_key=True)
    heure_debut = Column(Time, nullable=False)
    heure_fin = Column(Time, nullable=False)
    ordre = Column(Integer, unique=True, nullable=False)
    actif = Column(Boolean, default=True)

class Affectation(Base):
    __tablename__ = "tbl_affectations"
    
    id_affectation = Column(Integer, primary_key=True)
    id_annee = Column(Integer, ForeignKey("tbl_annees_univ.id_annee"), nullable=False)
    id_professeur = Column(Integer, ForeignKey("tbl_professeurs.id_professeur"), nullable=False)
    id_matiere = Column(Integer, ForeignKey("tbl_matieres.id_matiere"), nullable=False)
    id_section = Column(Integer, ForeignKey("tbl_sections.id_section"), nullable=False)
    semestre = Column(Integer, nullable=False)
    type_enseignement = Column(String(10), nullable=False)
    nb_seances_semaine = Column(Integer, default=1)
    duree_seance_minutes = Column(Integer, default=90)
    volume_total_minutes = Column(Integer)
    priorite = Column(Integer, default=50)
    actif = Column(Boolean, default=True)

class Seance(Base):
    __tablename__ = "tbl_seances"
    
    id_seance = Column(Integer, primary_key=True)
    id_annee = Column(Integer, nullable=False)
    id_affectation = Column(Integer, ForeignKey("tbl_affectations.id_affectation"), nullable=False)
    jour = Column(Integer, nullable=False)  # 1=Lundi, 7=Dimanche
    id_creneau = Column(Integer, ForeignKey("tbl_creneaux.id_creneau"), nullable=False)
    id_salle = Column(Integer, ForeignKey("tbl_salles.id_salle"), nullable=False)
    semaine_type = Column(String(10), default="TOUTES")
    verrouillee = Column(Boolean, default=False)
    origine = Column(String(10), default="AUTO")
    statut = Column(String(15), default="PROPOSEE")
    
    __table_args__ = (
        UniqueConstraint("id_annee", "jour", "id_creneau", "id_salle", "semaine_type", 
                        name="uq_seance_salle"),
    )

class Indisponibilite(Base):
    __tablename__ = "tbl_indisponibilites"

    id_indisponibilite = Column(Integer, primary_key=True)
    id_annee = Column(Integer, ForeignKey("tbl_annees_univ.id_annee"), nullable=False)
    id_professeur = Column(Integer, ForeignKey("tbl_professeurs.id_professeur"), nullable=False)
    jour = Column(Integer, nullable=False)
    id_creneau = Column(Integer, ForeignKey("tbl_creneaux.id_creneau"), nullable=False)
    type_contrainte = Column(String(15), nullable=False, default="INTERDIT")
    commentaire = Column(String(500))
    actif = Column(Boolean, default=True)

    __table_args__ = (
        UniqueConstraint("id_annee", "id_professeur", "jour", "id_creneau",
                         name="uq_indisponibilite_unique"),
        CheckConstraint("jour BETWEEN 1 AND 7", name="ck_indisponibilite_jour"),
        CheckConstraint("type_contrainte IN ('INTERDIT', 'EVITER', 'PREFERE')",
                        name="ck_indisponibilite_type"),
    )
