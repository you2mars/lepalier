"""Journal d'audit par service (APP-NF-05, APP-USR-03, TEC-SEC-10) : INSERT seul pour le rôle applicatif.

Chaque écriture métier est journalisée dans la même transaction que la donnée et l'outbox. La colonne
s'appelle `table_cible` (la spec dit « table », mot réservé en SQL).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import Column, Index, MetaData, Table, Text, func, insert
from sqlalchemy.dialects.postgresql import INET, JSONB, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Session

from commun.enveloppe import normaliser_json
from commun.ids import uuid7
from commun.trace import trace_id_courant


def table_journal(metadata: MetaData) -> Table:
    table = Table(
        "journal",
        metadata,
        Column("id", PG_UUID(as_uuid=True), primary_key=True),
        Column("horodatage", TIMESTAMP(timezone=True), nullable=False, server_default=func.now()),
        Column("utilisateur_id", PG_UUID(as_uuid=True)),
        Column("action", Text, nullable=False),
        Column("table_cible", Text, nullable=False),
        Column("enregistrement_id", PG_UUID(as_uuid=True), nullable=False),
        Column("avant", JSONB),
        Column("apres", JSONB),
        Column("ip", INET),
        Column("trace_id", Text, nullable=False),
    )
    # TEC-DAT-08
    Index("ix_journal_table_enregistrement", table.c.table_cible, table.c.enregistrement_id)
    return table


class Journal:
    def __init__(self, table: Table) -> None:
        self.table = table

    def ecrire(
        self,
        session: Session,
        *,
        action: str,
        table_cible: str,
        enregistrement_id: UUID,
        utilisateur_id: UUID | None = None,
        avant: dict[str, Any] | None = None,
        apres: dict[str, Any] | None = None,
        ip: str | None = None,
    ) -> None:
        """Ajoute une ligne ; `utilisateur_id` None = action du système (job, consommateur)."""
        session.execute(
            insert(self.table).values(
                id=uuid7(),
                utilisateur_id=utilisateur_id,
                action=action,
                table_cible=table_cible,
                enregistrement_id=enregistrement_id,
                avant=None if avant is None else normaliser_json(avant, "avant"),
                apres=None if apres is None else normaliser_json(apres, "apres"),
                ip=ip,
                trace_id=trace_id_courant(),
            )
        )
