"""Ajout des champs id_niveau, semestre, avec_cm, avec_td dans Matiere

Revision ID: 3bfb3c42e6ec
Revises: 86837a9a95d7
Create Date: 2026-08-28 18:30:29.933435

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3bfb3c42e6ec'
down_revision: Union[str, Sequence[str], None] = '86837a9a95d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('tbl_matieres') as batch_op:
        batch_op.add_column(sa.Column('id_niveau', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('semestre', sa.String(length=10), nullable=True))
        batch_op.add_column(sa.Column('avec_cm', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('avec_td', sa.Boolean(), nullable=True))
        batch_op.create_foreign_key(
            'fk_matieres_id_niveau',
            'tbl_niveaux',
            ['id_niveau'],
            ['id_niveau']
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('tbl_matieres') as batch_op:
        batch_op.drop_constraint('fk_matieres_id_niveau', type_='foreignkey')
        batch_op.drop_column('avec_td')
        batch_op.drop_column('avec_cm')
        batch_op.drop_column('semestre')
        batch_op.drop_column('id_niveau')
