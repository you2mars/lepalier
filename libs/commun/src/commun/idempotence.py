"""Clés d'idempotence des écritures (TEC-API-02) : réservation (`en_cours`) puis réponse conservée 24 h.

Une clé est propre à une portée (`utilisateur:<id>`, ou `anonyme:<route>` sans session). Une même clé avec un
autre corps (ou une autre route) est refusée ; un doublon simultané trouve la réservation `en_cours`.
La réservation est validée avant le traitement, pour qu'un doublon la voie ; la réponse (2xx ou 4xx) est
conservée ensuite et rejouée telle quelle ; un traitement en échec (5xx, exception) libère la réservation,
et un nouvel essai avec la même clé est alors possible. Une réservation « en cours » depuis plus de 2 minutes
est considérée comme abandonnée (processus arrêté net) et reprise ; chaque réservation est repérée par son
heure de création, pour qu'une requête d'origine seulement lente ne puisse ni écrire ni libérer celle qui l'a
reprise. Les messages sont fournis par le service.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, Column, Index, MetaData, SmallInteger, Table, Text, func, select
from sqlalchemy.dialects.postgresql import BYTEA, JSONB, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session
from starlette.responses import Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from commun.erreurs import reponse_erreur
from commun.identite import Identite

DUREE_CONSERVATION_HEURES = 24
RESERVATION_ABANDONNEE = timedelta(minutes=2)


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


METHODES_ECRITURE = frozenset({"POST", "PUT", "PATCH", "DELETE"})
ENTETE = b"idempotency-key"


@dataclass(frozen=True)
class MessagesIdempotence:
    cle_manquante: str
    requete_en_cours: str
    cle_reutilisee: str


def empreinte_requete(methode: str, chemin: str, corps: bytes) -> bytes:
    return hashlib.sha256(b"\0".join([methode.encode(), chemin.encode(), corps])).digest()


@dataclass(frozen=True)
class _Conservee:
    statut_http: int
    reponse: Any


class IdempotenceMiddleware:
    """Exige `Idempotency-Key` (UUID) sur les écritures des chemins `prefixes` ; à placer à l'intérieur
    d'IdentiteMiddleware, dont il lit l'identité pour la portée."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        fabrique: Callable[[], Session],
        table: Table,
        prefixes: Sequence[str],
        messages: MessagesIdempotence,
    ) -> None:
        self.app = app
        self.fabrique = fabrique
        self.table = table
        self.prefixes = tuple(prefixes)
        self.messages = messages

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] != "http"
            or scope["method"] not in METHODES_ECRITURE
            or not scope["path"].startswith(self.prefixes)
        ):
            await self.app(scope, receive, send)
            return
        cle = _cle(scope)
        if cle is None:
            await reponse_erreur(scope, 400, "cle_idempotence_manquante", self.messages.cle_manquante)(
                scope, receive, send
            )
            return
        route = f"{scope['method']} {scope['path']}"
        identite = scope.get("state", {}).get("identite")
        portee = f"utilisateur:{identite.user_id}" if isinstance(identite, Identite) else f"anonyme:{route}"
        corps = await _lire_corps(receive)
        empreinte = empreinte_requete(scope["method"], scope["path"], corps)
        issue = await asyncio.to_thread(self._reserver, portee, cle, route, empreinte)
        reservee_le = issue if isinstance(issue, datetime) else None
        if issue == "reutilisee":
            await reponse_erreur(scope, 422, "cle_reutilisee", self.messages.cle_reutilisee)(
                scope, receive, send
            )
            return
        if issue == "en_cours":
            await reponse_erreur(scope, 409, "requete_en_cours", self.messages.requete_en_cours)(
                scope, receive, send
            )
            return
        if isinstance(issue, _Conservee):
            await _rejouer(issue)(scope, receive, send)
            return
        assert reservee_le is not None

        statut: list[int] = []
        morceaux: list[bytes] = []
        type_contenu: list[bytes] = []

        async def envoyer(message: Message) -> None:
            if message["type"] == "http.response.start":
                statut.append(message["status"])
                type_contenu.extend(v for n, v in message.get("headers", []) if n == b"content-type")
            elif message["type"] == "http.response.body":
                morceaux.append(message.get("body", b""))
            await send(message)

        try:
            await self.app(scope, _relire(corps, receive), envoyer)
        except BaseException:
            await asyncio.to_thread(self._liberer, portee, cle, reservee_le)
            raise
        if not statut or statut[0] >= 500:
            await asyncio.to_thread(self._liberer, portee, cle, reservee_le)
            return
        contenu = b"".join(morceaux)
        reponse = json.loads(contenu) if contenu and type_contenu[:1] == [b"application/json"] else None
        await asyncio.to_thread(self._terminer, portee, cle, reservee_le, statut[0], reponse)

    def _reserver(self, portee: str, cle: UUID, route: str, empreinte: bytes) -> datetime | str | _Conservee:
        """Heure de la réservation obtenue pour cette requête ; sinon l'issue de la requête précédente."""
        t = self.table
        with self.fabrique() as s, s.begin():
            nouvelle = pg_insert(t).values(
                portee=portee,
                cle=cle,
                route=route,
                empreinte_requete=empreinte,
                statut="en_cours",
                expire_le=func.now() + timedelta(hours=DUREE_CONSERVATION_HEURES),
            )
            reservee = s.execute(
                nouvelle.on_conflict_do_update(
                    index_elements=[t.c.portee, t.c.cle],
                    set_={
                        "route": nouvelle.excluded.route,
                        "empreinte_requete": nouvelle.excluded.empreinte_requete,
                        "statut": "en_cours",
                        "statut_http": None,
                        "reponse": None,
                        "cree_le": func.now(),
                        "expire_le": nouvelle.excluded.expire_le,
                    },
                    # clé expirée, ou réservation abandonnée : traitée comme nouvelle
                    where=(t.c.expire_le <= func.now())
                    | ((t.c.statut == "en_cours") & (t.c.cree_le <= func.now() - RESERVATION_ABANDONNEE)),
                ).returning(t.c.cree_le)
            ).first()
            if reservee is not None:
                heure: datetime = reservee[0]
                return heure
            ligne = s.execute(select(t).where(t.c.portee == portee, t.c.cle == cle)).mappings().one()
        if ligne["empreinte_requete"] != empreinte:
            return "reutilisee"
        if ligne["statut"] == "en_cours":
            return "en_cours"
        return _Conservee(ligne["statut_http"], ligne["reponse"])

    def _terminer(
        self, portee: str, cle: UUID, reservee_le: datetime, statut_http: int, reponse: Any
    ) -> None:
        t = self.table
        with self.fabrique() as s, s.begin():
            s.execute(
                t.update()
                .where(
                    t.c.portee == portee, t.c.cle == cle, t.c.cree_le == reservee_le, t.c.statut == "en_cours"
                )
                .values(statut="terminee", statut_http=statut_http, reponse=reponse)
            )

    def _liberer(self, portee: str, cle: UUID, reservee_le: datetime) -> None:
        t = self.table
        with self.fabrique() as s, s.begin():
            s.execute(
                t.delete().where(
                    t.c.portee == portee, t.c.cle == cle, t.c.cree_le == reservee_le, t.c.statut == "en_cours"
                )
            )


