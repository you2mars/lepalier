from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass, field
from typing import Any

import nats
import pytest
from nats.js import JetStreamContext
from sqlalchemy import Engine, event, func, insert, select, update
from sqlalchemy.orm import Session, sessionmaker
from testcontainers.core.container import DockerContainer
from testcontainers.core.wait_strategies import LogMessageWaitStrategy

from commun.enveloppe import Enveloppe, nouvelle_enveloppe
from commun.ids import uuid7
from commun.inbox import Inbox, consommer_message
from commun.outbox import Outbox, PublieurJetStream, assurer_flux, nom_flux

from .conftest import EFFET, INBOX, OUTBOX

pytestmark = pytest.mark.integration

OUTBOX_SVC = Outbox(OUTBOX)
INBOX_SVC = Inbox(INBOX)


def _env(n: int = 0) -> Enveloppe:
    return nouvelle_enveloppe(
        type="utilisateur.cree", version=1, producer="identity", aggregate_id=uuid7(), payload={"n": n}
    )


def _compter(fabrique: sessionmaker[Session], table: Any, *conditions: Any) -> int:
    with fabrique() as s:
        return int(s.scalar(select(func.count()).select_from(table).where(*conditions)) or 0)


@dataclass
class PublieurFactice:
    echec_au_appel: int | None = None
    publies: list[tuple[str, bytes, str]] = field(default_factory=list)
    appels: int = 0

    async def publier(self, sujet: str, donnees: bytes, id_message: str) -> None:
        self.appels += 1
        if self.appels == self.echec_au_appel:
            raise ConnectionError("NATS indisponible")
        self.publies.append((sujet, donnees, id_message))


def _boucle_active() -> bool:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return False
    return True


@pytest.fixture
def requetes_sur_la_boucle(moteur: Engine) -> Iterator[list[bool]]:
    """Pour chaque requête SQL exécutée : True si elle l'a été depuis la boucle asyncio (à proscrire)."""
    constats: list[bool] = []

    def noter(*_: Any) -> None:
        constats.append(_boucle_active())

    event.listen(moteur, "before_cursor_execute", noter)
    yield constats
    event.remove(moteur, "before_cursor_execute", noter)


@dataclass
class PublieurAnnule:
    async def publier(self, sujet: str, donnees: bytes, id_message: str) -> None:
        raise asyncio.CancelledError


# --- outbox ---------------------------------------------------------------------------------------


def test_ajouter__transaction_annulee__ni_donnee_ni_evenement(fabrique: sessionmaker[Session]) -> None:
    with pytest.raises(RuntimeError), fabrique() as s, s.begin():
        s.execute(insert(EFFET).values(id=uuid7(), valeur="x"))
        OUTBOX_SVC.ajouter(s, _env())
        raise RuntimeError("échec après écriture")
    assert _compter(fabrique, EFFET) == 0
    assert _compter(fabrique, OUTBOX) == 0


def test_ajouter__transaction_validee__donnee_et_evenement(fabrique: sessionmaker[Session]) -> None:
    with fabrique() as s, s.begin():
        s.execute(insert(EFFET).values(id=uuid7(), valeur="x"))
        OUTBOX_SVC.ajouter(s, _env())
    assert _compter(fabrique, EFFET) == 1
    assert _compter(fabrique, OUTBOX, OUTBOX.c.relaye_le.is_(None)) == 1


async def test_relayer__ordre_des_id_identifiant_de_message_et_marquage(
    fabrique: sessionmaker[Session],
) -> None:
    envs = [_env(i) for i in range(5)]
    with fabrique() as s, s.begin():
        for env in reversed(envs):
            OUTBOX_SVC.ajouter(s, env)
    publieur = PublieurFactice()
    assert await OUTBOX_SVC.relayer(fabrique, publieur) == 5
    assert [p[2] for p in publieur.publies] == [str(e.id) for e in envs]
    assert [Enveloppe.depuis_json(p[1]) for p in publieur.publies] == envs
    assert {p[0] for p in publieur.publies} == {"evt.identity.utilisateur.cree.v1"}
    assert _compter(fabrique, OUTBOX, OUTBOX.c.relaye_le.is_(None)) == 0
    assert await OUTBOX_SVC.relayer(fabrique, publieur) == 0


