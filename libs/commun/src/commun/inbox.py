"""Inbox par consommateur (TEC-DAT-04) : un événement déjà traité est acquitté sans effet.

Le traitement et l'inscription dans `inbox` partagent la transaction ; l'accusé NATS n'est envoyé qu'après
commit. Après `MAX_LIVRAISONS` échecs, le message est mis en quarantaine (retiré du consommateur, conservé
dans le flux).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Literal, Protocol

from pydantic import ValidationError
from sqlalchemy import Column, MetaData, Table, Text, func
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID, insert
from sqlalchemy.orm import Session

from commun.enveloppe import Enveloppe

log = logging.getLogger("commun.inbox")

MAX_LIVRAISONS = 5
DELAI_RELIVRAISON_SECONDES = 30.0

Traitement = Callable[[Session, Enveloppe], None]
Issue = Literal["traite", "doublon", "reessai", "quarantaine"]


def table_inbox(metadata: MetaData) -> Table:
    return Table(
        "inbox",
        metadata,
        Column("event_id", UUID(as_uuid=True), primary_key=True),
        Column("type", Text, nullable=False),
        Column("traite_le", TIMESTAMP(timezone=True), nullable=False, server_default=func.now()),
    )


class Inbox:
    def __init__(self, table: Table) -> None:
        self.table = table

    def traiter(self, session: Session, env: Enveloppe, traitement: Traitement) -> bool:
        """Inscrit l'événement puis applique le traitement ; False (sans effet) s'il était déjà traité."""
        inscrit = session.execute(
            insert(self.table)
            .values(event_id=env.id, type=env.type)
            .on_conflict_do_nothing(index_elements=["event_id"])
            .returning(self.table.c.event_id)
        ).first()
        if inscrit is None:
            return False
        traitement(session, env)
        return True


class _Metadonnees(Protocol):
    @property
    def num_delivered(self) -> int: ...


class MessageNats(Protocol):
    @property
    def data(self) -> bytes: ...

    @property
    def metadata(self) -> _Metadonnees: ...

    async def ack(self) -> None: ...

    async def nak(self, delay: float | None = None) -> None: ...

    async def term(self) -> None: ...


def _traiter_en_transaction(
    fabrique: Callable[[], Session], inbox: Inbox, env: Enveloppe, traitement: Traitement
) -> bool:
    with fabrique() as session, session.begin():
        return inbox.traiter(session, env, traitement)


async def consommer_message(
    msg: MessageNats,
    fabrique: Callable[[], Session],
    inbox: Inbox,
    traitement: Traitement,
    max_livraisons: int = MAX_LIVRAISONS,
) -> Issue:
    try:
        env = Enveloppe.depuis_json(msg.data)
    except ValidationError:
        log.error("quarantaine : enveloppe illisible")
        await msg.term()
        return "quarantaine"
    try:
        # accès base hors de la boucle asyncio (callback NATS) : le traitement est synchrone
        nouveau = await asyncio.to_thread(_traiter_en_transaction, fabrique, inbox, env, traitement)
    except Exception:
        livraisons = msg.metadata.num_delivered
        if livraisons >= max_livraisons:
            log.exception("quarantaine après %s livraisons", livraisons, extra={"event_id": str(env.id)})
            await msg.term()
            return "quarantaine"
        log.warning("échec de traitement, relivraison prévue", exc_info=True, extra={"event_id": str(env.id)})
        await msg.nak(delay=DELAI_RELIVRAISON_SECONDES)
        return "reessai"
    await msg.ack()
    return "traite" if nouveau else "doublon"
