"""identity : alerte « compte suspendu » une fois par heure, compteur de codes des liens de réinitialisation

Révision : 0004
Précédente : 0003
Créée le : 2026-10-04

Expansion seule (aucune suppression) : deux colonnes ajoutées, droits du rôle applicatif inchangés (les droits
sur une table couvrent ses nouvelles colonnes).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("utilisateur", sa.Column("derniere_alerte_suspension_le", pg.TIMESTAMP(timezone=True)))
    op.add_column(
        "reinitialisation", sa.Column("essais_code", sa.SmallInteger, nullable=False, server_default="0")
    )
    op.create_check_constraint("ck_reinitialisation_essais_code", "reinitialisation", "essais_code >= 0")


def downgrade() -> None:
    op.drop_constraint("ck_reinitialisation_essais_code", "reinitialisation", type_="check")
    op.drop_column("reinitialisation", "essais_code")
    op.drop_column("utilisateur", "derniere_alerte_suspension_le")
