"""Baseline du schema historique actuel.

Revision ID: d7f3a91c4b20
Revises:
Create Date: 2026-08-29
"""

from alembic import op
import sqlalchemy as sa


revision = "d7f3a91c4b20"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tbl_annees_univ",
        sa.Column("id_annee", sa.Integer(), nullable=False),
        sa.Column("libelle", sa.String(9), nullable=False),
        sa.Column("date_debut", sa.Date(), nullable=False),
        sa.Column("date_fin", sa.Date(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id_annee"),
        sa.UniqueConstraint("libelle"),
    )
    op.create_table(
        "tbl_niveaux",
        sa.Column("id_niveau", sa.Integer(), nullable=False),
        sa.Column("code_niveau", sa.String(30), nullable=False),
        sa.Column("cycle", sa.String(20), nullable=False),
        sa.Column("specialite", sa.String(150), nullable=False),
        sa.Column("annee_etude", sa.String(10), nullable=False),
        sa.Column("libelle", sa.String(200), nullable=False),
        sa.Column("actif", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id_niveau"),
        sa.UniqueConstraint("code_niveau"),
        sa.UniqueConstraint("libelle"),
    )
    op.create_table(
        "tbl_professeurs",
        sa.Column("id_professeur", sa.Integer(), nullable=False),
        sa.Column("nom", sa.String(100), nullable=False),
        sa.Column("prenom", sa.String(100), nullable=True),
        sa.Column("grade", sa.String(100), nullable=True),
        sa.Column("email", sa.String(254), nullable=True),
        sa.Column("telephone", sa.String(30), nullable=True),
        sa.Column("actif", sa.Boolean(), nullable=True),
        sa.Column("statut", sa.String(20), server_default="Permanent", nullable=True),
        sa.Column("peut_cm", sa.Boolean(), server_default=sa.text("1"), nullable=True),
        sa.Column("peut_td", sa.Boolean(), server_default=sa.text("1"), nullable=True),
        sa.Column("peut_tp", sa.Boolean(), server_default=sa.text("0"), nullable=True),
        sa.PrimaryKeyConstraint("id_professeur"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "tbl_salles",
        sa.Column("id_salle", sa.Integer(), nullable=False),
        sa.Column("code_salle", sa.String(30), nullable=False),
        sa.Column("nom_salle", sa.String(150), nullable=False),
        sa.Column("type_salle", sa.String(30), nullable=False),
        sa.Column("capacite", sa.Integer(), nullable=False),
        sa.Column("batiment", sa.String(150), nullable=True),
        sa.Column("actif", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id_salle"),
        sa.UniqueConstraint("code_salle"),
    )
    op.create_table(
        "tbl_creneaux",
        sa.Column("id_creneau", sa.Integer(), nullable=False),
        sa.Column("heure_debut", sa.Time(), nullable=False),
        sa.Column("heure_fin", sa.Time(), nullable=False),
        sa.Column("ordre", sa.Integer(), nullable=False),
        sa.Column("actif", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id_creneau"),
        sa.UniqueConstraint("ordre"),
    )
    op.create_table(
        "tbl_sections",
        sa.Column("id_section", sa.Integer(), nullable=False),
        sa.Column("id_niveau", sa.Integer(), nullable=False),
        sa.Column("code_section", sa.String(30), nullable=False),
        sa.Column("libelle", sa.String(150), nullable=False),
        sa.Column("effectif", sa.Integer(), nullable=True),
        sa.Column("actif", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(["id_niveau"], ["tbl_niveaux.id_niveau"]),
        sa.PrimaryKeyConstraint("id_section"),
        sa.UniqueConstraint("id_niveau", "code_section", name="uq_section_niveau_code"),
    )
    op.create_table(
        "tbl_groupes",
        sa.Column("id_groupe", sa.Integer(), nullable=False),
        sa.Column("id_section", sa.Integer(), nullable=False),
        sa.Column("code_groupe", sa.String(20), nullable=False),
        sa.Column("nom_groupe", sa.String(100), nullable=False),
        sa.Column("effectif", sa.Integer(), nullable=True),
        sa.Column("actif", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(["id_section"], ["tbl_sections.id_section"]),
        sa.PrimaryKeyConstraint("id_groupe"),
        sa.UniqueConstraint("id_section", "code_groupe", name="uq_section_code_groupe"),
    )
    op.create_table(
        "tbl_matieres",
        sa.Column("id_matiere", sa.Integer(), nullable=False),
        sa.Column("code_matiere", sa.String(30), nullable=False),
        sa.Column("nom_matiere", sa.String(200), nullable=False),
        sa.Column("actif", sa.Boolean(), nullable=True),
        sa.Column("id_niveau", sa.Integer(), nullable=True),
        sa.Column("semestre", sa.String(10), nullable=True),
        sa.Column("avec_cm", sa.Boolean(), nullable=True),
        sa.Column("avec_td", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(
            ["id_niveau"], ["tbl_niveaux.id_niveau"], name="fk_matieres_id_niveau"
        ),
        sa.PrimaryKeyConstraint("id_matiere"),
        sa.UniqueConstraint("code_matiere"),
    )
    op.create_table(
        "tbl_affectations",
        sa.Column("id_affectation", sa.Integer(), nullable=False),
        sa.Column("id_annee", sa.Integer(), nullable=False),
        sa.Column("id_professeur", sa.Integer(), nullable=False),
        sa.Column("id_matiere", sa.Integer(), nullable=False),
        sa.Column("id_section", sa.Integer(), nullable=False),
        sa.Column("semestre", sa.Integer(), nullable=False),
        sa.Column("type_enseignement", sa.String(10), nullable=False),
        sa.Column("nb_seances_semaine", sa.Integer(), nullable=True),
        sa.Column("duree_seance_minutes", sa.Integer(), nullable=True),
        sa.Column("volume_total_minutes", sa.Integer(), nullable=True),
        sa.Column("priorite", sa.Integer(), nullable=True),
        sa.Column("actif", sa.Boolean(), nullable=True),
        sa.Column("id_groupe", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["id_annee"], ["tbl_annees_univ.id_annee"]),
        sa.ForeignKeyConstraint(["id_professeur"], ["tbl_professeurs.id_professeur"]),
        sa.ForeignKeyConstraint(["id_matiere"], ["tbl_matieres.id_matiere"]),
        sa.ForeignKeyConstraint(["id_section"], ["tbl_sections.id_section"]),
        sa.ForeignKeyConstraint(["id_groupe"], ["tbl_groupes.id_groupe"]),
        sa.PrimaryKeyConstraint("id_affectation"),
    )
    op.create_table(
        "tbl_seances",
        sa.Column("id_seance", sa.Integer(), nullable=False),
        sa.Column("id_annee", sa.Integer(), nullable=False),
        sa.Column("id_affectation", sa.Integer(), nullable=False),
        sa.Column("jour", sa.Integer(), nullable=False),
        sa.Column("id_creneau", sa.Integer(), nullable=False),
        sa.Column("id_salle", sa.Integer(), nullable=False),
        sa.Column("semaine_type", sa.String(10), nullable=True),
        sa.Column("verrouillee", sa.Boolean(), nullable=True),
        sa.Column("origine", sa.String(10), nullable=True),
        sa.Column("statut", sa.String(15), nullable=True),
        sa.ForeignKeyConstraint(["id_affectation"], ["tbl_affectations.id_affectation"]),
        sa.ForeignKeyConstraint(["id_creneau"], ["tbl_creneaux.id_creneau"]),
        sa.ForeignKeyConstraint(["id_salle"], ["tbl_salles.id_salle"]),
        sa.PrimaryKeyConstraint("id_seance"),
        sa.UniqueConstraint(
            "id_annee", "jour", "id_creneau", "id_salle", "semaine_type",
            name="uq_seance_salle",
        ),
    )
    op.create_table(
        "tbl_indisponibilites",
        sa.Column("id_indisponibilite", sa.Integer(), nullable=False),
        sa.Column("id_annee", sa.Integer(), nullable=False),
        sa.Column("id_professeur", sa.Integer(), nullable=False),
        sa.Column("jour", sa.Integer(), nullable=False),
        sa.Column("id_creneau", sa.Integer(), nullable=False),
        sa.Column("type_contrainte", sa.String(15), nullable=True),
        sa.Column("commentaire", sa.String(500), nullable=True),
        sa.Column("actif", sa.Boolean(), server_default=sa.text("1"), nullable=True),
        sa.ForeignKeyConstraint(["id_annee"], ["tbl_annees_univ.id_annee"]),
        sa.ForeignKeyConstraint(["id_professeur"], ["tbl_professeurs.id_professeur"]),
        sa.ForeignKeyConstraint(["id_creneau"], ["tbl_creneaux.id_creneau"]),
        sa.PrimaryKeyConstraint("id_indisponibilite"),
    )
    op.create_table(
        "tbl_historique",
        sa.Column("id_historique", sa.Integer(), nullable=False),
        sa.Column("utilisateur", sa.String(100), nullable=False),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("type_objet", sa.String(30), nullable=False),
        sa.Column("id_objet", sa.Integer(), nullable=False),
        sa.Column("ancienne_valeur", sa.Text(), nullable=True),
        sa.Column("nouvelle_valeur", sa.Text(), nullable=True),
        sa.Column("date_heure", sa.DateTime(), nullable=True),
        sa.Column("ip_adresse", sa.String(45), nullable=True),
        sa.PrimaryKeyConstraint("id_historique"),
    )


def downgrade():
    op.drop_table("tbl_historique")
    op.drop_table("tbl_indisponibilites")
    op.drop_table("tbl_seances")
    op.drop_table("tbl_affectations")
    op.drop_table("tbl_matieres")
    op.drop_table("tbl_groupes")
    op.drop_table("tbl_sections")
    op.drop_table("tbl_creneaux")
    op.drop_table("tbl_salles")
    op.drop_table("tbl_professeurs")
    op.drop_table("tbl_niveaux")
    op.drop_table("tbl_annees_univ")
