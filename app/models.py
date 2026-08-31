# app/models.py
from app import db
from datetime import date, time, datetime

class AnneeUniversitaire(db.Model):
    __tablename__ = "tbl_annees_univ"
    
    id_annee = db.Column(db.Integer, primary_key=True)
    libelle = db.Column(db.String(9), unique=True, nullable=False)
    date_debut = db.Column(db.Date, nullable=False)
    date_fin = db.Column(db.Date, nullable=False)
    active = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f"<Annee {self.libelle}>"

class Niveau(db.Model):
    __tablename__ = "tbl_niveaux"
    
    id_niveau = db.Column(db.Integer, primary_key=True)
    code_niveau = db.Column(db.String(30), unique=True, nullable=False)
    cycle = db.Column(db.String(20), nullable=False)
    specialite = db.Column(db.String(150), nullable=False)
    annee_etude = db.Column(db.String(10), nullable=False)
    libelle = db.Column(db.String(200), unique=True, nullable=False)
    actif = db.Column(db.Boolean, default=True)

class Section(db.Model):
    __tablename__ = "tbl_sections"
    
    id_section = db.Column(db.Integer, primary_key=True)
    id_niveau = db.Column(db.Integer, db.ForeignKey('tbl_niveaux.id_niveau'), nullable=False)
    code_section = db.Column(db.String(30), nullable=False)
    libelle = db.Column(db.String(150), nullable=False)
    effectif = db.Column(db.Integer, default=0)
    actif = db.Column(db.Boolean, default=True)

    niveau = db.relationship('Niveau', backref='sections', lazy=True)
    groupes = db.relationship('Groupe', back_populates='section', lazy=True)
    
    __table_args__ = (
        db.UniqueConstraint('id_niveau', 'code_section', name='uq_section_niveau_code'),
    )
    
    def __repr__(self):
        return f"<Section {self.code_section}>"


class Groupe(db.Model):
    __tablename__ = "tbl_groupes"

    id_groupe = db.Column(db.Integer, primary_key=True)
    id_section = db.Column(db.Integer, db.ForeignKey('tbl_sections.id_section'), nullable=False)
    code_groupe = db.Column(db.String(20), nullable=False)
    nom_groupe = db.Column(db.String(100), nullable=False)
    effectif = db.Column(db.Integer, nullable=True)
    actif = db.Column(db.Boolean, default=True)

    # Relation avec Section
    section = db.relationship('Section', back_populates='groupes', lazy=True)

    __table_args__ = (
        db.UniqueConstraint('id_section', 'code_groupe', name='uq_section_code_groupe'),
    )

    def __repr__(self):
        return f"<Groupe {self.code_groupe} - {self.nom_groupe}>"


class Professeur(db.Model):
    __tablename__ = "tbl_professeurs"
    
    id_professeur = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100))
    grade = db.Column(db.String(100))
    email = db.Column(db.String(254), unique=True)
    telephone = db.Column(db.String(30))
    actif = db.Column(db.Boolean, default=True)

    # === NOUVEAUX CHAMPS ===
    statut = db.Column(db.String(20), nullable=False, default='Permanent')
    peut_cm = db.Column(db.Boolean, default=True)
    peut_td = db.Column(db.Boolean, default=True)
    peut_tp = db.Column(db.Boolean, default=False)

    # Relation
    affectations = db.relationship('Affectation', back_populates='professeur', lazy=True)

    def __repr__(self):
        return f"<Professeur {self.nom} ({self.statut})>"

class Matiere(db.Model):
    __tablename__ = "tbl_matieres"
    
    id_matiere = db.Column(db.Integer, primary_key=True)
    code_matiere = db.Column(db.String(30), unique=True, nullable=False)
    nom_matiere = db.Column(db.String(200), nullable=False)

    # === NOUVEAUX CHAMPS ===
    id_niveau = db.Column(db.Integer, db.ForeignKey('tbl_niveaux.id_niveau'), nullable=True)
    semestre = db.Column(db.String(10), nullable=True)
    avec_cm = db.Column(db.Boolean, default=True)
    avec_td = db.Column(db.Boolean, default=False)
    actif = db.Column(db.Boolean, default=True)

    # Relation
    niveau = db.relationship('Niveau', backref='matieres', lazy=True)
    
    def __repr__(self):
        return f"<Matiere {self.code_matiere} - {self.nom_matiere}>"

