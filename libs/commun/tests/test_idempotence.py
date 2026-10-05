"""Clés d'idempotence des écritures (TEC-API-02) : réservation, réponse rejouée, conflits, libération."""

from __future__ import annotations

import asyncio
import uuid
from datetime import timedelta
from typing import Any

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from sqlalchemy import func, insert, select, update
from sqlalchemy.orm import Session, sessionmaker

from commun.idempotence import (
    IdempotenceMiddleware,
    MessagesIdempotence,
    _lire_corps,
    _relire,
    empreinte_requete,
)
from commun.identite import Identite

from .conftest import EFFET, IDEMPOTENCE

pytestmark = pytest.mark.integration

MESSAGES = MessagesIdempotence(
    cle_manquante="Clé manquante.", requete_en_cours="Déjà en cours.", cle_reutilisee="Clé réutilisée."
)
PERSONNE = uuid.UUID("0192f3a4-5b6c-7d8e-9f01-234567890c00")


class Panne(Exception):
    pass


def _app(fabrique: sessionmaker[Session]) -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        IdempotenceMiddleware, fabrique=fabrique, table=IDEMPOTENCE, prefixes=("/lots",), messages=MESSAGES
    )

    @app.middleware("http")
    async def identite(request: Request, suivant: Any) -> Any:
        # tient lieu d'IdentiteMiddleware, qui est plus externe dans un service
        uid = request.headers.get("x-test-utilisateur")
        if uid:
            request.scope.setdefault("state", {})["identite"] = Identite(uuid.UUID(uid), "gerant", 0)
        return await suivant(request)

    @app.post("/lots", status_code=201)
    def creer(corps: dict[str, Any]) -> dict[str, Any]:
        if corps.get("panne"):
            raise Panne
        if corps.get("indisponible"):
            from commun.erreurs import ErreurApi

            raise ErreurApi(503, "indisponible", "Indisponible.")
        if corps.get("refus"):
            from commun.erreurs import ErreurApi

            raise ErreurApi(409, "refus", "Refusé.")
        nouvel = uuid.uuid4()
        with fabrique() as s, s.begin():
            s.execute(insert(EFFET).values(id=nouvel, valeur=str(corps.get("valeur"))))
        return {"id": str(nouvel)}

    @app.delete("/lots/{lot_id}", status_code=204)
    def supprimer(lot_id: str) -> None:
        with fabrique() as s, s.begin():
            s.execute(insert(EFFET).values(id=uuid.uuid4(), valeur=f"suppression {lot_id}"))

    @app.get("/lots")
    def lire() -> dict[str, str]:
        return {"ok": "oui"}

    @app.post("/autres")
    def autre() -> dict[str, str]:
        return {"ok": "oui"}

    return app


def _client(fabrique: sessionmaker[Session]) -> TestClient:
    from commun.erreurs import installer_gestionnaires

    app = _app(fabrique)
    installer_gestionnaires(app)
    return TestClient(app, raise_server_exceptions=False)


def _entetes(cle: uuid.UUID | str, personne: uuid.UUID = PERSONNE) -> dict[str, str]:
    return {"Idempotency-Key": str(cle), "X-Test-Utilisateur": str(personne)}


def _effets(fabrique: sessionmaker[Session]) -> int:
    with fabrique() as s:
        return s.execute(select(func.count()).select_from(EFFET)).scalar_one()


def _reservations(fabrique: sessionmaker[Session]) -> list[dict[str, Any]]:
    with fabrique() as s:
        return [dict(r) for r in s.execute(select(IDEMPOTENCE)).mappings()]


@pytest.mark.parametrize("cle", [None, "", "pas-un-uuid"])
def test_ecriture_sans_cle_ou_cle_mal_formee__400_message(
    fabrique: sessionmaker[Session], cle: str | None
) -> None:
    entetes = {"X-Test-Utilisateur": str(PERSONNE)} | ({} if cle is None else {"Idempotency-Key": cle})
    r = _client(fabrique).post("/lots", json={"valeur": 1}, headers=entetes)
    assert (r.status_code, r.json()["code"], r.json()["message"]) == (
        400,
        "cle_idempotence_manquante",
        "Clé manquante.",
    )
    assert _effets(fabrique) == 0


def test_lecture_ou_route_hors_prefixes__aucune_cle_exigee_ni_stockee(
    fabrique: sessionmaker[Session],
) -> None:
    c = _client(fabrique)
    assert c.get("/lots").status_code == 200
    assert c.post("/autres").status_code == 200
    assert _reservations(fabrique) == []


