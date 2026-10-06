"""Clés d'idempotence des écritures (TEC-API-02)

Révision : 0002
Précédente : 0001
Créée le : 2026-10-04
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

from migrations.droits import accorder

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TZ = pg.TIMESTAMP(timezone=True)


def upgrade() -> None:
    op.create_table(
        "idempotence",
        sa.Column("portee", sa.Text, primary_key=True),
        sa.Column("cle", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("route", sa.Text, nullable=False),
        sa.Column("empreinte_requete", pg.BYTEA, nullable=False),
        sa.Column("statut", sa.Text, nullable=False, server_default="en_cours"),
        sa.Column("statut_http", sa.SmallInteger),
        sa.Column("reponse", pg.JSONB),
        sa.Column("cree_le", TZ, nullable=False, server_default=sa.func.now()),
        sa.Column("expire_le", TZ, nullable=False),
        sa.CheckConstraint("statut IN ('en_cours', 'terminee')", name="ck_idempotence_statut"),
        sa.CheckConstraint("statut = 'en_cours' OR statut_http IS NOT NULL", name="ck_idempotence_reponse"),
        sa.CheckConstraint("octet_length(empreinte_requete) = 32", name="ck_idempotence_empreinte"),
    )
    op.create_index("ix_idempotence_expire_le", "idempotence", ["expire_le"])
    # purgée après 24 h par le worker : DELETE nécessaire
    accorder(["idempotence"], "lecture_ecriture")


def downgrade() -> None:
    op.drop_table("idempotence")
