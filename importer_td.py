"""Importe les affectations de TD depuis un fichier Excel."""

import os
import sys

import pandas as pd
from sqlalchemy import create_engine
from config import DATABASE_URI
from sqlalchemy.orm import sessionmaker

from app.models import (
    Affectation,
    AnneeUniversitaire,
)
from app.services.import_affectations import valider_lignes_import


REQUIRED_COLUMNS = {
    "Professeur",
    "Matière",
    "Section",
    "Groupe",
    "Semestre",
    "Type",
}
DEFAULT_FILE = "TD_import.xlsx"


def clean_value(value):
    """Convertit une cellule Excel vide en chaîne vide."""
    return "" if pd.isna(value) else str(value).strip()


def ligne_validateur(row):
    """Adapte une ligne Excel TD au format du validateur commun."""
    return {
        'Professeur': clean_value(row['Professeur']),
        'Matiere': clean_value(row['Matière']),
        'Section': clean_value(row['Section']),
        'Groupe': clean_value(row['Groupe']),
        'Type_enseignement': clean_value(row['Type']),
        'Semestre': row['Semestre'],
        'Nb_seances_semaine': 1,
        'Duree_seance_minutes': 90,
        'Volume_total_minutes': '',
        'Priorite': 50,
        'Actif': True,
    }


def preparer_affectations_td(session, dataframe, annee):
    """Valide les lignes TD et prépare les objets sans les ajouter."""
    missing = REQUIRED_COLUMNS.difference(dataframe.columns)
    if missing:
        raise RuntimeError(
            "Colonnes manquantes : " + ", ".join(sorted(missing))
        )
    rapport = valider_lignes_import(
        session,
        [ligne_validateur(row) for _, row in dataframe.iterrows()],
        annee,
        verifier_doublons_base=True,
    )
    nouvelles, ignorees, messages = [], 0, []
    for resultat in rapport['resultats']:
        if resultat['statut'] != 'PRETE_A_IMPORTER':
            ignorees += 1
            messages.extend(
                f"Ligne {resultat['ligne']}: {message}"
                for message in resultat['erreurs'] + resultat['avertissements']
            )
            continue
        valeurs = resultat['valeurs']
        references = resultat['references']
        if valeurs['type_enseignement'] != 'TD':
            ignorees += 1
            messages.append(
                f"Ligne {resultat['ligne']}: type "
                f"'{valeurs['type_enseignement']}' ignore (TD attendu)."
            )
            continue
        nouvelles.append(Affectation(
            id_annee=annee.id_annee,
            id_professeur=references['professeur'].id_professeur,
            id_matiere=references['matiere'].id_matiere,
            id_section=references['section'].id_section,
            id_groupe=references['groupe'].id_groupe,
            semestre=valeurs['semestre'],
            type_enseignement=valeurs['type_enseignement'],
            nb_seances_semaine=valeurs['Nb_seances_semaine'],
            duree_seance_minutes=valeurs['Duree_seance_minutes'],
            volume_total_minutes=valeurs['Volume_total_minutes'],
            priorite=valeurs['Priorite'],
            actif=resultat['actif'],
        ))
    return nouvelles, ignorees, messages


def main():
    file_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_FILE
    if not os.path.isabs(file_path):
        file_path = os.path.join(os.path.dirname(__file__), file_path)

    engine = create_engine(DATABASE_URI)
    session = sessionmaker(bind=engine)()

    try:
        year = session.query(AnneeUniversitaire).filter_by(active=True).first()
        if year is None:
            raise RuntimeError("Aucune annee universitaire active trouvee.")

        try:
            dataframe = pd.read_excel(file_path, sheet_name="TD")
        except FileNotFoundError as exc:
            raise RuntimeError(f"Fichier introuvable : {file_path}") from exc

        nouvelles, skipped, messages = preparer_affectations_td(
            session, dataframe, year
        )
        for message in messages:
            print(message)
        for affectation in nouvelles:
            session.add(affectation)

        session.commit()
        print(f"Affectations TD ajoutees : {len(nouvelles)}")
        print(f"Lignes ignorees ou deja presentes : {skipped}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
