"""Consultation en lecture seule d'une liste blanche de tables métier."""

from sqlalchemy import inspect

from app import db
from app.models import (
    Affectation,
    AnneeUniversitaire,
    Creneau,
    Groupe,
    Matiere,
    Niveau,
    Salle,
    Seance,
    Section,
)


TAILLE_PAGE = 50

TABLES_AUTORISEES = {
    'tbl_annees_univ': {
        'libelle': 'Années universitaires',
        'modele': AnneeUniversitaire,
    },
    'tbl_niveaux': {'libelle': 'Niveaux', 'modele': Niveau},
    'tbl_sections': {'libelle': 'Sections', 'modele': Section},
    'tbl_groupes': {'libelle': 'Groupes', 'modele': Groupe},
    'tbl_matieres': {'libelle': 'Matières', 'modele': Matiere},
    'tbl_salles': {'libelle': 'Salles', 'modele': Salle},
    'tbl_creneaux': {'libelle': 'Créneaux', 'modele': Creneau},
    'tbl_affectations': {'libelle': 'Affectations', 'modele': Affectation},
    'tbl_seances': {'libelle': 'Séances', 'modele': Seance},
}


def lister_tables_autorisees():
    """Retourne la liste blanche sans découvrir les tables de la base."""
    return [
        {'nom': nom, 'libelle': configuration['libelle']}
        for nom, configuration in TABLES_AUTORISEES.items()
    ]


def obtenir_table_autorisee(nom_table):
    """Résout un nom uniquement s'il appartient à la liste blanche."""
    return TABLES_AUTORISEES.get(nom_table)


def obtenir_metadonnees(nom_table):
    """Lit colonnes, types et contraintes via l'inspecteur SQLAlchemy."""
    if nom_table not in TABLES_AUTORISEES:
        raise KeyError(nom_table)

    inspecteur = inspect(db.engine)
    cle_primaire = set(
        inspecteur.get_pk_constraint(nom_table).get('constrained_columns') or []
    )
    cles_etrangeres = {}
    for contrainte in inspecteur.get_foreign_keys(nom_table):
        colonnes = contrainte.get('constrained_columns') or []
        cibles = contrainte.get('referred_columns') or []
        table_cible = contrainte.get('referred_table')
        for index, colonne in enumerate(colonnes):
            colonne_cible = cibles[index] if index < len(cibles) else None
            cles_etrangeres[colonne] = (
                f'{table_cible}.{colonne_cible}' if colonne_cible
                else table_cible
            )

    return [
        {
            'nom': colonne['name'],
            'type': str(colonne['type']),
            'cle_primaire': colonne['name'] in cle_primaire,
            'cle_etrangere': colonne['name'] in cles_etrangeres,
            'cible': cles_etrangeres.get(colonne['name']),
        }
        for colonne in inspecteur.get_columns(nom_table)
    ]


def obtenir_donnees_paginees(nom_table, page):
    """Charge au plus 50 lignes, dans un ordre stable par clé primaire."""
    configuration = obtenir_table_autorisee(nom_table)
    if configuration is None:
        raise KeyError(nom_table)

    modele = configuration['modele']
    cles_primaires = list(inspect(modele).primary_key)
    pagination = (
        db.session.query(modele)
        .order_by(*cles_primaires)
        .paginate(page=page, per_page=TAILLE_PAGE, error_out=False)
    )
    colonnes = [colonne.key for colonne in inspect(modele).columns]
    lignes = [
        [getattr(objet, colonne) for colonne in colonnes]
        for objet in pagination.items
    ]
    return colonnes, lignes, pagination
