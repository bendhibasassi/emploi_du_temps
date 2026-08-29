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
    Groupe,
    Matiere,
    Professeur,
    Section,
)


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


def parse_semester(value):
    """Convertit S1, S2, etc. en entier."""
    semester = clean_value(value).upper()
    if semester.startswith("S"):
        semester = semester[1:]
    return int(semester)


def find_professor(session, value):
    """Recherche un professeur par nom ou par nom complet."""
    name = clean_value(value)
    professor = session.query(Professeur).filter_by(nom=name).first()
    if professor:
        return professor
    return session.query(Professeur).filter(
        (Professeur.nom + " " + Professeur.prenom) == name
    ).first()


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

        missing = REQUIRED_COLUMNS.difference(dataframe.columns)
        if missing:
            raise RuntimeError(
                "Colonnes manquantes : " + ", ".join(sorted(missing))
            )

        added = 0
        skipped = 0

        for index, row in dataframe.iterrows():
            line_number = index + 2
            professor = find_professor(session, row["Professeur"])
            subject_name = clean_value(row["Matière"])
            section_name = clean_value(row["Section"])
            group_code = clean_value(row["Groupe"])
            teaching_type = clean_value(row["Type"]).upper()

            if professor is None:
                print(f"Ligne {line_number}: professeur introuvable.")
                skipped += 1
                continue

            subject = session.query(Matiere).filter_by(
                nom_matiere=subject_name
            ).first()
            section = session.query(Section).filter_by(
                libelle=section_name
            ).first()
            group = session.query(Groupe).filter_by(
                id_section=section.id_section if section else None,
                code_groupe=group_code,
            ).first()

            if subject is None or section is None or group is None:
                print(f"Ligne {line_number}: matiere, section ou groupe introuvable.")
                skipped += 1
                continue

            try:
                semester = parse_semester(row["Semestre"])
            except ValueError:
                print(f"Ligne {line_number}: semestre invalide.")
                skipped += 1
                continue

            if teaching_type != "TD":
                print(f"Ligne {line_number}: type '{teaching_type}' ignore (TD attendu).")
                skipped += 1
                continue

            existing = session.query(Affectation).filter_by(
                id_annee=year.id_annee,
                id_professeur=professor.id_professeur,
                id_matiere=subject.id_matiere,
                id_section=section.id_section,
                id_groupe=group.id_groupe,
                semestre=semester,
                type_enseignement="TD",
            ).first()
            if existing:
                skipped += 1
                continue

            session.add(
                Affectation(
                    id_annee=year.id_annee,
                    id_professeur=professor.id_professeur,
                    id_matiere=subject.id_matiere,
                    id_section=section.id_section,
                    id_groupe=group.id_groupe,
                    semestre=semester,
                    type_enseignement="TD",
                    nb_seances_semaine=1,
                    duree_seance_minutes=90,
                    actif=True,
                )
            )
            added += 1

        session.commit()
        print(f"Affectations TD ajoutees : {added}")
        print(f"Lignes ignorees ou deja presentes : {skipped}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
