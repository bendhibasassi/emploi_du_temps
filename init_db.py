"""Initialisation explicite du schéma ORM officiel.

Ne pas exécuter ce script contre la base principale sans intention explicite.
"""

from sqlalchemy import create_engine

from app import db
from app import models  # noqa: F401 - enregistre tous les modèles dans db.metadata
from config import DATABASE_URI


def initialiser_base(database_uri=DATABASE_URI, echo=True):
    """Crée les tables officielles dans la base indiquée."""
    engine = create_engine(database_uri, echo=echo)
    db.metadata.create_all(engine)
    return engine


if __name__ == "__main__":
    print("🚀 Création de la base de données...")
    initialiser_base()
    print("✅ Base de données 'emploi_du_temps.db' créée avec succès !")
