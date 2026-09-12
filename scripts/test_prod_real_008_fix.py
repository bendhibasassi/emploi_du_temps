"""Tests sur copie mémoire d'une sauvegarde immuable ; jamais la base principale.

Le niveau DL-L1 synthétique sert UNIQUEMENT à tester la branche de succès.
Il ne constitue aucune référence métier utilisable en production.
"""
import sqlite3
import unittest
import prod_real_008_fix as fix


class InjectionTests(unittest.TestCase):
    def setUp(self):
        self.c = sqlite3.connect(':memory:', isolation_level=None)
        reader = sqlite3.connect(fix.DRY_DB.resolve().as_uri()+'?mode=ro&immutable=1', uri=True)
        try: reader.backup(self.c)
        finally: reader.close()
        self.c.row_factory = sqlite3.Row
        self.c.execute('PRAGMA foreign_keys=ON')
        self.data = fix.load_inputs()

    def tearDown(self):
        self.c.close()

    def all_rows(self):
        tables = [r[0] for r in self.c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        return {t: fix.snapshot(self.c, t) for t in tables}

    def fixture_dl(self):
        fix.insert(self.c, 'tbl_niveaux', dict(code_niveau='DL-L1', cycle='LICENCE',
                   specialite='TEST UNIQUEMENT', annee_etude='1ère année',
                   libelle='FIXTURE SYNTHETIQUE DL-L1', actif=0))

    def test_missing_dl_report_and_rollback(self):
        before = self.all_rows()
        self.c.execute('BEGIN IMMEDIATE')
        report = {'blocages': []}
        fix.inject(self.c, self.data, report)
        self.assertIn('DL-L3', [r['objet'] for r in report['blocages']])
        self.assertTrue(any('groupes ' in r['objet'] for r in report['blocages']))
        self.assertEqual(report['controles']['permanents_resolus'], 101)
        self.assertEqual(report['controles']['matieres_resolues'], 82)
        self.assertEqual(self.c.execute('SELECT active FROM tbl_annees_univ WHERE libelle=?', ('2025-2026',)).fetchone()[0], 1)
        self.c.rollback()
        self.assertEqual(self.all_rows(), before)

    def test_success_then_idempotence_only_with_synthetic_dl(self):
        self.fixture_dl()
        # Écarter les codifications historiques ambiguës UNIQUEMENT dans cette fixture.
        other_year = fix.insert(self.c, 'tbl_annees_univ', dict(libelle='TEST', date_debut='2000-01-01', date_fin='2000-12-31', active=0))
        self.c.execute('UPDATE tbl_sections SET id_annee=? WHERE id_annee=2', (other_year,))
        self.c.execute('BEGIN IMMEDIATE')
        report = {'blocages': []}
        fix.inject(self.c, self.data, report)
        self.assertFalse(report['blocages'])
        self.assertEqual(report['sections_cibles_resolues'], 17)
        self.assertEqual(report['groupes_cibles_resolus'], 54)
        self.assertEqual(self.c.execute('SELECT active FROM tbl_annees_univ WHERE libelle=?', ('2026-2027',)).fetchone()[0], 1)
        self.c.commit()  # Mémoire uniquement.
        before = self.all_rows()
        self.c.execute('BEGIN IMMEDIATE')
        fix.inject(self.c, self.data, {'blocages': []})
        self.c.commit()
        self.assertEqual(self.all_rows(), before)

    def test_failure_after_writes_rolls_back(self):
        self.fixture_dl()
        before = self.all_rows()
        # Introduire une contradiction de type, après les étapes niveaux/professeurs/groupes.
        self.data['subjects_source'][0]['mode_pedagogique'] = 'TYPE_INVALIDE_TEST'
        self.c.execute('BEGIN IMMEDIATE')
        try:
            with self.assertRaisesRegex(ValueError, 'Type non géré'):
                fix.inject(self.c, self.data, {'blocages': []})
        finally:
            self.c.rollback()
        self.assertEqual(self.all_rows(), before)


if __name__ == '__main__':
    unittest.main()
