# app/__init__.py
import secrets
from flask import Flask, abort, flash, redirect, request, session, url_for
from flask_sqlalchemy import SQLAlchemy
import sqlite3

from sqlalchemy import event
from sqlalchemy.engine import Engine

from config import (
    ADMIN_PASSWORD_HASH, ADMIN_USERNAME, DATABASE_URI, SECRET_KEY,
    SECRET_KEY_EPHEMERAL,
)

# Initialisation de SQLAlchemy
db = SQLAlchemy()


ROUTES_ECRITURE = {
    'main.ajouter_annee_universitaire',
    'main.activer_annee_universitaire',
    'main.ajouter_affectation', 'main.modifier_affectation',
    'main.changer_statut_affectation',
    'main.ajouter_niveau', 'main.modifier_niveau',
    'main.ajouter_section', 'main.modifier_section',
    'main.ajouter_creneau', 'main.modifier_creneau',
    'main.ajouter_seance', 'main.modifier_seance', 'main.supprimer_seance',
    'main.ajouter_professeur', 'main.modifier_professeur',
    'main.supprimer_professeur', 'main.importer_professeurs',
    'main.ajouter_salle', 'main.modifier_salle', 'main.supprimer_salle',
    'main.ajouter_groupe', 'main.modifier_groupe', 'main.supprimer_groupe',
    'main.ajouter_matiere', 'main.modifier_matiere', 'main.supprimer_matiere',
    'main.ajouter_indisponibilite', 'main.supprimer_indisponibilite',
}


def csrf_token():
    """Retourne le jeton CSRF associé à la session courante."""
    token = session.get('_csrf_token')
    if token is None:
        token = secrets.token_urlsafe(32)
        session['_csrf_token'] = token
    return token


@event.listens_for(Engine, "connect")
def activer_cles_etrangeres_sqlite(dbapi_connection, connection_record):
    """Active les contraintes de clés étrangères sur chaque connexion SQLite."""
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = SECRET_KEY
    app.config['SECRET_KEY_EPHEMERAL'] = SECRET_KEY_EPHEMERAL
    app.config['ADMIN_USERNAME'] = ADMIN_USERNAME
    app.config['ADMIN_PASSWORD_HASH'] = ADMIN_PASSWORD_HASH
    
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialisation de la base
    db.init_app(app)
    
    # Importer les routes
    from app.routes import main
    app.register_blueprint(main)

    @app.before_request
    def proteger_ecritures_et_csrf():
        """Exige une connexion pour écrire et valide tous les POST."""
        action_ecriture = (
            request.endpoint in ROUTES_ECRITURE or
            (request.method == 'POST' and request.endpoint != 'main.connexion')
        )
        if action_ecriture and not session.get('admin_connecte'):
            flash('Connectez-vous pour effectuer cette action.', 'warning')
            return redirect(url_for('main.connexion', next=request.full_path))

        if request.method == 'POST':
            token_session = session.get('_csrf_token', '')
            token_formulaire = request.form.get('_csrf_token', '')
            if not (token_session and token_formulaire and
                    secrets.compare_digest(token_session, token_formulaire)):
                abort(400, description='Jeton CSRF absent ou invalide.')

    @app.context_processor
    def injecter_annee_active():
        """Rend l'année de travail disponible dans tous les templates."""
        from app.models import AnneeUniversitaire
        return {
            'annee_active_globale': AnneeUniversitaire.query.filter_by(
                active=True
            ).first(),
            'csrf_token': csrf_token,
            'administrateur_connecte': bool(session.get('admin_connecte')),
        }
    
    # Créer les tables si elles n'existent pas
    with app.app_context():
        db.create_all()
        # Vérification
        from app.models import Professeur
        print(f"Professeurs dans la base Flask : {Professeur.query.count()}")
    
    return app
