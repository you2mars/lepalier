"""Outbox transactionnelle et relais vers NATS JetStream (TEC-DAT-04, TEC-JOB-08).

L'événement est écrit dans `outbox` dans la même transaction que la donnée ; le worker le relaie ensuite dans
l'ordre des identifiants (UUID v7), chaque marquage validé dès la publication confirmée. L'en-tête
`Nats-Msg-Id` = id de l'événement fait dédoublonner par JetStream une republication après un crash entre la
publication et le marquage, si elle a lieu dans la fenêtre de dédoublonnage. Garantie : au moins une fois
dans le flux ; exactement une fois en effet chez le consommateur grâce à son inbox (au-delà de la fenêtre, un
doublon reste possible dans le flux).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Sequence
from datetime import timedelta
from typing import Any, Protocol
from uuid import UUID as UUID_

from nats.js import JetStreamContext
from nats.js.api import DiscardPolicy, RetentionPolicy, StorageType, StreamConfig
from nats.js.errors import NotFoundError
from sqlalchemy import Column, Index, Integer, MetaData, RowMapping, Table, Text, func, insert, select, update
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Session

from commun.enveloppe import Enveloppe, Producteur

log = logging.getLogger("commun.outbox")

# inférieure à la conservation du flux (illimitée, max_age=0), exigé par JetStream
FENETRE_DEDOUBLONNAGE = timedelta(hours=1)


def table_outbox(metadata: MetaData) -> Table:
    table = Table(
        "outbox",
        metadata,
        Column("id", UUID(as_uuid=True), primary_key=True),
        Column("type", Text, nullable=False),
        Column("version", Integer, nullable=False),
        Column("producteur", Text, nullable=False),
        Column("cle_agregat", UUID(as_uuid=True), nullable=False),
        Column("payload", JSONB, nullable=False),
        Column("trace_id", Text, nullable=False),
        Column("causation_id", UUID(as_uuid=True)),
        Column("cree_le", TIMESTAMP(timezone=True), nullable=False),
        Column("relaye_le", TIMESTAMP(timezone=True)),
    )
    # TEC-DAT-08 : index partiel des événements à relayer
    Index("ix_outbox_a_relayer", table.c.id, postgresql_where=table.c.relaye_le.is_(None))
    return table


class Publieur(Protocol):
    async def publier(self, sujet: str, donnees: bytes, id_message: str) -> None: ...


class PublieurJetStream:
    def __init__(self, js: JetStreamContext) -> None:
        self.js = js

    async def publier(self, sujet: str, donnees: bytes, id_message: str) -> None:
        await self.js.publish(sujet, donnees, headers={"Nats-Msg-Id": id_message})


def nom_flux(producteur: Producteur) -> str:
    return "EVT_" + producteur.upper().replace("-", "_")


async def assurer_flux(js: JetStreamContext, producteur: Producteur) -> None:
    """Crée le flux du producteur s'il n'existe pas : fichier, rétention illimitée (le flux sert au rejeu).

    Un flux existant garde ses messages ; sa fenêtre de dédoublonnage est portée à FENETRE_DEDOUBLONNAGE.
    """
    fenetre = FENETRE_DEDOUBLONNAGE.total_seconds()
    try:
        info = await js.stream_info(nom_flux(producteur))
    except NotFoundError:
        await js.add_stream(
            StreamConfig(
                name=nom_flux(producteur),
                subjects=[f"evt.{producteur}.>"],
                retention=RetentionPolicy.LIMITS,
                storage=StorageType.FILE,
                discard=DiscardPolicy.OLD,
                max_age=0,
                max_msgs=-1,
                max_bytes=-1,
                duplicate_window=fenetre,
            )
        )
        return
    if info.config.duplicate_window != fenetre:
        info.config.duplicate_window = fenetre
        await js.update_stream(info.config)


class Outbox:
    def __init__(self, table: Table) -> None:
        self.table = table

    def ajouter(self, session: Session, env: Enveloppe) -> None:
        """À appeler dans la transaction qui écrit la donnée (le service applicatif valide l'ensemble)."""
        session.execute(
            insert(self.table).values(
                id=env.id,
                type=env.type,
                version=env.version,
                producteur=env.producer,
                cle_agregat=env.aggregate_id,
                payload=env.payload,
                trace_id=env.trace_id,
                causation_id=env.causation_id,
                cree_le=env.occurred_at,
            )
        )

    async def relayer(self, fabrique: Callable[[], Session], publieur: Publieur, limite: int = 100) -> int:
        """Publie au plus `limite` événements non relayés, dans l'ordre ; s'arrête au premier échec.

        Chaque événement a sa transaction : verrou, publication, marquage, validation. Un arrêt du worker ne
        fait donc republier que l'événement en cours. Retourne le nombre d'événements publiés et marqués.
        """
        publies = 0
        while publies < limite and await self._relayer_un(fabrique, publieur):
            publies += 1
        return publies

    async def _relayer_un(self, fabrique: Callable[[], Session], publieur: Publieur) -> bool:
        """Les accès base passent par `asyncio.to_thread` pour ne pas bloquer la boucle du worker ; la session
        n'est utilisée que par un fil à la fois."""
        session = await asyncio.to_thread(fabrique)
        try:
            lignes = await asyncio.to_thread(self._a_relayer, session, 1)
            if not lignes:
                await asyncio.to_thread(session.rollback)
                return False
            env = self._enveloppe(lignes[0])
            try:
                await publieur.publier(env.sujet(), env.en_json(), str(env.id))
            except Exception:
                log.exception("relais interrompu", extra={"event_id": str(env.id)})
                await asyncio.to_thread(session.rollback)
                return False
            await asyncio.to_thread(self._marquer_relaye, session, env.id)
            await asyncio.to_thread(session.commit)
            return True
        except BaseException:
            await asyncio.to_thread(session.rollback)
            raise
        finally:
            await asyncio.to_thread(session.close)

    def _a_relayer(self, session: Session, limite: int) -> Sequence[RowMapping]:
        t = self.table
        requete = (
            select(t)
            .where(t.c.relaye_le.is_(None))
            .order_by(t.c.id)
            .limit(limite)
            .with_for_update(skip_locked=True)
        )
        return session.execute(requete).mappings().all()

    def _marquer_relaye(self, session: Session, event_id: UUID_) -> None:
        t = self.table
        session.execute(update(t).where(t.c.id == event_id).values(relaye_le=func.now()))

    @staticmethod
    def _enveloppe(ligne: Any) -> Enveloppe:
        return Enveloppe(
            id=ligne["id"],
            type=ligne["type"],
            version=ligne["version"],
            occurred_at=ligne["cree_le"],
            producer=ligne["producteur"],
            aggregate_id=ligne["cle_agregat"],
            trace_id=ligne["trace_id"],
            causation_id=ligne["causation_id"],
            payload=ligne["payload"],
        )