def _cle(scope: Scope) -> UUID | None:
    brute = next((v.decode("latin-1") for n, v in scope["headers"] if n == ENTETE), "")
    try:
        return UUID(brute)
    except ValueError:
        return None


async def _lire_corps(receive: Receive) -> bytes:
    morceaux: list[bytes] = []
    while True:
        message = await receive()
        if message["type"] != "http.request":
            break
        morceaux.append(message.get("body", b""))
        if not message.get("more_body", False):
            break
    return b"".join(morceaux)


def _relire(corps: bytes, receive: Receive) -> Receive:
    """Rend le corps déjà lu à l'application, puis laisse passer les messages suivants (déconnexion)."""
    rendu = False

    async def recevoir() -> Message:
        nonlocal rendu
        if not rendu:
            rendu = True
            return {"type": "http.request", "body": corps, "more_body": False}
        return await receive()

    return recevoir


def _rejouer(conservee: _Conservee) -> Response:
    entetes = {"Idempotent-Replayed": "true"}
    if conservee.reponse is None:
        return Response(status_code=conservee.statut_http, headers=entetes)
    return Response(
        content=json.dumps(conservee.reponse, ensure_ascii=False).encode(),
        status_code=conservee.statut_http,
        media_type="application/json",
        headers=entetes,
    )
