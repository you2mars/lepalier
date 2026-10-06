"""Socle du service : outbox, inbox, journal, job, planificateur, état du worker

Révision : 0001
Précédente :
Créée le : 2026-10-04

DDL écrit à la main (et non importé de `commun`) pour que l'historique ne bouge pas si `commun` évolue ;
un test vérifie qu'il correspond aux tables déclarées.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

from migrations.droits import accorder

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TZ = pg.TIMESTAMP(timezone=True)


def upgrade() -> None:
    op.create_table(
        "outbox",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("type", sa.Text, nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("producteur", sa.Text, nullable=False),
        sa.Column("cle_agregat", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("payload", pg.JSONB, nullable=False),
        sa.Column("trace_id", sa.Text, nullable=False),
        sa.Column("causation_id", pg.UUID(as_uuid=True)),
        sa.Column("cree_le", TZ, nullable=False),
        sa.Column("relaye_le", TZ),
    )
    op.create_index("ix_outbox_a_relayer", "outbox", ["id"], postgresql_where=sa.text("relaye_le IS NULL"))

    op.create_table(
        "inbox",
        sa.Column("event_id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("type", sa.Text, nullable=False),
        sa.Column("traite_le", TZ, nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "journal",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("horodatage", TZ, nullable=False, server_default=sa.func.now()),
        sa.Column("utilisateur_id", pg.UUID(as_uuid=True)),
        sa.Column("action", sa.Text, nullable=False),
        sa.Column("table_cible", sa.Text, nullable=False),
        sa.Column("enregistrement_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("avant", pg.JSONB),
        sa.Column("apres", pg.JSONB),
        sa.Column("ip", pg.INET),
        sa.Column("trace_id", sa.Text, nullable=False),
    )
    op.create_index("ix_journal_table_enregistrement", "journal", ["table_cible", "enregistrement_id"])

    op.create_table(
        "job",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("type", sa.Text, nullable=False),
        sa.Column("cle", sa.Text, nullable=False),
        sa.Column("statut", sa.Text, nullable=False, server_default="planifie"),
        sa.Column("planifie_pour", TZ, nullable=False, server_default=sa.func.now()),
        sa.Column("tentatives", sa.Integer, nullable=False, server_default="0"),
        sa.Column("verrouille_jusqu", TZ),
        sa.Column("derniere_erreur", sa.Text),
        sa.Column("payload", pg.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("cree_le", TZ, nullable=False, server_default=sa.func.now()),
        sa.Column("termine_le", TZ),
        sa.UniqueConstraint("type", "cle", name="uq_job_type_cle"),
        sa.CheckConstraint("statut IN ('planifie', 'en_cours', 'termine', 'echec')", name="ck_job_statut"),
    )
    op.create_index("ix_job_statut_planifie_pour", "job", ["statut", "planifie_pour"])

    op.create_table(
        "planificateur",
        sa.Column("nom", sa.Text, primary_key=True),
        sa.Column("dernier_tick", sa.Date, nullable=False),
    )
    op.create_table(
        "etat_worker",
        sa.Column("nom", sa.Text, primary_key=True),
        sa.Column("vu_le", TZ, nullable=False),
    )

    accorder(["outbox", "inbox", "job", "planificateur", "etat_worker"], "lecture_ecriture")
    accorder(["journal"], "ajout_seul")


def downgrade() -> None:
    for table in ("etat_worker", "planificateur", "job", "journal", "inbox", "outbox"):
        op.drop_table(table)
