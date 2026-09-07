"""Import atomique des affectations de CM depuis un fichier Excel."""

import os
import sys

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import (
    Affectation,
    AnneeUniversitaire,
    Seance,
)
from app.services.import_affectations import valider_lignes_import
from config import DATABASE_URI


DEFAULT_FILE = "Affectations_corrigees.xlsx"
REQUIRED_COLUMNS = {
    "Professeur",
    "Matière",
    "Section",
    "Type (CM/TD)",
    "Semestre",
}


class ImportAffectationsError(RuntimeError):
    """Signale un import invalide avant tout remplacement."""


def clean_value(value):
    """Convertit une cellule Excel vide en chaîne vide."""
    return "" if pd.isna(value) else str(value).strip()


def ligne_validateur(row):
    """Adapte une ligne Excel CM au format du validateur commun."""
    return {
        'Professeur': clean_value(row['Professeur']),
        'Matiere': clean_value(row['Matière']),
        'Section': clean_value(row['Section']),
        'Groupe': clean_value(row.get('Groupe', '')),
        'Type_enseignement': clean_value(row['Type (CM/TD)']),
        'Semestre': row['Semestre'],
        'Nb_seances_semaine': 2,
        'Duree_seance_minutes': 90,
        'Volume_total_minutes': '',
        'Priorite': 50,
        'Actif': True,
    }


def preparer_affectations(session, dataframe, annee):
    """Valide toutes les lignes et prépare les objets sans les ajouter."""
    colonnes_manquantes = REQUIRED_COLUMNS.difference(dataframe.columns)
    if colonnes_manquantes:
        raise ImportAffectationsError(
            "Colonnes manquantes : " + ", ".join(sorted(colonnes_manquantes))
        )
    if dataframe.empty:
        raise ImportAffectationsError(
            "Le fichier ne contient aucune ligne ; aucun remplacement effectué."
        )

    rapport = valider_lignes_import(
        session,
        [ligne_validateur(row) for _, row in dataframe.iterrows()],
        annee,
        verifier_doublons_base=False,
    )
    erreurs = []
    nouvelles_affectations = []
    for resultat in rapport['resultats']:
        if resultat['statut'] == 'ERREUR_BLOQUANTE':
            erreurs.extend(
                f"Ligne {resultat['ligne']}: {erreur}"
                for erreur in resultat['erreurs']
            )
            continue
        if resultat['statut'] == 'DOUBLON_IGNORE':
            continue
        valeurs = resultat['valeurs']
        references = resultat['references']
        if valeurs['type_enseignement'] != 'CM':
            erreurs.append(
                f"Ligne {resultat['ligne']}: type "
                f"'{valeurs['type_enseignement']}' invalide (CM attendu)."
            )
            continue
        nouvelles_affectations.append(Affectation(
            id_annee=annee.id_annee,
            id_professeur=references['professeur'].id_professeur,
            id_matiere=references['matiere'].id_matiere,
            id_section=references['section'].id_section,
            id_groupe=getattr(references['groupe'], 'id_groupe', None),
            semestre=valeurs['semestre'],
            type_enseignement=valeurs['type_enseignement'],
            nb_seances_semaine=valeurs['Nb_seances_semaine'],
            duree_seance_minutes=valeurs['Duree_seance_minutes'],
            volume_total_minutes=valeurs['Volume_total_minutes'],
            priorite=valeurs['Priorite'],
            actif=resultat['actif'],
        ))

    if erreurs:
        raise ImportAffectationsError("\n".join(erreurs))
    if not nouvelles_affectations:
        raise ImportAffectationsError(
            "Aucune affectation valide ; aucun remplacement effectué."
        )
    return nouvelles_affectations


def remplacer_affectations(session, nouvelles_affectations):
    """Remplace toutes les affectations dans une transaction indivisible."""
    if not nouvelles_affectations:
        raise ImportAffectationsError(
            "Aucune affectation valide ; aucun remplacement effectué."
        )
    seance_existante = session.query(Seance.id_seance).join(
        Affectation, Seance.id_affectation == Affectation.id_affectation
    ).first()
    if seance_existante:
        raise ImportAffectationsError(
            "Import refusé : des affectations existantes possèdent des séances."
        )

    try:
        supprimees = session.query(Affectation).delete(
            synchronize_session="fetch"
        )
        session.add_all(nouvelles_affectations)
        session.flush()
        session.commit()
        return supprimees, len(nouvelles_affectations)
    except Exception:
        session.rollback()
        raise


def main():
    fichier = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_FILE
    if not os.path.isabs(fichier):
        fichier = os.path.join(os.path.dirname(__file__), fichier)

    try:
        dataframe = pd.read_excel(fichier, sheet_name="Affectations")
    except FileNotFoundError as exc:
        raise ImportAffectationsError(f"Fichier introuvable : {fichier}") from exc
    except Exception as exc:
        raise ImportAffectationsError(
            f"Le fichier ne peut pas être lu : {exc}"
        ) from exc

    engine = create_engine(DATABASE_URI)
    session = sessionmaker(bind=engine)()
    try:
        annee = session.query(AnneeUniversitaire).filter_by(active=True).first()
        if annee is None:
            raise ImportAffectationsError(
                "Aucune année universitaire active trouvée."
            )
        nouvelles_affectations = preparer_affectations(
            session, dataframe, annee
        )
        supprimees, ajoutees = remplacer_affectations(
            session, nouvelles_affectations
        )
        print(f"Affectations supprimées : {supprimees}")
        print(f"Affectations CM ajoutées : {ajoutees}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        engine.dispose()


if __name__ == "__main__":
    main()
