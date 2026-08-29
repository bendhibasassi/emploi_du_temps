# app/__init__.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
import sqlite3

from sqlalchemy import event
from sqlalchemy.engine import Engine

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
    
    # === CHEMIN ABSOLU VERS LA BASE ===
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(BASE_DIR, "emploi_du_temps.db")
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialisation de la base
    db.init_app(app)
    
    # Importer les routes
    from app.routes import main
    app.register_blueprint(main)
    
    # Créer les tables si elles n'existent pas
    with app.app_context():
        db.create_all()
        # Vérification
        from app.models import Professeur
        print(f"📊 Professeurs dans la base Flask : {Professeur.query.count()}")
    
    return app
