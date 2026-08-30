"""ajoute fk seances annee

Revision ID: c9556d459179
Revises: a91c7d2e4f60
Create Date: 2026-08-30 01:22:47.803280

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9556d459179'
down_revision: Union[str, Sequence[str], None] = 'a91c7d2e4f60'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('tbl_seances') as batch_op:
        batch_op.create_foreign_key(
            'fk_seances_id_annee',
            'tbl_annees_univ',
            ['id_annee'],
            ['id_annee'],
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('tbl_seances') as batch_op:
        batch_op.drop_constraint('fk_seances_id_annee', type_='foreignkey')
