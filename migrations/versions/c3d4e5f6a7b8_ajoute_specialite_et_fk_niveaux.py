"""Ajoute la structure Specialite et sa FK nullable sur Niveau.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-09-04
"""

from alembic import op
import sqlalchemy as sa


revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tbl_specialites",
        sa.Column("id_specialite", sa.Integer(), primary_key=True),
        sa.Column("id_formation", sa.Integer(), nullable=False),
        sa.Column("code_specialite", sa.String(length=50), nullable=False),
        sa.Column("libelle", sa.String(length=200), nullable=False),
        sa.Column("actif", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(
            ["id_formation"], ["tbl_formations.id_formation"],
            name="fk_specialite_formation",
        ),
        sa.UniqueConstraint(
            "id_formation", "code_specialite",
            name="uq_specialite_formation_code",
        ),
        sa.UniqueConstraint(
            "id_formation", "libelle",
            name="uq_specialite_formation_libelle",
        ),
    )
    op.create_index("ix_tbl_specialites_id_formation", "tbl_specialites", ["id_formation"])

    op.execute("PRAGMA foreign_keys=OFF")
    try:
        with op.batch_alter_table("tbl_niveaux") as batch_op:
            batch_op.add_column(sa.Column("id_specialite", sa.Integer(), nullable=True))
            batch_op.create_index("ix_tbl_niveaux_id_specialite", ["id_specialite"], unique=False)
            batch_op.create_foreign_key(
                "fk_tbl_niveaux_specialite",
                "tbl_specialites",
                ["id_specialite"],
                ["id_specialite"],
            )
    finally:
        op.execute("PRAGMA foreign_keys=ON")


def downgrade():
    op.execute("PRAGMA foreign_keys=OFF")
    try:
        with op.batch_alter_table("tbl_niveaux") as batch_op:
            batch_op.drop_constraint("fk_tbl_niveaux_specialite", type_="foreignkey")
            batch_op.drop_index("ix_tbl_niveaux_id_specialite")
            batch_op.drop_column("id_specialite")
    finally:
        op.execute("PRAGMA foreign_keys=ON")

    op.drop_index("ix_tbl_specialites_id_formation", table_name="tbl_specialites")
    op.drop_table("tbl_specialites")
