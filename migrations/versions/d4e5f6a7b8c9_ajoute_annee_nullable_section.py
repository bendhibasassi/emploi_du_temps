"""R3J : ajoute une annee nullable aux sections, sans annualiser les donnees.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
"""

from alembic import op


revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade():
    # SQLite accepte cette FK inline sur une nouvelle colonne nullable.
    # ALTER direct preserve la table et evite toute recopie des donnees.
    op.execute(
        "ALTER TABLE tbl_sections ADD COLUMN id_annee INTEGER "
        "CONSTRAINT fk_sections_id_annee REFERENCES tbl_annees_univ (id_annee)"
    )


def downgrade():
    # SQLite >= 3.35 : supprime la colonne et sa FK inline uniquement.
    op.execute("ALTER TABLE tbl_sections DROP COLUMN id_annee")
