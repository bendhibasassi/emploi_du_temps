"""Rend la capacite des salles facultative.

Revision ID: a91c7d2e4f60
Revises: e8a4b02d5c31
Create Date: 2026-08-29
"""

from alembic import op
import sqlalchemy as sa


revision = "a91c7d2e4f60"
down_revision = "e8a4b02d5c31"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("PRAGMA foreign_keys=OFF")

    with op.batch_alter_table("tbl_salles") as batch_op:
        batch_op.alter_column(
            "capacite",
            existing_type=sa.Integer(),
            nullable=True,
        )

    op.execute("PRAGMA foreign_keys=ON")


def downgrade():
    op.execute("PRAGMA foreign_keys=OFF")

    with op.batch_alter_table("tbl_salles") as batch_op:
        batch_op.alter_column(
            "capacite",
            existing_type=sa.Integer(),
            nullable=False,
        )

    op.execute("PRAGMA foreign_keys=ON")
