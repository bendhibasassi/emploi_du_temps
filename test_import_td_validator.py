import tempfile
import unittest
from datetime import date
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import db
from app.models import (
    Affectation, AnneeUniversitaire, Groupe, Matiere, Niveau, Professeur,
    Section,
)
from importer_td import preparer_affectations_td


class ImportTdValidatorTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / 'import_td.db'
        self.engine = create_engine(f'sqlite:///{database_path.as_posix()}')
        db.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)()
        self.annee = AnneeUniversitaire(
            libelle='2099-2100', date_debut=date(2099, 9, 1),
            date_fin=date(2100, 6, 30), active=True,
        )
        self.niveau = Niveau(
            code_niveau='TEST-TD', cycle='MASTER', specialite='Test',
            annee_etude='1', libelle='Test TD', actif=True,
        )
        self.professeur = Professeur(
            nom='Professeur TD', statut='Permanent', actif=True,
        )
        self.session.add_all([self.annee, self.niveau, self.professeur])
        self.session.flush()
        self.section = Section(
            id_niveau=self.niveau.id_niveau, code_section='A',
            libelle='Section TD test', actif=True,
        )
        self.matiere = Matiere(
            code_matiere='TEST-TD-S1', nom_matiere='Matiere TD test',
            id_niveau=self.niveau.id_niveau, semestre='S1', actif=True,
        )
        self.session.add_all([self.section, self.matiere])
        self.session.flush()
        self.groupe = Groupe(
            id_section=self.section.id_section, code_groupe='G1',
            nom_groupe='Groupe TD test', actif=True,
        )
        self.session.add(self.groupe)
        self.session.commit()

    def tearDown(self):
        self.session.close()
        self.engine.dispose()
        self.temp_dir.cleanup()

    def dataframe(self, **changes):
        ligne = {
            'Professeur': self.professeur.nom,
            'Matière': self.matiere.nom_matiere,
            'Section': self.section.libelle,
            'Groupe': self.groupe.code_groupe,
            'Semestre': 'S1',
            'Type': 'TD',
        }
        ligne.update(changes)
        return pd.DataFrame([ligne])

    def preparer(self, dataframe=None):
        return preparer_affectations_td(
            self.session,
            self.dataframe() if dataframe is None else dataframe,
            self.annee,
        )

    def test_td_valide_importe(self):
        nouvelles, ignorees, _ = self.preparer()
        self.assertEqual((len(nouvelles), ignorees), (1, 0))
        for affectation in nouvelles:
            self.session.add(affectation)
        self.session.commit()
        self.assertEqual(self.session.query(Affectation).count(), 1)

    def test_groupe_inactif_refuse(self):
        self.groupe.actif = False
        self.session.commit()
        nouvelles, ignorees, _ = self.preparer()
        self.assertEqual((len(nouvelles), ignorees), (0, 1))

    def test_niveau_groupe_inactif_refuse(self):
        self.niveau.actif = False
        self.session.commit()
        nouvelles, ignorees, _ = self.preparer()
        self.assertEqual((len(nouvelles), ignorees), (0, 1))

    def test_incoherence_matiere_section_refusee(self):
        autre_niveau = Niveau(
            code_niveau='AUTRE-TD', cycle='MASTER', specialite='Autre',
            annee_etude='2', libelle='Autre niveau TD', actif=True,
        )
        self.session.add(autre_niveau)
        self.session.flush()
        self.matiere.id_niveau = autre_niveau.id_niveau
        self.session.commit()
        nouvelles, ignorees, _ = self.preparer()
        self.assertEqual((len(nouvelles), ignorees), (0, 1))

    def test_td_sans_groupe_refuse(self):
        nouvelles, ignorees, _ = self.preparer(self.dataframe(Groupe=''))
        self.assertEqual((len(nouvelles), ignorees), (0, 1))

    def test_doublon_base_ignore(self):
        existante = self.preparer()[0][0]
        self.session.add(existante)
        self.session.commit()
        nouvelles, ignorees, _ = self.preparer()
        self.assertEqual((len(nouvelles), ignorees), (0, 1))

    def test_doublon_fichier_ignore(self):
        dataframe = pd.concat(
            [self.dataframe(), self.dataframe()], ignore_index=True
        )
        nouvelles, ignorees, _ = self.preparer(dataframe)
        self.assertEqual((len(nouvelles), ignorees), (1, 1))

    def test_ligne_invalide_jamais_ecrite(self):
        nouvelles, ignorees, _ = self.preparer(
            self.dataframe(Professeur='Inconnu')
        )
        self.assertEqual((len(nouvelles), ignorees), (0, 1))
        self.assertEqual(self.session.query(Affectation).count(), 0)


if __name__ == '__main__':
    unittest.main()