def test_meme_cle_meme_corps__reponse_rejouee_sans_second_effet(fabrique: sessionmaker[Session]) -> None:
    c, cle = _client(fabrique), uuid.uuid4()
    premiere = c.post("/lots", json={"valeur": 1}, headers=_entetes(cle))
    seconde = c.post("/lots", json={"valeur": 1}, headers=_entetes(cle))
    assert (premiere.status_code, seconde.status_code) == (201, 201)
    assert seconde.json() == premiere.json()
    assert seconde.headers["Idempotent-Replayed"] == "true"
    assert "Idempotent-Replayed" not in premiere.headers
    assert _effets(fabrique) == 1
    (reservation,) = _reservations(fabrique)
    assert (reservation["statut"], reservation["statut_http"], reservation["route"]) == (
        "terminee",
        201,
        "POST /lots",
    )
    assert reservation["expire_le"] - reservation["cree_le"] == timedelta(hours=24)


def test_reponse_sans_corps__rejouee_sans_corps(fabrique: sessionmaker[Session]) -> None:
    c, cle = _client(fabrique), uuid.uuid4()
    assert c.delete("/lots/12", headers=_entetes(cle)).status_code == 204
    rejouee = c.delete("/lots/12", headers=_entetes(cle))
    assert (rejouee.status_code, rejouee.content) == (204, b"")
    assert _effets(fabrique) == 1


def test_refus_metier__conserve_et_rejoue(fabrique: sessionmaker[Session]) -> None:
    c, cle = _client(fabrique), uuid.uuid4()
    premiere = c.post("/lots", json={"refus": True}, headers=_entetes(cle))
    seconde = c.post("/lots", json={"refus": True}, headers=_entetes(cle))
    assert (premiere.status_code, seconde.status_code) == (409, 409)
    assert seconde.json()["message"] == "Refusé."


def test_meme_cle_autre_corps_ou_autre_route__422_message(fabrique: sessionmaker[Session]) -> None:
    c, cle = _client(fabrique), uuid.uuid4()
    c.post("/lots", json={"valeur": 1}, headers=_entetes(cle))
    for r in (
        c.post("/lots", json={"valeur": 2}, headers=_entetes(cle)),
        c.delete("/lots/12", headers=_entetes(cle)),
    ):
        assert (r.status_code, r.json()["code"], r.json()["message"]) == (
            422,
            "cle_reutilisee",
            "Clé réutilisée.",
        )
    assert _effets(fabrique) == 1


def test_doublon_simultane__409_requete_deja_en_cours(fabrique: sessionmaker[Session]) -> None:
    """La première requête a réservé la clé et n'a pas encore répondu."""
    cle = uuid.uuid4()
    corps = b'{"valeur":1}'
    with fabrique() as s, s.begin():
        s.execute(
            insert(IDEMPOTENCE).values(
                portee=f"utilisateur:{PERSONNE}",
                cle=cle,
                route="POST /lots",
                empreinte_requete=empreinte_requete("POST", "/lots", corps),
                expire_le=func.now() + timedelta(hours=24),
            )
        )
    r = _client(fabrique).post(
        "/lots", content=corps, headers={**_entetes(cle), "Content-Type": "application/json"}
    )
    assert (r.status_code, r.json()["code"], r.json()["message"]) == (
        409,
        "requete_en_cours",
        "Déjà en cours.",
    )
    assert _effets(fabrique) == 0


def test_traitement_en_echec__reservation_liberee(fabrique: sessionmaker[Session]) -> None:
    c, cle = _client(fabrique), uuid.uuid4()
    assert c.post("/lots", json={"valeur": 1, "panne": True}, headers=_entetes(cle)).status_code == 500
    assert _reservations(fabrique) == []
    assert c.post("/lots", json={"valeur": 1}, headers=_entetes(cle)).status_code == 201


def test_portee_par_utilisateur__meme_cle_deux_personnes_independantes(
    fabrique: sessionmaker[Session],
) -> None:
    c, cle = _client(fabrique), uuid.uuid4()
    autre = uuid.UUID("0192f3a4-5b6c-7d8e-9f01-234567890c99")
    assert c.post("/lots", json={"valeur": 1}, headers=_entetes(cle)).status_code == 201
    assert c.post("/lots", json={"valeur": 2}, headers=_entetes(cle, autre)).status_code == 201
    assert _effets(fabrique) == 2


def test_sans_identite__portee_anonyme_par_route(fabrique: sessionmaker[Session]) -> None:
    c, cle = _client(fabrique), uuid.uuid4()
    c.post("/lots", json={"valeur": 1}, headers={"Idempotency-Key": str(cle)})
    (reservation,) = _reservations(fabrique)
    assert reservation["portee"] == "anonyme:POST /lots"


