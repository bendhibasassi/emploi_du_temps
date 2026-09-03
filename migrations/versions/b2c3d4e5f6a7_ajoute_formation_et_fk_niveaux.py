"""Ajoute la structure Formation et sa FK nullable sur Niveau.

Revision ID: b2c3d4e5f6a7
Revises: f1a2b3c4d5e6
Create Date: 2026-09-03
"""

from alembic import op
import sqlalchemy as sa


revision = "b2c3d4e5f6a7"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tbl_formations",
        sa.Column("id_formation", sa.Integer(), primary_key=True),
        sa.Column("code_formation", sa.String(length=30), nullable=False),
        sa.Column("libelle", sa.String(length=200), nullable=False),
        sa.Column("cycle", sa.String(length=20), nullable=False),
        sa.Column("actif", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("code_formation"),
        sa.UniqueConstraint("libelle"),
    )

    op.execute("PRAGMA foreign_keys=OFF")
    try:
        with op.batch_alter_table("tbl_niveaux") as batch_op:
            batch_op.add_column(sa.Column("id_formation", sa.Integer(), nullable=True))
            batch_op.create_index(
                "ix_tbl_niveaux_id_formation", ["id_formation"], unique=False
            )
            batch_op.create_foreign_key(
                "fk_tbl_niveaux_formation",
                "tbl_formations",
                ["id_formation"],
                ["id_formation"],
            )
    finally:
        op.execute("PRAGMA foreign_keys=ON")


def downgrade():
    op.execute("PRAGMA foreign_keys=OFF")
    try:
        with op.batch_alter_table("tbl_niveaux") as batch_op:
            batch_op.drop_constraint("fk_tbl_niveaux_formation", type_="foreignkey")
            batch_op.drop_index("ix_tbl_niveaux_id_formation")
            batch_op.drop_column("id_formation")
    finally:
        op.execute("PRAGMA foreign_keys=ON")

    op.drop_table("tbl_formations")