class Salle(db.Model):
    __tablename__ = "tbl_salles"
    
    id_salle = db.Column(db.Integer, primary_key=True)
    code_salle = db.Column(db.String(30), unique=True, nullable=False)
    nom_salle = db.Column(db.String(150), nullable=False)
    type_salle = db.Column(db.String(30), nullable=False)
    capacite = db.Column(db.Integer, nullable=True)
    batiment = db.Column(db.String(150))
    actif = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f"<Salle {self.nom_salle}>"

class Creneau(db.Model):
    __tablename__ = "tbl_creneaux"
    
    id_creneau = db.Column(db.Integer, primary_key=True)
    heure_debut = db.Column(db.Time, nullable=False)
    heure_fin = db.Column(db.Time, nullable=False)
    ordre = db.Column(db.Integer, unique=True, nullable=False)
    actif = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f"<Creneau {self.heure_debut}-{self.heure_fin}>"

class Affectation(db.Model):
    __tablename__ = "tbl_affectations"
    
    id_affectation = db.Column(db.Integer, primary_key=True)
    id_annee = db.Column(db.Integer, db.ForeignKey('tbl_annees_univ.id_annee'), nullable=False)
    id_professeur = db.Column(db.Integer, db.ForeignKey('tbl_professeurs.id_professeur'), nullable=False)
    id_matiere = db.Column(db.Integer, db.ForeignKey('tbl_matieres.id_matiere'), nullable=False)
    id_section = db.Column(db.Integer, db.ForeignKey('tbl_sections.id_section'), nullable=False)
    id_groupe = db.Column(db.Integer, db.ForeignKey('tbl_groupes.id_groupe'), nullable=True)
    semestre = db.Column(db.Integer, nullable=False)
    type_enseignement = db.Column(db.String(10), nullable=False)
    nb_seances_semaine = db.Column(db.Integer, default=1)
    duree_seance_minutes = db.Column(db.Integer, default=90)
    volume_total_minutes = db.Column(db.Integer)
    priorite = db.Column(db.Integer, default=50)
    actif = db.Column(db.Boolean, default=True)
    
    # Relations
    groupe = db.relationship('Groupe', backref='affectations', lazy=True)
    professeur = db.relationship('Professeur', back_populates='affectations', lazy=True)
    matiere = db.relationship('Matiere', backref='affectations', lazy=True)
    section = db.relationship('Section', backref='affectations', lazy=True)
    annee = db.relationship('AnneeUniversitaire', backref='affectations', lazy=True)

    def calculer_planification(self):
        """Calcule la charge hebdomadaire couverte par les séances réelles."""
        try:
            attendu = float(self.nb_seances_semaine)
        except (TypeError, ValueError):
            attendu = 1.0
        if attendu <= 0:
            attendu = 1.0

        poids_semaine = {
            'TOUTES': 1.0,
            'PAIRE': 0.5,
            'IMPAIRE': 0.5,
        }
        planifie = sum(
            poids_semaine.get(seance.semaine_type, 0.0)
            for seance in self.seances
            if seance.statut != 'ANNULEE'
        )

        if planifie == 0:
            statut = 'SANS_SEANCE'
        elif planifie < attendu:
            statut = 'PARTIEL'
        else:
            statut = 'COMPLET'

        return {
            'planifie': planifie,
            'attendu': attendu,
            'statut': statut,
        }

    @property
    def planification(self):
        """Expose le statut de planification aux vues et autres usages métier."""
        return self.calculer_planification()

