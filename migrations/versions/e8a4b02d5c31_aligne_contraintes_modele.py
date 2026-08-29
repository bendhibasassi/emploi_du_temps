"""Aligne les contraintes confirmees avec le modele officiel.

Revision ID: e8a4b02d5c31
Revises: d7f3a91c4b20
Create Date: 2026-08-29
"""

from alembic import op
import sqlalchemy as sa


revision = "e8a4b02d5c31"
down_revision = "d7f3a91c4b20"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("PRAGMA foreign_keys=OFF")

    with op.batch_alter_table("tbl_professeurs") as batch_op:
        batch_op.alter_column(
            "statut",
            existing_type=sa.String(20),
            existing_server_default="Permanent",
            nullable=False,
        )

    with op.batch_alter_table("tbl_indisponibilites") as batch_op:
        batch_op.alter_column(
            "type_contrainte",
            existing_type=sa.String(15),
            nullable=False,
        )
        batch_op.create_unique_constraint(
            "uq_indisponibilite_unique",
            ["id_annee", "id_professeur", "jour", "id_creneau"],
        )
        batch_op.create_check_constraint(
            "ck_indisponibilite_jour", "jour BETWEEN 1 AND 7"
        )
        batch_op.create_check_constraint(
            "ck_indisponibilite_type",
            "type_contrainte IN ('INTERDIT', 'EVITER', 'PREFERE')",
        )

    op.execute("PRAGMA foreign_keys=ON")


def downgrade():
    op.execute("PRAGMA foreign_keys=OFF")

    with op.batch_alter_table("tbl_indisponibilites") as batch_op:
        batch_op.drop_constraint("ck_indisponibilite_type", type_="check")
        batch_op.drop_constraint("ck_indisponibilite_jour", type_="check")
        batch_op.drop_constraint("uq_indisponibilite_unique", type_="unique")
        batch_op.alter_column(
            "type_contrainte",
            existing_type=sa.String(15),
            nullable=True,
        )

    with op.batch_alter_table("tbl_professeurs") as batch_op:
        batch_op.alter_column(
            "statut",
            existing_type=sa.String(20),
            existing_server_default="Permanent",
            nullable=True,
        )

    op.execute("PRAGMA foreign_keys=ON")
