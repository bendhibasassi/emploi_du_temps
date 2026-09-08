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


class ValidationSemestreAffectationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(cls.temp_dir.name) / 'r2j_test.db'
        app_module.DATABASE_URI = f'sqlite:///{database_path.as_posix()}'
        cls.app = app_module.create_app()
        cls.app.config.update(TESTING=True)

        with cls.app.app_context():
            annee = AnneeUniversitaire(
                libelle='2099-2100', date_debut=date(2099, 9, 1),
                date_fin=date(2100, 6, 30), active=True,
            )
            niveau_m2 = Niveau(
                code_niveau='TEST-M2', cycle='MASTER',
                specialite='Test M2', annee_etude='2ème année Master',
                libelle='Test M2', actif=True,
            )
            niveau_l3 = Niveau(
                code_niveau='TEST-L3', cycle='LICENCE',
                specialite='Test L3', annee_etude='3ème année',
                libelle='Test L3', actif=True,
            )
            professeur = Professeur(
                nom='Test', prenom='R2J', statut='Permanent',
                peut_cm=True, peut_td=True, peut_tp=True, actif=True,
            )
            db.session.add_all([annee, niveau_m2, niveau_l3, professeur])
            db.session.flush()

            section_m2 = Section(
                id_niveau=niveau_m2.id_niveau, code_section='U',
                libelle='Section M2 test', actif=True,
            )
            section_l3 = Section(
                id_niveau=niveau_l3.id_niveau, code_section='U',
                libelle='Section L3 test', actif=True,
            )
            matiere_s3 = Matiere(
                code_matiere='TEST-S3', nom_matiere='Matière S3 test',
                id_niveau=niveau_m2.id_niveau, semestre='S3',
                avec_cm=True, avec_td=True, actif=True,
            )
            matiere_s5 = Matiere(
                code_matiere='TEST-S5', nom_matiere='Matière S5 test',
                id_niveau=niveau_l3.id_niveau, semestre='S5',
                avec_cm=True, avec_td=False, actif=True,
            )
            matiere_historique = Matiere(
                code_matiere='TEST-HIST',
                nom_matiere='Matière historique test',
                id_niveau=niveau_l3.id_niveau, semestre='S5',
                avec_cm=True, avec_td=False, actif=False,
            )
            db.session.add_all([
                section_m2, section_l3, matiere_s3, matiere_s5,
                matiere_historique,
            ])
            db.session.flush()
            groupe = Groupe(
                id_section=section_m2.id_section, code_groupe='G1',
                nom_groupe='Groupe 1', actif=True,
            )
            db.session.add(groupe)
            db.session.commit()

            cls.ids = {
                'annee': annee.id_annee,
                'professeur': professeur.id_professeur,
                'section_m2': section_m2.id_section,
                'section_l3': section_l3.id_section,
                'groupe': groupe.id_groupe,
                'matiere_s3': matiere_s3.id_matiere,
                'matiere_s5': matiere_s5.id_matiere,
                'matiere_historique': matiere_historique.id_matiere,
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
            session['admin_connecte'] = True
            session['admin_username'] = 'test-r2j'
            session['_csrf_token'] = 'r2j-token'

    def formulaire(self, matiere, section, semestre, **overrides):
        donnees = {
            '_csrf_token': 'r2j-token',
            'id_annee': str(self.ids['annee']),
            'id_professeur': str(self.ids['professeur']),
            'id_matiere': str(matiere),
            'id_section': str(section),
            'id_groupe': '',
            'type_enseignement': 'CM',
            'semestre': str(semestre),
            'nb_seances_semaine': '1',
            'duree_seance_minutes': '90',
            'volume_total_minutes': '',
            'priorite': '50',
            'actif': 'on',
        }
        donnees.update(overrides)
        return donnees

    def nombre_affectations(self):
        with self.app.app_context():
            return Affectation.query.count()

    def test_creation_s3_acceptee_et_post_s2_refuse(self):
        avant = self.nombre_affectations()
        reponse = self.client.post('/affectation/ajouter', data=self.formulaire(
            self.ids['matiere_s3'], self.ids['section_m2'], 3,
        ))
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(self.nombre_affectations(), avant + 1)

        reponse = self.client.post('/affectation/ajouter', data=self.formulaire(
            self.ids['matiere_s3'], self.ids['section_m2'], 2,
        ))
        self.assertEqual(reponse.status_code, 200)
        self.assertIn(b'doit correspondre au semestre', reponse.data)
        self.assertEqual(self.nombre_affectations(), avant + 1)

    def test_creation_s5_acceptee_et_s1_refusee(self):
        avant = self.nombre_affectations()
        reponse = self.client.post('/affectation/ajouter', data=self.formulaire(
            self.ids['matiere_s5'], self.ids['section_l3'], 5,
        ))
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(self.nombre_affectations(), avant + 1)

        reponse = self.client.post('/affectation/ajouter', data=self.formulaire(
            self.ids['matiere_s5'], self.ids['section_l3'], 1,
        ))
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(self.nombre_affectations(), avant + 1)

    def test_modification_correcte_acceptee_et_incorrecte_refusee(self):
        self.client.post('/affectation/ajouter', data=self.formulaire(
            self.ids['matiere_s3'], self.ids['section_m2'], 3,
            priorite='51',
        ))
        with self.app.app_context():
            affectation = Affectation.query.filter_by(priorite=51).one()
            identifiant = affectation.id_affectation

        reponse = self.client.post(
            f'/affectation/{identifiant}/modifier',
            data=self.formulaire(
                self.ids['matiere_s3'], self.ids['section_m2'], 3,
                priorite='52',
            ),
        )
        self.assertEqual(reponse.status_code, 302)

        reponse = self.client.post(
            f'/affectation/{identifiant}/modifier',
            data=self.formulaire(
                self.ids['matiere_s3'], self.ids['section_m2'], 2,
                priorite='99',
            ),
        )
        self.assertEqual(reponse.status_code, 200)
        with self.app.app_context():
            affectation = db.session.get(Affectation, identifiant)
            self.assertEqual(affectation.semestre, 3)
            self.assertEqual(affectation.priorite, 52)

    def test_controles_cm_td_groupe_et_doublon_restent_actifs(self):
        avant = self.nombre_affectations()
        reponse = self.client.post('/affectation/ajouter', data=self.formulaire(
            self.ids['matiere_s3'], self.ids['section_l3'], 3,
        ))
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(self.nombre_affectations(), avant)

        reponse = self.client.post('/affectation/ajouter', data=self.formulaire(
            self.ids['matiere_s3'], self.ids['section_m2'], 3,
            id_groupe=str(self.ids['groupe']), type_enseignement='CM',
        ))
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(self.nombre_affectations(), avant)

        reponse = self.client.post('/affectation/ajouter', data=self.formulaire(
            self.ids['matiere_s3'], self.ids['section_m2'], 3,
            id_groupe=str(self.ids['groupe']), type_enseignement='TD',
        ))
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(self.nombre_affectations(), avant + 1)

        reponse = self.client.post('/affectation/ajouter', data=self.formulaire(
            self.ids['matiere_s3'], self.ids['section_m2'], 3,
            id_groupe=str(self.ids['groupe']), type_enseignement='TD',
        ))
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(self.nombre_affectations(), avant + 1)

    def test_matiere_historique_masquee_et_creation_post_refusee(self):
        reponse = self.client.get('/affectation/ajouter')

        avant = self.nombre_affectations()
        reponse = self.client.post('/affectation/ajouter', data=self.formulaire(
            self.ids['matiere_historique'], self.ids['section_l3'], 5,
        ))
        self.assertEqual(reponse.status_code, 200)
        self.assertIn(b'historique/inactive', reponse.data)
        self.assertEqual(self.nombre_affectations(), avant)

    def test_affectation_historique_lisible_mais_modification_refusee(self):
        with self.app.app_context():
            affectation = Affectation(
                id_annee=self.ids['annee'],
                id_professeur=self.ids['professeur'],
                id_matiere=self.ids['matiere_historique'],
                id_section=self.ids['section_l3'],
                semestre=5, type_enseignement='CM',
                nb_seances_semaine=1, duree_seance_minutes=90,
                priorite=50, actif=True,
            )
            db.session.add(affectation)
            db.session.commit()
            identifiant = affectation.id_affectation

        reponse = self.client.get(f'/affectation/{identifiant}/modifier')
        self.assertEqual(reponse.status_code, 200)
        self.assertIn(b'TEST-HIST', reponse.data)

        reponse = self.client.post(
            f'/affectation/{identifiant}/modifier',
            data=self.formulaire(
                self.ids['matiere_historique'], self.ids['section_l3'], 5,
                priorite='77',
            ),
        )
        self.assertEqual(reponse.status_code, 200)
        self.assertIn(b'historique/inactive', reponse.data)
        with self.app.app_context():
            affectation = db.session.get(Affectation, identifiant)
            self.assertEqual(affectation.id_matiere, self.ids['matiere_historique'])
            self.assertEqual(affectation.priorite, 50)

    def test_modification_vers_matiere_historique_refusee(self):
        self.client.post('/affectation/ajouter', data=self.formulaire(
            self.ids['matiere_s5'], self.ids['section_l3'], 5,
            priorite='63',
        ))
        with self.app.app_context():
            identifiant = Affectation.query.filter_by(priorite=63).one().id_affectation
        reponse = self.client.post(
            f'/affectation/{identifiant}/modifier',
            data=self.formulaire(
                self.ids['matiere_historique'], self.ids['section_l3'], 5,
                priorite='64',
            ),
        )
        self.assertEqual(reponse.status_code, 200)
        self.assertIn(b'historique/inactive', reponse.data)
        with self.app.app_context():
            affectation = db.session.get(Affectation, identifiant)
            self.assertEqual(affectation.id_matiere, self.ids['matiere_s5'])
            self.assertEqual(affectation.priorite, 63)

    def test_attribution_professeur_hors_validation_r2j(self):
        with self.app.app_context():
            affectation = Affectation(
                id_annee=self.ids['annee'],
                id_professeur=self.ids['professeur'],
                id_matiere=self.ids['matiere_historique'],
                id_section=self.ids['section_l3'],
                semestre=5, type_enseignement='CM',
                nb_seances_semaine=1, duree_seance_minutes=90,
                priorite=50, actif=True,
            )
            db.session.add(affectation)
            db.session.commit()
            identifiant = affectation.id_affectation

        reponse = self.client.get(
            f'/affectation/{identifiant}/attribuer-professeur'
        )
        self.assertEqual(reponse.status_code, 302)

if __name__ == '__main__':
    unittest.main()
