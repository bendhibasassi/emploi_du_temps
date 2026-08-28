"""Ajout de tbl_groupes et id_groupe dans affectations

Revision ID: 86837a9a95d7
Revises:
Create Date: 2026-08-28 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '86837a9a95d7'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # 1. Créer la table tbl_groupes
    op.create_table(
        'tbl_groupes',
        sa.Column('id_groupe', sa.Integer(), nullable=False),
        sa.Column('id_section', sa.Integer(), nullable=False),
        sa.Column('code_groupe', sa.String(length=20), nullable=False),
        sa.Column('nom_groupe', sa.String(length=100), nullable=False),
        sa.Column('effectif', sa.Integer(), nullable=True),
        sa.Column('actif', sa.Boolean(), server_default='1', nullable=True),
        sa.PrimaryKeyConstraint('id_groupe'),
        sa.ForeignKeyConstraint(
            ['id_section'],
            ['tbl_sections.id_section'],
            name='fk_groupe_section'
        ),
        sa.UniqueConstraint(
            'id_section',
            'code_groupe',
            name='uq_section_code_groupe'
        )
    )

    # 2. Ajouter la colonne id_groupe à tbl_affectations (sans contrainte d'abord)
    with op.batch_alter_table('tbl_affectations') as batch_op:
        batch_op.add_column(sa.Column('id_groupe', sa.Integer(), nullable=True))

    # 3. Ajouter la clé étrangère en mode batch
    with op.batch_alter_table('tbl_affectations') as batch_op:
        batch_op.create_foreign_key(
            'fk_affectations_id_groupe',
            'tbl_groupes',
            ['id_groupe'],
            ['id_groupe']
        )


def downgrade():
    # 1. Supprimer la clé étrangère et la colonne
    with op.batch_alter_table('tbl_affectations') as batch_op:
        batch_op.drop_constraint(
            'fk_affectations_id_groupe',
            type_='foreignkey'
        )
        batch_op.drop_column('id_groupe')

    # 2. Supprimer la table tbl_groupes
    op.drop_table('tbl_groupes')
