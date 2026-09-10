"""Creation reproductible de la base initiale propre Emploi du temps.

SECURITE :
- ne modifie jamais emploi_du_temps.db ;
- refuse d'ecraser une base existante ;
- cree uniquement une nouvelle base explicitement demandee.
"""

import argparse
from datetime import time
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import create_engine
from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session

from app import models  # noqa: F401
from app.models import Formation, Specialite, Niveau, Salle, Creneau


MAIN_DATABASE = (PROJECT_ROOT / "emploi_du_temps.db").resolve()


def build_initial_database(output_path: Path) -> Path:
    output_path = output_path.resolve()

    print("BASE PRINCIPALE =", MAIN_DATABASE)
    print("BASE CIBLE      =", output_path)

    if output_path == MAIN_DATABASE:
        raise RuntimeError(
            "SECURITE: refus absolu d'ecrire dans emploi_du_temps.db"
        )

    if output_path.exists():
        raise RuntimeError(
            f"SECURITE: la base cible existe deja: {output_path}"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Le schema officiel est construit uniquement par Alembic.
    alembic_cfg = Config(str(PROJECT_ROOT / "alembic.ini"))

    database_url = "sqlite:///" + output_path.as_posix()

    alembic_cfg.set_main_option(
        "sqlalchemy.url",
        database_url,
    )

    print("ALEMBIC URL     =", database_url)

    command.upgrade(
        alembic_cfg,
        "head",
    )

    # SQLAlchemy est utilise ensuite uniquement pour inserer
    # les donnees canoniques dans le schema cree par Alembic.
    engine = create_engine(database_url)

    with Session(engine) as session:

        # ------------------------------------------------------
        # FORMATIONS — 2
        # ------------------------------------------------------
        formations = [
            Formation(
                code_formation="LIC",
                libelle="Licence",
                actif=True,
            ),
            Formation(
                code_formation="MAS",
                libelle="Master",
                actif=True,
            ),
        ]

        session.add_all(formations)
        session.flush()

        formations_by_code = {
            x.code_formation: x
            for x in formations
        }

        # ------------------------------------------------------
        # SPECIALITES — 6
        # ------------------------------------------------------
        specialites = [
            Specialite(
                id_formation=formations_by_code["LIC"].id_formation,
                code_specialite="PUB",
                libelle="Droit public",
                actif=True,
            ),
            Specialite(
                id_formation=formations_by_code["LIC"].id_formation,
                code_specialite="PRIV",
                libelle="Droit priv\u00e9",
                actif=True,
            ),
            Specialite(
                id_formation=formations_by_code["MAS"].id_formation,
                code_specialite="ADMIN",
                libelle="Droit administratif",
                actif=True,
            ),
            Specialite(
                id_formation=formations_by_code["MAS"].id_formation,
                code_specialite="PEN-SCI",
                libelle="Droit p\u00e9nal et science criminelle",
                actif=True,
            ),
            Specialite(
                id_formation=formations_by_code["MAS"].id_formation,
                code_specialite="INT-PUB",
                libelle="Droit international public",
                actif=True,
            ),
            Specialite(
                id_formation=formations_by_code["MAS"].id_formation,
                code_specialite="GOUV-CORR",
                libelle="Gouvernance et lutte contre la corruption",
                actif=True,
            ),
        ]

        session.add_all(specialites)
        session.flush()

        specialites_by_code = {
            x.code_specialite: x
            for x in specialites
        }

        # ------------------------------------------------------
        # NIVEAUX — 12
        # ------------------------------------------------------
        niveaux = [
            (
                "L1", "LICENCE", "Droit",
                "1\u00e8re ann\u00e9e",
                "Licence 1 Droit",
                "LIC", None,
            ),
            (
                "L2", "LICENCE", "Droit",
                "2\u00e8me ann\u00e9e",
                "Licence 2 Droit",
                "LIC", None,
            ),
            (
                "L3-PUB", "LICENCE", "Droit public",
                "3\u00e8me ann\u00e9e",
                "Licence 3 Droit public",
                "LIC", "PUB",
            ),
            (
                "L3-PRIV", "LICENCE", "Droit priv\u00e9",
                "3\u00e8me ann\u00e9e",
                "Licence 3 Droit priv\u00e9",
                "LIC", "PRIV",
            ),
            (
                "M1-ADMIN", "MASTER", "Droit administratif",
                "1\u00e8re ann\u00e9e Master",
                "Master 1 Droit administratif",
                "MAS", "ADMIN",
            ),
            (
                "M2-ADMIN", "MASTER", "Droit administratif",
                "2\u00e8me ann\u00e9e Master",
                "Master 2 Droit administratif",
                "MAS", "ADMIN",
            ),
            (
                "M1-PEN", "MASTER",
                "Droit p\u00e9nal et science criminelle",
                "1\u00e8re ann\u00e9e Master",
                "Master 1 Droit p\u00e9nal",
                "MAS", "PEN-SCI",
            ),
            (
                "M2-PEN", "MASTER",
                "Droit p\u00e9nal et science criminelle",
                "2\u00e8me ann\u00e9e Master",
                "Master 2 Droit p\u00e9nal",
                "MAS", "PEN-SCI",
            ),
            (
                "M1-INT", "MASTER", "Droit international public",
                "1\u00e8re ann\u00e9e Master",
                "Master 1 Droit international public",
                "MAS", "INT-PUB",
            ),
            (
                "M2-INT", "MASTER", "Droit international public",
                "2\u00e8me ann\u00e9e Master",
                "Master 2 Droit international public",
                "MAS", "INT-PUB",
            ),
            (
                "M1-GOUV", "MASTER",
                "Gouvernance et lutte contre la corruption",
                "1\u00e8re ann\u00e9e Master",
                "Master 1 Gouvernance et lutte contre la corruption",
                "MAS", "GOUV-CORR",
            ),
            (
                "M2-GOUV", "MASTER",
                "Gouvernance et lutte contre la corruption",
                "2\u00e8me ann\u00e9e Master",
                "Master 2 Gouvernance et lutte contre la corruption",
                "MAS", "GOUV-CORR",
            ),
        ]

        for (
            code,
            cycle,
            specialite_texte,
            annee_etude,
            libelle,
            formation_code,
            specialite_code,
        ) in niveaux:

            session.add(
                Niveau(
                    code_niveau=code,
                    cycle=cycle,
                    specialite=specialite_texte,
                    annee_etude=annee_etude,
                    libelle=libelle,
                    actif=True,
                    id_formation=(
                        formations_by_code[formation_code].id_formation
                    ),
                    id_specialite=(
                        specialites_by_code[specialite_code].id_specialite
                        if specialite_code
                        else None
                    ),
                )
            )

        # ------------------------------------------------------
        # SALLES — 30
        # ------------------------------------------------------
        amphitheatres = [
            "A0", "A1", "A2", "A3", "BIO1", "BIO2"
        ]

        grandes_salles = [
            "DSP1", "DSP2", "DSP3", "DSP4", "DSP5",
            "DSP6", "DSP7", "DSP22", "DSP23", "DSP24",
        ]

        petites_salles = [
            f"DSP{i}"
            for i in range(8, 22)
        ]

        for code in amphitheatres:
            session.add(
                Salle(
                    code_salle=code,
                    nom_salle="Amphith\u00e9\u00e2tre " + code,
                    type_salle="AMPHI",
                    capacite=None,
                    batiment=None,
                    actif=True,
                )
            )

        for code in grandes_salles:
            session.add(
                Salle(
                    code_salle=code,
                    nom_salle=code,
                    type_salle="GRANDE_SALLE",
                    capacite=None,
                    batiment=None,
                    actif=True,
                )
            )

        for code in petites_salles:
            session.add(
                Salle(
                    code_salle=code,
                    nom_salle=code,
                    type_salle="PETITE_SALLE",
                    capacite=None,
                    batiment=None,
                    actif=True,
                )
            )

        # ------------------------------------------------------
        # CRENEAUX — 6
        # ------------------------------------------------------
        creneaux = [
            (time(8, 0), time(9, 30), 1),
            (time(9, 30), time(11, 0), 2),
            (time(11, 0), time(12, 30), 3),
            (time(13, 0), time(14, 30), 4),
            (time(14, 30), time(16, 0), 5),
            (time(16, 0), time(18, 0), 6),
        ]

        for debut, fin, ordre in creneaux:
            session.add(
                Creneau(
                    heure_debut=debut,
                    heure_fin=fin,
                    ordre=ordre,
                    actif=True,
                )
            )

        session.commit()

    print("BASE INITIALE CREEE AVEC SUCCES")
    print(output_path)

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Cree une nouvelle base initiale propre."
    )

    parser.add_argument(
        "output",
        type=Path,
        help="Chemin de la nouvelle base SQLite a creer.",
    )

    args = parser.parse_args()

    build_initial_database(args.output)


if __name__ == "__main__":
    main()
