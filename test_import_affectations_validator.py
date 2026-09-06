import unittest
from types import SimpleNamespace

from app.services.import_affectations import valider_lignes_import


class Query:
    def __init__(self, values): self.values = values
    def filter_by(self, **kw): return Query([x for x in self.values if all(getattr(x, k, None) == v for k, v in kw.items())])
    def all(self): return list(self.values)


class Session:
    def __init__(self, objects): self.objects = objects
    def query(self, model): return Query(self.objects.get(model, []))
    def _ecriture_interdite(self, *args, **kwargs):
        raise AssertionError('Le validateur ne doit pas ecrire dans la session.')
    add = add_all = delete = flush = commit = rollback = _ecriture_interdite


class ValidatorTests(unittest.TestCase):
    def setUp(self):
        from app.models import Affectation, Groupe, Matiere, Professeur, Section
        self.models = (Affectation, Groupe, Matiere, Professeur, Section)
        self.niveau = SimpleNamespace(id_niveau=10, actif=True)
        self.prof = SimpleNamespace(id_professeur=1, nom='Durand', actif=True)
        self.mat = SimpleNamespace(id_matiere=2, nom_matiere='Droit', semestre='S1', actif=True,
                                   id_niveau=10, niveau=self.niveau)
        self.sec = SimpleNamespace(id_section=3, libelle='Section A', actif=True,
                                   id_niveau=10, niveau=self.niveau)
        self.grp = SimpleNamespace(id_groupe=4, code_groupe='G1', id_section=3,
                                   actif=True, section=self.sec)
        self.session = Session({Professeur:[self.prof], Matiere:[self.mat], Section:[self.sec], Groupe:[self.grp], Affectation:[]})
        self.annee = SimpleNamespace(id_annee=9)

    def ligne(self, **changes):
        row = {'Professeur':'Durand','Matiere':'Droit','Section':'Section A','Groupe':'G1','Type_enseignement':'TD','Semestre':'S1','Nb_seances_semaine':1,'Duree_seance_minutes':90,'Volume_total_minutes':'','Priorite':50,'Actif':'oui'}
        row.update(changes); return row

    def test_valid_and_invalid(self):
        result = valider_lignes_import(self.session, [self.ligne(), self.ligne(Semestre='S9')], self.annee)
        self.assertEqual(result['resultats'][0]['statut'], 'PRETE_A_IMPORTER')
        self.assertEqual(result['resultats'][1]['statut'], 'ERREUR_BLOQUANTE')

    def test_no_session_writes(self):
        result = valider_lignes_import(self.session, [self.ligne()], self.annee)
        self.assertEqual(result['statut_global'], 'PRETE_A_IMPORTER')

    def assert_error(self, **changes):
        result = valider_lignes_import(self.session, [self.ligne(**changes)], self.annee)
        self.assertEqual(result['resultats'][0]['statut'], 'ERREUR_BLOQUANTE')

    def assert_error_contains(self, texte, **changes):
        result = valider_lignes_import(self.session, [self.ligne(**changes)], self.annee)
        self.assertIn(texte, result['resultats'][0]['erreurs'])

    def test_references_introuvables(self):
        self.assert_error(Professeur='Inconnu')
        self.assert_error(Matiere='Inconnue')
        self.assert_error(Section='Inconnue', Groupe='')

    def test_groupe_incoherent(self):
        from app.models import Groupe
        autre_section = SimpleNamespace(id_section=99, actif=True, niveau=self.niveau)
        self.session.objects[Groupe].append(SimpleNamespace(
            id_groupe=5, code_groupe='G2', id_section=99,
            actif=True, section=autre_section,
        ))
        self.assert_error(Groupe='G2')

    def test_referentiels_inactifs_et_niveaux(self):
        self.mat.actif = False
        self.assert_error()
        self.mat.actif = True
        self.mat.niveau.actif = False
        self.assert_error()
        self.mat.niveau.actif = True

        self.sec.actif = False
        self.assert_error()
        self.sec.actif = True
        self.sec.niveau.actif = False
        self.assert_error()

    def test_section_inexistante_avec_groupe_est_une_erreur_structuree(self):
        self.assert_error(Section='Inconnue', Groupe='G1')

    def test_incoherence_matiere_section(self):
        self.mat.id_niveau = 11
        self.assert_error()

    def test_groupes_invalides(self):
        self.assert_error(Groupe='INCONNU')
        self.grp.actif = False
        self.assert_error()
        self.grp.actif = True
        self.grp.section = SimpleNamespace(
            id_section=self.sec.id_section, actif=True,
            niveau=SimpleNamespace(actif=False),
        )
        self.assert_error_contains('Niveau du groupe inactif.')

    def test_groupe_resolu_dans_sa_section(self):
        from app.models import Groupe
        autre_section = SimpleNamespace(id_section=99, actif=True, niveau=self.niveau)
        self.session.objects[Groupe].append(SimpleNamespace(
            id_groupe=5, code_groupe='G1', id_section=99,
            actif=True, section=autre_section,
        ))
        result = valider_lignes_import(
            self.session, [self.ligne()], self.annee
        )
        self.assertEqual(result['resultats'][0]['statut'], 'PRETE_A_IMPORTER')
        self.assertIs(result['resultats'][0]['references']['groupe'], self.grp)

    def test_regles_structurelles_cm_td_tp(self):
        self.assert_error(Type_enseignement='CM', Groupe='G1')
        self.assert_error(Type_enseignement='TD', Groupe='')
        self.assert_error(Type_enseignement='TP', Groupe='')
        result = valider_lignes_import(
            self.session, [self.ligne(Type_enseignement='TP')], self.annee
        )
        self.assertEqual(result['resultats'][0]['statut'], 'PRETE_A_IMPORTER')

    def test_professeur_inactif(self):
        self.prof.actif = False
        self.assert_error()

    def test_valeurs_invalides(self):
        self.assert_error(Type_enseignement='XX')
        self.assert_error(Semestre='S9')
        self.assert_error(Nb_seances_semaine=0)
        self.assert_error(Duree_seance_minutes=0)
        self.assert_error(Volume_total_minutes=-1)
        self.assert_error(Priorite=-1)
        self.assert_error(Actif='peut-être')

    def test_doublons_base_et_fichier(self):
        from app.models import Affectation
        existing = SimpleNamespace(id_annee=9, id_professeur=1, id_matiere=2, id_section=3,
                                   id_groupe=4, type_enseignement='TD', semestre=1)
        self.session.objects[Affectation].append(existing)
        result = valider_lignes_import(self.session, [self.ligne()], self.annee)
        self.assertEqual(result['resultats'][0]['statut'], 'DOUBLON_IGNORE')

        self.session.objects[Affectation].clear()
        result = valider_lignes_import(self.session, [self.ligne(), self.ligne()], self.annee)
        self.assertEqual(result['resultats'][0]['statut'], 'PRETE_A_IMPORTER')
        self.assertEqual(result['resultats'][1]['statut'], 'DOUBLON_IGNORE')


if __name__ == '__main__': unittest.main()
