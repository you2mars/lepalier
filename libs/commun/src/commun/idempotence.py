"""Clés d'idempotence des écritures (TEC-API-02) : réservation (`en_cours`) puis réponse conservée 24 h.

Une clé est propre à une portée (`utilisateur:<id>`, ou `anonyme:<route>` sans session). Une même clé avec un
autre corps est refusée ; un doublon simultané trouve la réservation `en_cours`. Le traitement des requêtes
viendra avec les premières routes d'écriture ; ce module ne fournit pour l'instant que la table.
"""

from __future__ import annotations

from sqlalchemy import CheckConstraint, Column, Index, MetaData, SmallInteger, Table, Text, func
from sqlalchemy.dialects.postgresql import BYTEA, JSONB, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

DUREE_CONSERVATION_HEURES = 24


def table_idempotence(metadata: MetaData) -> Table:
    table = Table(
        "idempotence",
        metadata,
        Column("portee", Text, primary_key=True),
        Column("cle", PG_UUID(as_uuid=True), primary_key=True),
        Column("route", Text, nullable=False),
        Column("empreinte_requete", BYTEA, nullable=False),
        Column("statut", Text, nullable=False, server_default="en_cours"),
        Column("statut_http", SmallInteger),
        Column("reponse", JSONB),
        Column("cree_le", TIMESTAMP(timezone=True), nullable=False, server_default=func.now()),
        Column("expire_le", TIMESTAMP(timezone=True), nullable=False),
        CheckConstraint("statut IN ('en_cours', 'terminee')", name="ck_idempotence_statut"),
        CheckConstraint("statut = 'en_cours' OR statut_http IS NOT NULL", name="ck_idempotence_reponse"),
        CheckConstraint("octet_length(empreinte_requete) = 32", name="ck_idempotence_empreinte"),
    )
    Index("ix_idempotence_expire_le", table.c.expire_le)
    return table
