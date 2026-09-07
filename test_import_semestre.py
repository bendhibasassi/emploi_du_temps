import unittest
from types import SimpleNamespace

from app.services.affectation_rules import valider_semestre_import


class ValidationSemestreImportTest(unittest.TestCase):
    def verifier(self, semestre_matiere, valeur_importee):
        matiere = SimpleNamespace(semestre=semestre_matiere)
        return valider_semestre_import(matiere, valeur_importee)

    def test_import_cm_s3_correct_et_incorrect(self):
        self.assertEqual(self.verifier('S3', 'S3'), (3, None))
        semestre, erreur = self.verifier('S3', 'S2')
        self.assertIsNone(semestre)
        self.assertIn('doit correspondre', erreur)

    def test_import_cm_s5_correct_et_incorrect(self):
        self.assertEqual(self.verifier('S5', 5), (5, None))
        semestre, erreur = self.verifier('S5', 1)
        self.assertIsNone(semestre)
        self.assertIn('doit correspondre', erreur)

    def test_import_td_s3_correct_et_incorrect(self):
        self.assertEqual(self.verifier('S3', 3), (3, None))
        semestre, erreur = self.verifier('S3', 2)
        self.assertIsNone(semestre)
        self.assertIn('doit correspondre', erreur)

    def test_semestre_matiere_absent_ou_invalide_est_refuse(self):
        for valeur in (None, '', 'S9'):
            with self.subTest(valeur=valeur):
                semestre, erreur = self.verifier(valeur, 3)
                self.assertIsNone(semestre)
                self.assertIn('ne peut pas être validée automatiquement', erreur)

    def test_semestre_importe_invalide_est_refuse(self):
        for valeur in ('', 'abc', 'S7', 0):
            with self.subTest(valeur=valeur):
                semestre, erreur = self.verifier('S3', valeur)
                self.assertIsNone(semestre)
                self.assertEqual(erreur, 'Le semestre importé est invalide.')


if __name__ == '__main__':
    unittest.main()
