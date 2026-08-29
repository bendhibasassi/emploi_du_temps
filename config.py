"""Configuration centrale des chemins du projet."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
DATABASE_PATH = PROJECT_ROOT / "emploi_du_temps.db"
DATABASE_URI = f"sqlite:///{DATABASE_PATH.as_posix()}"
