"""Configuration centrale de l'application."""

import os
import secrets
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
DATABASE_PATH = PROJECT_ROOT / "emploi_du_temps.db"
DATABASE_URI = f"sqlite:///{DATABASE_PATH.as_posix()}"

# En production, définir EDT_SECRET_KEY avec une valeur stable et aléatoire.
# Ce fallback éphémère convient au développement mais invalide les sessions
# à chaque redémarrage tant que la variable n'est pas configurée.
SECRET_KEY = os.environ.get("EDT_SECRET_KEY") or secrets.token_hex(32)
SECRET_KEY_EPHEMERAL = "EDT_SECRET_KEY" not in os.environ

# Administrateur minimal sans table utilisateur. Le mot de passe n'est jamais
# stocké ici : EDT_ADMIN_PASSWORD_HASH doit contenir un hash Werkzeug.
ADMIN_USERNAME = os.environ.get("EDT_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH = os.environ.get("EDT_ADMIN_PASSWORD_HASH")
