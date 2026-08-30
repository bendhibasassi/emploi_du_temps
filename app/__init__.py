# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import sqlite3

from sqlalchemy import event
from sqlalchemy.engine import Engine

from config import DATABASE_URI

# Initialisation de SQLAlchemy
db = SQLAlchemy()


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
    app.config['SECRET_KEY'] = 'dev-key-12345'
    
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialisation de la base
    db.init_app(app)
    
    # Importer les routes
    from app.routes import main
    app.register_blueprint(main)

    @app.context_processor
    def injecter_annee_active():
        """Rend l'année de travail disponible dans tous les templates."""
        from app.models import AnneeUniversitaire
        return {
            'annee_active_globale': AnneeUniversitaire.query.filter_by(
                active=True
            ).first()
        }
    
    # Créer les tables si elles n'existent pas
    with app.app_context():
        db.create_all()
        # Vérification
        from app.models import Professeur
        print(f"Professeurs dans la base Flask : {Professeur.query.count()}")
    
    return app
