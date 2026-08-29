"""Compatibilité temporaire avec les anciens imports de scripts.

La définition officielle et unique des modèles se trouve dans app.models.
"""

from app import db
from app.models import (
    Affectation,
    AnneeUniversitaire,
    Creneau,
    Groupe,
    Historique,
    Indisponibilite,
    Matiere,
    Niveau,
    Professeur,
    Salle,
    Seance,
    Section,
)

# Compatibilité avec les anciens appels Base.metadata.create_all(...).
# Aucun registre ni aucune MetaData supplémentaire n'est créé.
Base = db.Model

__all__ = (
    'Base',
    'Affectation',
    'AnneeUniversitaire',
    'Creneau',
    'Groupe',
    'Historique',
    'Indisponibilite',
    'Matiere',
    'Niveau',
    'Professeur',
    'Salle',
    'Seance',
    'Section',
)
