import tempfile
import unittest
from datetime import date, time
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import db
from app.models import (
    Affectation,
    AnneeUniversitaire,
    Creneau,
    Groupe,
    Matiere,
    Niveau,
    Professeur,
    Salle,
    Seance,
    Section,
)
from importer_affectations import (
    ImportAffectationsError,
    preparer_affectations,
    remplacer_affectations,
)


class ImportCmTransactionTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "import_cm.db"
        self.engine = create_engine(f"sqlite:///{self.database_path.as_posix()}")
        db.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)()

        self.annee = AnneeUniversitaire(
            libelle="2099-2100", date_debut=date(2099, 9, 1),
            date_fin=date(2100, 6, 30), active=True,
        )
        self.niveau = Niveau(
            code_niveau="TEST-M2-CM", cycle="MASTER",
            specialite="Test", annee_etude="2ème année Master",
            libelle="Test M2 CM", actif=True,
        )
        self.professeur = Professeur(
            nom="Professeur test", prenom="CM", statut="Permanent",
            peut_cm=True, peut_td=True, peut_tp=False, actif=True,
        )
        self.session.add_all([self.annee, self.niveau, self.professeur])
        self.session.flush()
        self.section = Section(
            id_niveau=self.niveau.id_niveau, code_section="U",
            libelle="Section CM test", actif=True,
        )
        self.matiere = Matiere(
            code_matiere="TEST-CM-S3", nom_matiere="Matière CM test",
            id_niveau=self.niveau.id_niveau, semestre="S3",
            avec_cm=True, avec_td=False, actif=True,
        )
        self.session.add_all([self.section, self.matiere])
        self.session.flush()
        self.ancienne = Affectation(
            id_annee=self.annee.id_annee,
            id_professeur=self.professeur.id_professeur,
            id_matiere=self.matiere.id_matiere,
            id_section=self.section.id_section,
            semestre=3,
            type_enseignement="CM",
            nb_seances_semaine=1,
            duree_seance_minutes=90,
            actif=True,
        )
        self.session.add(self.ancienne)
        self.session.commit()
        self.ancienne_id = self.ancienne.id_affectation

    def tearDown(self):
        self.session.close()
        self.engine.dispose()
        self.temp_dir.cleanup()

    def dataframe(self, semestre="S3"):
        return pd.DataFrame([{
            "Professeur": self.professeur.nom,
            "Matière": self.matiere.nom_matiere,
            "Section": self.section.libelle,
            "Type (CM/TD)": "CM",
            "Semestre": semestre,
        }])

    def ids_affectations(self):
        return [
            valeur for valeur, in self.session.query(
                Affectation.id_affectation
            ).order_by(Affectation.id_affectation).all()
        ]

    def test_import_valide_remplace_avec_un_seul_commit(self):
        nouvelles = preparer_affectations(
            self.session, self.dataframe(), self.annee
        )
        commit_reel = self.session.commit
        with patch.object(
                self.session, "commit", wraps=commit_reel) as commit:
            supprimees, ajoutees = remplacer_affectations(
                self.session, nouvelles, self.annee
            )
        self.assertEqual(commit.call_count, 1)
        self.assertEqual((supprimees, ajoutees), (1, 1))
        self.assertEqual(self.session.query(Affectation).count(), 1)

    def test_erreur_avant_remplacement_conserve_ancienne(self):
        invalide = self.dataframe()
        invalide.loc[0, "Professeur"] = "Inconnu"
        with self.assertRaises(ImportAffectationsError):
            preparer_affectations(self.session, invalide, self.annee)
        self.assertEqual(self.ids_affectations(), [self.ancienne_id])

    def test_erreur_au_flush_declenche_rollback(self):
        nouvelles = preparer_affectations(
            self.session, self.dataframe(), self.annee
        )
        flush_reel = self.session.flush

        def echouer_apres_suppression(*args, **kwargs):
            if self.session.new:
                with self.session.no_autoflush:
                    self.assertEqual(self.session.query(Affectation).count(), 0)
                raise RuntimeError("test flush après suppression")
            return flush_reel(*args, **kwargs)

        with patch.object(
                self.session, "flush", side_effect=echouer_apres_suppression):
            with self.assertRaises(RuntimeError):
                remplacer_affectations(self.session, nouvelles, self.annee)
        self.assertEqual(self.ids_affectations(), [self.ancienne_id])

    def test_semestre_incompatible_conserve_ancienne(self):
        with self.assertRaises(ImportAffectationsError) as contexte:
            preparer_affectations(
                self.session, self.dataframe("S2"), self.annee
            )
        self.assertIn("doit correspondre", str(contexte.exception))
        self.assertEqual(self.ids_affectations(), [self.ancienne_id])

    def test_matiere_inactive_refusee_et_ancienne_conservee(self):
        self.matiere.actif = False
        self.session.commit()
        with self.assertRaises(ImportAffectationsError) as contexte:
            preparer_affectations(
                self.session, self.dataframe(), self.annee
            )
        self.assertIn('Matiere inactive', str(contexte.exception))
        self.assertEqual(self.ids_affectations(), [self.ancienne_id])

    def test_niveau_matiere_inactif_refuse(self):
        self.niveau.actif = False
        self.session.commit()
        with self.assertRaises(ImportAffectationsError):
            preparer_affectations(self.session, self.dataframe(), self.annee)
        self.assertEqual(self.ids_affectations(), [self.ancienne_id])

    def test_niveau_section_inactif_refuse(self):
        self.niveau.actif = False
        self.session.commit()
        with self.assertRaises(ImportAffectationsError):
            preparer_affectations(self.session, self.dataframe(), self.annee)
        self.assertEqual(self.ids_affectations(), [self.ancienne_id])

    def test_incoherence_matiere_section_refusee(self):
        autre_niveau = Niveau(
            code_niveau='AUTRE-CM', cycle='MASTER', specialite='Autre',
            annee_etude='1', libelle='Autre niveau CM', actif=True,
        )
        self.session.add(autre_niveau)
        self.session.flush()
        self.matiere.id_niveau = autre_niveau.id_niveau
        self.session.commit()
        with self.assertRaises(ImportAffectationsError):
            preparer_affectations(self.session, self.dataframe(), self.annee)
        self.assertEqual(self.ids_affectations(), [self.ancienne_id])

    def test_cm_avec_groupe_refuse(self):
        groupe = Groupe(
            id_section=self.section.id_section, code_groupe='G1',
            nom_groupe='Groupe CM', actif=True,
        )
        self.session.add(groupe)
        self.session.commit()
        dataframe = self.dataframe()
        dataframe['Groupe'] = 'G1'
        with self.assertRaises(ImportAffectationsError):
            preparer_affectations(self.session, dataframe, self.annee)
        self.assertEqual(self.ids_affectations(), [self.ancienne_id])

    def test_doublon_fichier_cm_ignore(self):
        dataframe = pd.concat(
            [self.dataframe(), self.dataframe()], ignore_index=True
        )
        nouvelles = preparer_affectations(
            self.session, dataframe, self.annee
        )
        self.assertEqual(len(nouvelles), 1)

    def test_affectation_avec_seance_bloque_remplacement(self):
        creneau = Creneau(
            heure_debut=time(8, 0), heure_fin=time(9, 30),
            ordre=1, actif=True,
        )
        salle = Salle(
            code_salle="TEST-SALLE", nom_salle="Salle test",
            type_salle="AMPHI", capacite=50, actif=True,
        )
        self.session.add_all([creneau, salle])
        self.session.flush()
        seance = Seance(
            id_annee=self.annee.id_annee,
            id_affectation=self.ancienne_id,
            jour=1,
            id_creneau=creneau.id_creneau,
            id_salle=salle.id_salle,
            semaine_type="TOUTES",
            origine="AUTO",
            statut="PROPOSEE",
        )
        self.session.add(seance)
        self.session.commit()
        seance_id = seance.id_seance
        nouvelles = preparer_affectations(
            self.session, self.dataframe(), self.annee
        )

        with self.assertRaises(ImportAffectationsError):
            remplacer_affectations(self.session, nouvelles, self.annee)
        self.assertEqual(self.ids_affectations(), [self.ancienne_id])
        self.assertIsNotNone(self.session.get(Seance, seance_id))

    def test_une_ligne_invalide_bloque_tout_le_fichier(self):
        mixte = pd.concat([
            self.dataframe(),
            self.dataframe("S2"),
        ], ignore_index=True)
        with self.assertRaises(ImportAffectationsError):
            preparer_affectations(self.session, mixte, self.annee)
        self.assertEqual(self.ids_affectations(), [self.ancienne_id])

    def creer_affectations_hors_perimetre(self):
        autre_annee = AnneeUniversitaire(
            libelle='2100-2101', date_debut=date(2100, 9, 1),
            date_fin=date(2101, 6, 30), active=False,
        )
        groupe = Groupe(
            id_section=self.section.id_section, code_groupe='G1',
            nom_groupe='Groupe test', actif=True,
        )
        self.session.add_all([autre_annee, groupe])
        self.session.flush()
        affectations = []
        for annee, type_enseignement in (
                (self.annee, 'TD'), (self.annee, 'TP'),
                (autre_annee, 'CM'), (autre_annee, 'TD'),
                (autre_annee, 'TP')):
            affectation = Affectation(
                id_annee=annee.id_annee,
                id_professeur=self.professeur.id_professeur,
                id_matiere=self.matiere.id_matiere,
                id_section=self.section.id_section,
                id_groupe=groupe.id_groupe if type_enseignement != 'CM' else None,
                semestre=3, type_enseignement=type_enseignement,
                nb_seances_semaine=1, duree_seance_minutes=90, actif=True,
            )
            self.session.add(affectation)
            affectations.append(affectation)
        self.session.commit()
        return affectations

    def test_td_tp_et_autres_annees_conserves(self):
        conservees = self.creer_affectations_hors_perimetre()
        ids = [a.id_affectation for a in conservees]
        nouvelles = preparer_affectations(
            self.session, self.dataframe(), self.annee
        )
        self.assertEqual(
            remplacer_affectations(self.session, nouvelles, self.annee), (1, 1)
        )
        self.session.expire_all()
        for identifiant in ids:
            with self.subTest(id_affectation=identifiant):
                self.assertIsNotNone(self.session.get(Affectation, identifiant))
        self.assertNotIn(self.ancienne_id, self.ids_affectations())
        self.assertEqual(self.session.query(Affectation).count(), 6)

    def test_seances_hors_perimetre_ne_bloquent_pas(self):
        conservees = self.creer_affectations_hors_perimetre()
        creneau = Creneau(
            heure_debut=time(8, 0), heure_fin=time(9, 30), ordre=1, actif=True,
        )
        salle = Salle(
            code_salle='HORS-CM', nom_salle='Salle test',
            type_salle='AMPHI', capacite=50, actif=True,
        )
        self.session.add_all([creneau, salle])
        self.session.flush()
        seances = []
        for jour, affectation in enumerate(conservees, 1):
            seance = Seance(
                id_annee=affectation.id_annee,
                id_affectation=affectation.id_affectation,
                jour=jour, id_creneau=creneau.id_creneau,
                id_salle=salle.id_salle, semaine_type='TOUTES',
                origine='AUTO', statut='PROPOSEE',
            )
            self.session.add(seance)
            seances.append(seance)
        self.session.commit()
        liens = [(s.id_seance, s.id_affectation) for s in seances]
        nouvelles = preparer_affectations(
            self.session, self.dataframe(), self.annee
        )
        self.assertEqual(
            remplacer_affectations(self.session, nouvelles, self.annee), (1, 1)
        )
        self.session.expire_all()
        for id_seance, id_affectation in liens:
            with self.subTest(id_seance=id_seance):
                self.assertEqual(
                    self.session.get(Seance, id_seance).id_affectation,
                    id_affectation,
                )
                self.assertIsNotNone(
                    self.session.get(Affectation, id_affectation)
                )

    def test_cm_inactif_annee_cible_remplace(self):
        self.ancienne.actif = False
        self.session.commit()
        nouvelles = preparer_affectations(
            self.session, self.dataframe(), self.annee
        )
        self.assertEqual(
            remplacer_affectations(self.session, nouvelles, self.annee), (1, 1)
        )
        self.assertEqual(self.session.query(Affectation).count(), 1)
        self.assertTrue(self.session.query(Affectation).one().actif)

    def test_fichier_vide_ne_vide_pas_les_affectations(self):
        vide = pd.DataFrame(columns=sorted({
            "Professeur", "Matière", "Section", "Type (CM/TD)", "Semestre",
        }))
        with self.assertRaises(ImportAffectationsError):
            preparer_affectations(self.session, vide, self.annee)
        self.assertEqual(self.ids_affectations(), [self.ancienne_id])


if __name__ == "__main__":
    unittest.main()