def test_cle_expiree__traitee_comme_nouvelle(fabrique: sessionmaker[Session]) -> None:
    c, cle = _client(fabrique), uuid.uuid4()
    c.post("/lots", json={"valeur": 1}, headers=_entetes(cle))
    with fabrique() as s, s.begin():
        s.execute(update(IDEMPOTENCE).values(expire_le=func.now() - timedelta(seconds=1)))
    assert c.post("/lots", json={"valeur": 2}, headers=_entetes(cle)).status_code == 201
    assert _effets(fabrique) == 2


def test_reponse_5xx_sans_exception__reservation_liberee(fabrique: sessionmaker[Session]) -> None:
    c, cle = _client(fabrique), uuid.uuid4()
    assert c.post("/lots", json={"indisponible": True}, headers=_entetes(cle)).status_code == 503
    assert _reservations(fabrique) == []


def test_lecture_du_corps__deconnexion_avant_la_fin__corps_partiel() -> None:
    messages = iter([{"type": "http.request", "body": b"ab", "more_body": True}, {"type": "http.disconnect"}])

    async def recevoir() -> Any:
        return next(messages)

    assert asyncio.run(_lire_corps(recevoir)) == b"ab"


def test_relecture__corps_rendu_une_fois_puis_messages_suivants() -> None:
    async def recevoir() -> Any:
        return {"type": "http.disconnect"}

    relu = _relire(b"corps", recevoir)

    async def lire() -> Any:
        return await relu()

    assert asyncio.run(lire()) == {"type": "http.request", "body": b"corps", "more_body": False}
    assert asyncio.run(lire()) == {"type": "http.disconnect"}


def _reserver_a_la_main(
    fabrique: sessionmaker[Session], cle: uuid.UUID, corps: bytes, age: timedelta
) -> None:
    with fabrique() as s, s.begin():
        s.execute(
            insert(IDEMPOTENCE).values(
                portee=f"utilisateur:{PERSONNE}",
                cle=cle,
                route="POST /lots",
                empreinte_requete=empreinte_requete("POST", "/lots", corps),
                cree_le=func.now() - age,
                expire_le=func.now() + timedelta(hours=24) - age,
            )
        )


def test_reservation_en_cours_depuis_plus_de_2_minutes__abandonnee_reprise_avec_la_meme_cle(
    fabrique: sessionmaker[Session],
) -> None:
    cle, corps = uuid.uuid4(), b'{"valeur":1}'
    _reserver_a_la_main(fabrique, cle, corps, timedelta(minutes=2, seconds=1))
    r = _client(fabrique).post(
        "/lots", content=corps, headers={**_entetes(cle), "Content-Type": "application/json"}
    )
    assert r.status_code == 201
    assert _effets(fabrique) == 1
    (reservation,) = _reservations(fabrique)
    assert reservation["statut"] == "terminee"


def test_reservation_en_cours_depuis_moins_de_2_minutes__toujours_409(
    fabrique: sessionmaker[Session],
) -> None:
    cle, corps = uuid.uuid4(), b'{"valeur":1}'
    _reserver_a_la_main(fabrique, cle, corps, timedelta(minutes=1, seconds=50))
    r = _client(fabrique).post(
        "/lots", content=corps, headers={**_entetes(cle), "Content-Type": "application/json"}
    )
    assert r.status_code == 409


def test_reservation_reprise__l_ancienne_requete_ne_peut_plus_l_ecrire_ni_la_liberer(
    fabrique: sessionmaker[Session],
) -> None:
    """La requête d'origine, seulement lente, finit après la reprise : la réponse de la reprise reste."""
    cle, corps = uuid.uuid4(), b'{"valeur":1}'
    _reserver_a_la_main(fabrique, cle, corps, timedelta(minutes=3))
    with fabrique() as s:
        ancienne = s.execute(select(IDEMPOTENCE.c.cree_le)).scalar_one()
    c = _client(fabrique)
    premiere = c.post("/lots", content=corps, headers={**_entetes(cle), "Content-Type": "application/json"})
    portee = f"utilisateur:{PERSONNE}"
    milieu = IdempotenceMiddleware(
        _app(fabrique), fabrique=fabrique, table=IDEMPOTENCE, prefixes=("/lots",), messages=MESSAGES
    )
    milieu._terminer(portee, cle, ancienne, 500, {"perdu": True})
    milieu._liberer(portee, cle, ancienne)
    rejouee = c.post("/lots", content=corps, headers={**_entetes(cle), "Content-Type": "application/json"})
    assert (rejouee.status_code, rejouee.json()) == (201, premiere.json())
