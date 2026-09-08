import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from flask import Flask

import app as app_module
from app import db
from app.models import Professeur


class ModifierProfesseurTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        database_path = Path(self.temp_dir.name) / 'professeurs_test.db'
        uri = f'sqlite:///{database_path.as_posix()}'
        # Prepare only the temporary database before create_app queries it.
        bootstrap = Flask(__name__)
        bootstrap.config['SQLALCHEMY_DATABASE_URI'] = uri
        db.init_app(bootstrap)
        with bootstrap.app_context():
            db.create_all()
            db.session.remove()
            db.engine.dispose()
        with patch.object(app_module, 'DATABASE_URI', uri):
            self.app = app_module.create_app()
        self.app.config.update(TESTING=True)
        self.addCleanup(self.close_database)
        self.client = self.app.test_client()
        with self.client.session_transaction() as session:
            session['admin_connecte'] = True
            session['_csrf_token'] = 'test-token'
        self.form = {
            'nom': 'Test', 'prenom': 'Initial', 'grade': 'Assistant',
            'email': 'initial@example.test', 'telephone': '0102030405',
            'actif': 'on', '_csrf_token': 'test-token',
        }

    def close_database(self):
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()

    def create_professor(self, statut, cm, td, tp):
        with self.app.app_context():
            professeur = Professeur(
                **{key: self.form[key] for key in
                   ('nom', 'prenom', 'grade', 'email', 'telephone')},
                actif=True, statut=statut, peut_cm=cm, peut_td=td, peut_tp=tp,
            )
            db.session.add(professeur)
            db.session.commit()
            self.professor_id = professeur.id_professeur
        self.url = f'/professeur/{self.professor_id}/modifier'

    def submit_and_check(self, protected):
        response = self.client.post(self.url, data=self.form)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith('/professeurs'))
        with self.app.app_context():
            professeur = db.session.get(Professeur, self.professor_id)
            self.assertEqual(
                (professeur.statut, professeur.peut_cm,
                 professeur.peut_td, professeur.peut_tp), protected,
            )
            for field in ('nom', 'prenom', 'grade', 'email', 'telephone'):
                self.assertEqual(getattr(professeur, field), self.form[field])
            self.assertEqual(professeur.actif, self.form.get('actif') == 'on')

    def test_vacataire_telephone_preserves_absent_fields(self):
        self.create_professor('Vacataire', False, True, False)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        for field in ('statut', 'peut_cm', 'peut_td', 'peut_tp'):
            self.assertNotIn(f'name="{field}"', response.get_data(as_text=True))
        self.form['telephone'] = '0999999999'
        self.submit_and_check(('Vacataire', False, True, False))

    def test_permanent_email_preserves_absent_fields(self):
        self.create_professor('Permanent', True, True, True)
        self.form['email'] = 'nouveau@example.test'
        self.submit_and_check(('Permanent', True, True, True))

    def test_visible_fields_still_change(self):
        self.create_professor('Vacataire', False, True, False)
        self.form.update(nom='Nouveau', prenom='Prenom', grade='Doctorant',
                         email='visible@example.test', telephone='0888888888')
        self.form.pop('actif')
        self.submit_and_check(('Vacataire', False, True, False))

    def test_present_fields_keep_existing_submission_behavior(self):
        self.create_professor('Permanent', False, True, True)
        self.form.update(statut='Vacataire', peut_cm='on', peut_td='')
        self.submit_and_check(('Vacataire', True, False, True))


if __name__ == '__main__':
    unittest.main()