class Seance(db.Model):
    __tablename__ = "tbl_seances"
    
    id_seance = db.Column(db.Integer, primary_key=True)
    id_annee = db.Column(db.Integer, db.ForeignKey('tbl_annees_univ.id_annee'), nullable=False)
    id_affectation = db.Column(db.Integer, db.ForeignKey('tbl_affectations.id_affectation'), nullable=False)
    jour = db.Column(db.Integer, nullable=False)
    id_creneau = db.Column(db.Integer, db.ForeignKey('tbl_creneaux.id_creneau'), nullable=False)
    id_salle = db.Column(db.Integer, db.ForeignKey('tbl_salles.id_salle'), nullable=False)
    semaine_type = db.Column(db.String(10), default="TOUTES")
    verrouillee = db.Column(db.Boolean, default=False)
    origine = db.Column(db.String(10), default="AUTO")
    statut = db.Column(db.String(15), default="PROPOSEE")
    
    # Relations
    affectation = db.relationship('Affectation', backref='seances', lazy=True)
    creneau = db.relationship('Creneau', backref='seances', lazy=True)
    salle = db.relationship('Salle', backref='seances', lazy=True)
    
    __table_args__ = (
        db.UniqueConstraint('id_annee', 'jour', 'id_creneau', 'id_salle', 'semaine_type', 
                           name='uq_seance_salle'),
    )

class Indisponibilite(db.Model):
    __tablename__ = "tbl_indisponibilites"
    
    id_indisponibilite = db.Column(db.Integer, primary_key=True)
    id_annee = db.Column(db.Integer, db.ForeignKey('tbl_annees_univ.id_annee'), nullable=False)
    id_professeur = db.Column(db.Integer, db.ForeignKey('tbl_professeurs.id_professeur'), nullable=False)
    jour = db.Column(db.Integer, nullable=False)  # 1=Lundi, 2=Mardi, ..., 7=Dimanche
    id_creneau = db.Column(db.Integer, db.ForeignKey('tbl_creneaux.id_creneau'), nullable=False)
    type_contrainte = db.Column(db.String(15), nullable=False, default='INTERDIT')
    commentaire = db.Column(db.String(500))
    actif = db.Column(db.Boolean, default=True)

    # Relations
    professeur = db.relationship('Professeur', backref='indisponibilites', lazy=True)
    creneau = db.relationship('Creneau', backref='indisponibilites', lazy=True)
    annee = db.relationship('AnneeUniversitaire', backref='indisponibilites', lazy=True)

    __table_args__ = (
        db.UniqueConstraint('id_annee', 'id_professeur', 'jour', 'id_creneau',
                           name='uq_indisponibilite_unique'),
        db.CheckConstraint('jour BETWEEN 1 AND 7', name='ck_indisponibilite_jour'),
        db.CheckConstraint("type_contrainte IN ('INTERDIT', 'EVITER', 'PREFERE')",
                          name='ck_indisponibilite_type'),
    )

    def __repr__(self):
        return f"<Indisponibilite {self.professeur.nom} {self.jour} {self.creneau.heure_debut}>"

class Historique(db.Model):
    __tablename__ = "tbl_historique"
    
    id_historique = db.Column(db.Integer, primary_key=True)
    utilisateur = db.Column(db.String(100), nullable=False, default='Système')
    action = db.Column(db.String(20), nullable=False)  # AJOUT, MODIFICATION, SUPPRESSION
    type_objet = db.Column(db.String(30), nullable=False)  # PROFESSEUR, SEANCE, INDISPONIBILITE, etc.
    id_objet = db.Column(db.Integer, nullable=False)
    ancienne_valeur = db.Column(db.Text)
    nouvelle_valeur = db.Column(db.Text)
    date_heure = db.Column(db.DateTime, default=datetime.utcnow)
    ip_adresse = db.Column(db.String(45))
    
    def __repr__(self):
        return f"<Historique {self.action} {self.type_objet} {self.id_objet} à {self.date_heure}>"