async def test_relayer__acces_base_hors_de_la_boucle_asyncio(
    fabrique: sessionmaker[Session], requetes_sur_la_boucle: list[bool]
) -> None:
    with fabrique() as s, s.begin():
        OUTBOX_SVC.ajouter(s, _env())
    requetes_sur_la_boucle.clear()
    assert await OUTBOX_SVC.relayer(fabrique, PublieurFactice()) == 1
    assert requetes_sur_la_boucle
    assert not any(requetes_sur_la_boucle)


async def test_relayer__arret_du_worker_pendant_la_publication__rien_n_est_marque(
    fabrique: sessionmaker[Session],
) -> None:
    with fabrique() as s, s.begin():
        OUTBOX_SVC.ajouter(s, _env())
    with pytest.raises(asyncio.CancelledError):
        await OUTBOX_SVC.relayer(fabrique, PublieurAnnule())
    assert _compter(fabrique, OUTBOX, OUTBOX.c.relaye_le.is_(None)) == 1


async def test_relayer__limite_par_lot(fabrique: sessionmaker[Session]) -> None:
    with fabrique() as s, s.begin():
        for i in range(3):
            OUTBOX_SVC.ajouter(s, _env(i))
    assert await OUTBOX_SVC.relayer(fabrique, PublieurFactice(), limite=2) == 2
    assert _compter(fabrique, OUTBOX, OUTBOX.c.relaye_le.is_(None)) == 1


async def test_relayer__echec_de_publication__deja_publies_marques_reste_repris_dans_l_ordre(
    fabrique: sessionmaker[Session],
) -> None:
    envs = [_env(i) for i in range(5)]
    with fabrique() as s, s.begin():
        for env in envs:
            OUTBOX_SVC.ajouter(s, env)
    assert await OUTBOX_SVC.relayer(fabrique, PublieurFactice(echec_au_appel=3)) == 2
    assert _compter(fabrique, OUTBOX, OUTBOX.c.relaye_le.is_(None)) == 3
    reprise = PublieurFactice()
    assert await OUTBOX_SVC.relayer(fabrique, reprise) == 3
    assert [p[2] for p in reprise.publies] == [str(e.id) for e in envs[2:]]


# --- inbox ----------------------------------------------------------------------------------------


def _effet(session: Session, env: Enveloppe) -> None:
    session.execute(insert(EFFET).values(id=env.id, valeur=str(env.payload["n"])))


def test_traiter__deux_livraisons__un_seul_effet(fabrique: sessionmaker[Session]) -> None:
    env = _env()
    resultats = []
    for _ in range(2):
        with fabrique() as s, s.begin():
            resultats.append(INBOX_SVC.traiter(s, env, _effet))
    assert resultats == [True, False]
    assert _compter(fabrique, EFFET) == 1


def test_traiter__traitement_en_echec__rien_n_est_retenu(fabrique: sessionmaker[Session]) -> None:
    env = _env()

    def echoue(session: Session, env: Enveloppe) -> None:
        _effet(session, env)
        raise ValueError("donnée manquante")

    with pytest.raises(ValueError), fabrique() as s, s.begin():
        INBOX_SVC.traiter(s, env, echoue)
    assert _compter(fabrique, INBOX) == 0
    with fabrique() as s, s.begin():
        assert INBOX_SVC.traiter(s, env, _effet) is True
    assert _compter(fabrique, EFFET) == 1


@dataclass
class _Meta:
    num_delivered: int


@dataclass
class MessageFactice:
    data: bytes
    livraisons: int = 1
    actions: list[str] = field(default_factory=list)

    @property
    def metadata(self) -> _Meta:
        return _Meta(self.livraisons)

    async def ack(self) -> None:
        self.actions.append("ack")

    async def nak(self, delay: float | None = None) -> None:
        self.actions.append("nak")

    async def term(self) -> None:
        self.actions.append("term")


def _echoue(session: Session, env: Enveloppe) -> None:
    raise ValueError("donnée manquante")


