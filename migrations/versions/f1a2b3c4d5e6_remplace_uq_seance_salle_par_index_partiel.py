"""Remplace la contrainte de salle par un index partiel pour les seances actives.

Revision ID: f1a2b3c4d5e6
Revises: c9556d459179
Create Date: 2026-09-02
"""

from alembic import op
import sqlalchemy as sa


revision = "f1a2b3c4d5e6"
down_revision = "c9556d459179"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("tbl_seances") as batch_op:
        batch_op.drop_constraint("uq_seance_salle", type_="unique")

    op.create_index(
        "idx_seance_slot_active",
        "tbl_seances",
        ["id_annee", "jour", "id_creneau", "id_salle", "semaine_type"],
        unique=True,
        sqlite_where=sa.text(
            "statut IS NULL OR statut != 'ANNULEE'"
        ),
    )


def downgrade():
    op.drop_index("idx_seance_slot_active", table_name="tbl_seances")

    # Peut echouer si plusieurs seances ANNULEE identiques existent.
    with op.batch_alter_table("tbl_seances") as batch_op:
        batch_op.create_unique_constraint(
            "uq_seance_salle",
            ["id_annee", "jour", "id_creneau", "id_salle", "semaine_type"],
        )
