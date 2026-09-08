"""R3L : annualise uniquement la contrainte d'unicite des sections.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
"""

from alembic import op
import sqlalchemy as sa


revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def _remplacer_unicite(ancienne, nouvelle, colonnes):
    bind = op.get_bind()
    # La table est referencee par Groupes/Affectations. SQLite exige de
    # suspendre les FK hors transaction pendant sa reconstruction batch.
    with op.get_context().autocommit_block():
        foreign_keys = bind.exec_driver_sql("PRAGMA foreign_keys").scalar()
        bind.exec_driver_sql("PRAGMA foreign_keys=OFF")
        bind.exec_driver_sql("BEGIN IMMEDIATE")
        try:
            table = sa.Table(
                "tbl_sections", sa.MetaData(), autoload_with=bind,
                resolve_fks=False,
            )
            # La reflexion SQLite peut omettre le nom de la FK inline R3J.
            for fk in table.foreign_key_constraints:
                if list(fk.column_keys) == ["id_annee"]:
                    fk.name = "fk_sections_id_annee"
            with op.batch_alter_table("tbl_sections", copy_from=table) as batch:
                batch.drop_constraint(ancienne, type_="unique")
                batch.create_unique_constraint(nouvelle, colonnes)
            if bind.exec_driver_sql("PRAGMA foreign_key_check").fetchall():
                raise RuntimeError("Violation de cle etrangere apres R3L")
            bind.exec_driver_sql("COMMIT")
        except BaseException:
            bind.exec_driver_sql("ROLLBACK")
            raise
        finally:
            bind.exec_driver_sql(
                "PRAGMA foreign_keys=ON" if foreign_keys else "PRAGMA foreign_keys=OFF"
            )


def upgrade():
    _remplacer_unicite(
        "uq_section_niveau_code", "uq_section_annee_niveau_code",
        ["id_annee", "id_niveau", "code_section"],
    )


def downgrade():
    # Echouera sans perte de donnees si des sections annuelles ont depuis
    # introduit des doublons sur l'ancienne cle (niveau, code).
    _remplacer_unicite(
        "uq_section_annee_niveau_code", "uq_section_niveau_code",
        ["id_niveau", "code_section"],
    )