async def test_consommer__succes_puis_doublon(fabrique: sessionmaker[Session]) -> None:
    env = _env()
    premier, second = MessageFactice(env.en_json()), MessageFactice(env.en_json(), livraisons=2)
    assert await consommer_message(premier, fabrique, INBOX_SVC, _effet) == "traite"
    assert await consommer_message(second, fabrique, INBOX_SVC, _effet) == "doublon"
    assert premier.actions == ["ack"]
    assert second.actions == ["ack"]
    assert _compter(fabrique, EFFET) == 1


async def test_consommer__traitement_et_acces_base_hors_de_la_boucle_asyncio(
    fabrique: sessionmaker[Session], requetes_sur_la_boucle: list[bool]
) -> None:
    def verifie_hors_boucle(session: Session, env: Enveloppe) -> None:
        assert not _boucle_active()
        _effet(session, env)

    msg = MessageFactice(_env().en_json())
    assert await consommer_message(msg, fabrique, INBOX_SVC, verifie_hors_boucle) == "traite"
    assert requetes_sur_la_boucle
    assert not any(requetes_sur_la_boucle)


async def test_consommer__echec__relivraison_demandee(fabrique: sessionmaker[Session]) -> None:
    msg = MessageFactice(_env().en_json(), livraisons=4)
    assert await consommer_message(msg, fabrique, INBOX_SVC, _echoue) == "reessai"
    assert msg.actions == ["nak"]


async def test_consommer__echec_a_la_cinquieme_livraison__quarantaine(
    fabrique: sessionmaker[Session],
) -> None:
    msg = MessageFactice(_env().en_json(), livraisons=5)
    assert await consommer_message(msg, fabrique, INBOX_SVC, _echoue) == "quarantaine"
    assert msg.actions == ["term"]
    assert _compter(fabrique, INBOX) == 0


async def test_consommer__message_illisible__quarantaine_immediate(fabrique: sessionmaker[Session]) -> None:
    msg = MessageFactice(b'{"type": "pas une enveloppe"}')
    assert await consommer_message(msg, fabrique, INBOX_SVC, _effet) == "quarantaine"
    assert msg.actions == ["term"]


# --- NATS JetStream réel ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def url_nats() -> Iterator[str]:
    conteneur = (
        DockerContainer("nats:2-alpine")
        .with_command("-js")
        .with_exposed_ports(4222)
        .waiting_for(LogMessageWaitStrategy("Server is ready"))
    )
    with conteneur:
        yield f"nats://{conteneur.get_container_host_ip()}:{conteneur.get_exposed_port(4222)}"


@pytest.fixture
async def js(url_nats: str) -> AsyncIterator[JetStreamContext]:
    client = await nats.connect(url_nats)
    contexte = client.jetstream()
    try:
        await contexte.delete_stream(nom_flux("identity"))
    except nats.js.errors.NotFoundError:
        pass
    await assurer_flux(contexte, "identity")
    yield contexte
    await client.close()


async def test_assurer_flux__idempotent_et_retention_illimitee(js: JetStreamContext) -> None:
    await assurer_flux(js, "identity")
    info = await js.stream_info(nom_flux("identity"))
    assert info.config.subjects == ["evt.identity.>"]
    assert info.config.max_age in (0, None)
    assert info.config.max_msgs in (-1, None)


async def test_relayer__crash_entre_publication_et_commit__pas_de_doublon_dans_le_flux(
    fabrique: sessionmaker[Session], js: JetStreamContext
) -> None:
    env = _env()
    with fabrique() as s, s.begin():
        OUTBOX_SVC.ajouter(s, env)
    publieur = PublieurJetStream(js)
    assert await OUTBOX_SVC.relayer(fabrique, publieur) == 1
    # crash simulé : la publication a eu lieu mais le marquage est perdu
    with fabrique() as s, s.begin():
        s.execute(update(OUTBOX).values(relaye_le=None))
    assert await OUTBOX_SVC.relayer(fabrique, publieur) == 1
    info = await js.stream_info(nom_flux("identity"))
    assert info.state.messages == 1
    msg = await js.get_msg(nom_flux("identity"), seq=1)
    assert msg.subject == "evt.identity.utilisateur.cree.v1"
    assert msg.headers is not None
    assert msg.headers["Nats-Msg-Id"] == str(env.id)
    assert msg.data is not None
    assert Enveloppe.depuis_json(msg.data) == env
