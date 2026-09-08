import tempfile
import unittest
from datetime import date
from pathlib import Path

import app as app_module
from app import db
from app.models import (
    Affectation,
    AnneeUniversitaire,
    Groupe,
    Matiere,
    Niveau,
    Professeur,
    Section,
)
from app.routes import analyser_preparation_annee


class CopieAnneeSemestreTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(cls.temp_dir.name) / "copie_annee.db"
        app_module.DATABASE_URI = f"sqlite:///{database_path.as_posix()}"
        cls.app = app_module.create_app()
        cls.app.config.update(TESTING=True)

        with cls.app.app_context():
            cls.source = AnneeUniversitaire(
                libelle="2098-2099", date_debut=date(2098, 9, 1),
                date_fin=date(2099, 6, 30), active=False,
            )
            cls.cible = AnneeUniversitaire(
                libelle="2099-2100", date_debut=date(2099, 9, 1),
                date_fin=date(2100, 6, 30), active=True,
            )
            niveau = Niveau(
                code_niveau="TEST-COPIE", cycle="MASTER",
                specialite="Test", annee_etude="2ème année Master",
                libelle="Test copie année", actif=True,
            )
            professeur = Professeur(
                nom="Professeur copie", prenom="Test", statut="Permanent",
                peut_cm=True, peut_td=True, peut_tp=False, actif=True,
            )
            db.session.add_all([cls.source, cls.cible, niveau, professeur])
            db.session.flush()
            section = Section(
                id_niveau=niveau.id_niveau, code_section="U",
                libelle="Section copie test", actif=True,
            )
            cls.matiere_s3 = Matiere(
                code_matiere="COPIE-S3", nom_matiere="Matière copie S3",
                id_niveau=niveau.id_niveau, semestre="S3",
                avec_cm=True, avec_td=True, actif=True,
            )
            cls.matiere_s5 = Matiere(
                code_matiere="COPIE-S5", nom_matiere="Matière copie S5",
                id_niveau=niveau.id_niveau, semestre="S5",
                avec_cm=True, avec_td=False, actif=True,
            )
            cls.matiere_invalide = Matiere(
                code_matiere="COPIE-INVALIDE",
                nom_matiere="Matière copie invalide",
                id_niveau=niveau.id_niveau, semestre=None,
                avec_cm=True, avec_td=False, actif=True,
            )
            cls.matiere_historique = Matiere(
                code_matiere="COPIE-HISTORIQUE",
                nom_matiere="Matière copie historique",
                id_niveau=niveau.id_niveau, semestre="S3",
                avec_cm=True, avec_td=False, actif=False,
            )
            db.session.add_all([
                section, cls.matiere_s3, cls.matiere_s5,
                cls.matiere_invalide, cls.matiere_historique,
            ])
            db.session.flush()
            groupe = Groupe(
                id_section=section.id_section, code_groupe="G1",
                nom_groupe="Groupe copie", actif=True,
            )
            db.session.add(groupe)
            db.session.commit()
            cls.ids = {
                "source": cls.source.id_annee,
                "cible": cls.cible.id_annee,
                "professeur": professeur.id_professeur,
                "section": section.id_section,
                "groupe": groupe.id_groupe,
                "s3": cls.matiere_s3.id_matiere,
                "s5": cls.matiere_s5.id_matiere,
                "invalide": cls.matiere_invalide.id_matiere,
                "historique": cls.matiere_historique.id_matiere,
            }

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
        cls.temp_dir.cleanup()

    def setUp(self):
        with self.app.app_context():
            Affectation.query.delete()
            db.session.commit()
        self.client = self.app.test_client()
        with self.client.session_transaction() as session:
            session["admin_connecte"] = True
            session["admin_username"] = "test-r2m"
            session["_csrf_token"] = "r2m-token"

    def ajouter_source(
            self, id_matiere, semestre, type_enseignement="CM",
            id_groupe=None):
        with self.app.app_context():
            affectation = Affectation(
                id_annee=self.ids["source"],
                id_professeur=self.ids["professeur"],
                id_matiere=id_matiere,
                id_section=self.ids["section"],
                id_groupe=id_groupe,
                semestre=semestre,
                type_enseignement=type_enseignement,
                nb_seances_semaine=2,
                duree_seance_minutes=90,
                volume_total_minutes=1800,
                priorite=42,
                actif=True,
            )
            db.session.add(affectation)
            db.session.commit()
            return affectation.id_affectation

    def analyser(self):
        with self.app.app_context():
            source = db.session.get(
                AnneeUniversitaire, self.ids["source"]
            )
            cible = db.session.get(
                AnneeUniversitaire, self.ids["cible"]
            )
            return analyser_preparation_annee(source, cible)

    def poster(self):
        return self.client.post(
            "/annees-universitaires/preparer",
            data={
                "_csrf_token": "r2m-token",
                "source_id": str(self.ids["source"]),
                "cible_id": str(self.ids["cible"]),
                "confirmer": "on",
            },
        )

    def nombre_cible(self):
        with self.app.app_context():
            return Affectation.query.filter_by(
                id_annee=self.ids["cible"]
            ).count()

    def test_s3_coherent_autorise_copie_post_et_preserve_champs(self):
        self.ajouter_source(
            self.ids["s3"], 3, "TD", self.ids["groupe"]
        )
        analyse = self.analyser()
        self.assertEqual(analyse["nombre_a_creer"], 1)
        self.assertEqual(analyse["semestres_invalides"], [])
        self.assertEqual(self.poster().status_code, 302)
        with self.app.app_context():
            copie = Affectation.query.filter_by(
                id_annee=self.ids["cible"]
            ).one()
            self.assertEqual(copie.id_professeur, self.ids["professeur"])
            self.assertEqual(copie.id_matiere, self.ids["s3"])
            self.assertEqual(copie.id_section, self.ids["section"])
            self.assertEqual(copie.id_groupe, self.ids["groupe"])
            self.assertEqual(copie.type_enseignement, "TD")
            self.assertEqual(copie.semestre, 3)
            self.assertEqual(copie.volume_total_minutes, 1800)
            self.assertEqual(copie.priorite, 42)
            self.assertTrue(copie.actif)

    def test_s3_incoherent_refuse(self):
        identifiant = self.ajouter_source(self.ids["s3"], 2)
        analyse = self.analyser()
        self.assertEqual(
            analyse["semestres_invalides"][0]["id_affectation"],
            identifiant,
        )
        reponse = self.poster()
        self.assertEqual(reponse.status_code, 200)
        self.assertIn(f"Affectation {identifiant}".encode(), reponse.data)
        self.assertIn(str(self.ids["s3"]).encode(), reponse.data)
        self.assertIn(b"semestre affectation 2", reponse.data)
        self.assertIn(b"S3", reponse.data)
        self.assertEqual(self.nombre_cible(), 0)

    def test_melange_bloque_toute_copie(self):
        self.ajouter_source(self.ids["s3"], 3)
        self.ajouter_source(self.ids["s5"], 1)
        analyse = self.analyser()
        self.assertEqual(analyse["nombre_a_creer"], 1)
        self.assertEqual(len(analyse["semestres_invalides"]), 1)
        self.poster()
        self.assertEqual(self.nombre_cible(), 0)

    def test_s5_coherent_autorise(self):
        self.ajouter_source(self.ids["s5"], 5)
        analyse = self.analyser()
        self.assertEqual(analyse["nombre_a_creer"], 1)
        self.assertEqual(analyse["semestres_invalides"], [])

    def test_s5_incoherent_refuse(self):
        self.ajouter_source(self.ids["s5"], 1)
        analyse = self.analyser()
        self.assertEqual(len(analyse["semestres_invalides"]), 1)
        self.poster()
        self.assertEqual(self.nombre_cible(), 0)

    def test_semestre_matiere_absent_refuse(self):
        self.ajouter_source(self.ids["invalide"], 3)
        analyse = self.analyser()
        self.assertEqual(len(analyse["semestres_invalides"]), 1)
        self.assertIsNone(
            analyse["semestres_invalides"][0]["semestre_matiere"]
        )
        self.poster()
        self.assertEqual(self.nombre_cible(), 0)

    def test_matiere_historique_bloque_globalement_avant_ecriture(self):
        self.ajouter_source(self.ids["s3"], 3)
        identifiant = self.ajouter_source(self.ids["historique"], 3)
        analyse = self.analyser()
        self.assertEqual(len(analyse["matieres_inactives"]), 1)
        self.assertEqual(
            analyse["matieres_inactives"][0]["id_affectation"],
            identifiant,
        )
        reponse = self.poster()
        self.assertEqual(reponse.status_code, 200)
        self.assertIn(b'historiques/inactives', reponse.data)
        self.assertEqual(self.nombre_cible(), 0)


if __name__ == "__main__":
    unittest.main()
