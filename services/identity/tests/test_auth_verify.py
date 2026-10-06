"""Section C : /auth/verify, appelé par nginx (auth_request) à chaque requête /api/* (liste du 4 octobre)."""

from __future__ import annotations

import time
from collections.abc import Iterator
from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, event, func, select, update
from sqlalchemy.orm import Session, sessionmaker

from app.models import SESSION, UTILISATEUR
from commun.identite import Identite, verifier

from .aides import CLE_HMAC, MOT_DE_PASSE, Compte, client, creer_compte, lignes

pytestmark = pytest.mark.integration


def _connecte(fabrique: sessionmaker[Session]) -> tuple[TestClient, Compte]:
    compte = creer_compte(fabrique)
    c = client(fabrique)
    c.post("/auth/connexion", json={"email": compte.email, "mot_de_passe": MOT_DE_PASSE})
    assert c.post("/auth/code", json={"code": compte.code_totp()}).status_code == 200
    return c, compte


def _session_active(fabrique: sessionmaker[Session], compte: Compte) -> dict[str, Any]:
    (session,) = lignes(fabrique, SESSION, SESSION.c.utilisateur_id == compte.id, SESSION.c.etat == "active")
    return session


def test_verify__session_valide__entetes_signes_exp_60_s(fabrique: sessionmaker[Session]) -> None:
    c, compte = _connecte(fabrique)
    r = c.get("/auth/verify")
    assert r.status_code == 200
    maintenant = int(time.time())
    assert abs(int(r.headers["X-Auth-Exp"]) - (maintenant + 60)) <= 2
    assert verifier(r.headers, [CLE_HMAC], maintenant) == Identite(
        compte.id, "associe", int(r.headers["X-Auth-Exp"])
    )


@pytest.fixture
def requetes(fabrique: sessionmaker[Session]) -> Iterator[list[str]]:
    moteur: Engine = fabrique.kw["bind"]
    emises: list[str] = []

    def noter(_cnx: object, _curseur: object, sql: str, *_: object) -> None:
        emises.append(" ".join(sql.split()))

    event.listen(moteur, "before_cursor_execute", noter)
    yield emises
    event.remove(moteur, "before_cursor_execute", noter)


def test_verify__lecture_et_prolongation_en_une_requete_update_returning(
    fabrique: sessionmaker[Session], requetes: list[str]
) -> None:
    c, _ = _connecte(fabrique)
    requetes.clear()
    assert c.get("/auth/verify").status_code == 200
    assert len(requetes) == 1
    assert requetes[0].startswith("UPDATE session s SET derniere_activite_le = now()")
    assert "RETURNING" in requetes[0]


def test_verify__prolonge_12_h_glissantes(fabrique: sessionmaker[Session]) -> None:
    c, compte = _connecte(fabrique)
    with fabrique() as s, s.begin():
        s.execute(
            update(SESSION)
            .where(SESSION.c.etat == "active")
            .values(expire_le=func.now() + timedelta(minutes=5))
        )
    assert c.get("/auth/verify").status_code == 200
    session = _session_active(fabrique, compte)
    with fabrique() as s:
        maintenant = s.execute(select(func.now())).scalar_one()
    assert abs(session["expire_le"] - (maintenant + timedelta(hours=12))) < timedelta(seconds=10)


def test_verify__ne_depasse_jamais_30_jours_apres_la_creation(fabrique: sessionmaker[Session]) -> None:
    c, compte = _connecte(fabrique)
    with fabrique() as s, s.begin():
        s.execute(
            update(SESSION)
            .where(SESSION.c.etat == "active")
            .values(cree_le=func.now() - timedelta(days=29, hours=23))
        )
    assert c.get("/auth/verify").status_code == 200
    session = _session_active(fabrique, compte)
    assert session["expire_le"] == session["cree_le"] + timedelta(days=30)


def _rendre(fabrique: sessionmaker[Session], cas: str) -> None:
    table: dict[str, dict[str, Any]] = {
        "expiree": {"expire_le": func.now() - timedelta(seconds=1)},
        "revoquee": {"revoquee_le": func.now(), "motif_revocation": "deconnexion"},
        "trente_jours": {
            "cree_le": func.now() - timedelta(days=30, seconds=1),
            "expire_le": func.now() - timedelta(seconds=1),
        },
    }
    with fabrique() as s, s.begin():
        s.execute(update(SESSION).where(SESSION.c.etat == "active").values(**table[cas]))


@pytest.mark.parametrize("cas", ["expiree", "revoquee", "trente_jours"])
def test_verify__session_expiree_revoquee_ou_trop_ancienne__401_sans_corps(
    fabrique: sessionmaker[Session], cas: str
) -> None:
    c, _ = _connecte(fabrique)
    _rendre(fabrique, cas)
    r = c.get("/auth/verify")
    assert (r.status_code, r.content) == (401, b"")
    assert "X-User-Id" not in r.headers


@pytest.mark.parametrize("cookie", [None, "inconnu", "", "x" * 43, "%C3%A9" * 10])
def test_verify__sans_cookie_ou_cookie_inconnu__401_sans_corps(
    fabrique: sessionmaker[Session], cookie: str | None
) -> None:
    c = client(fabrique)
    if cookie is not None:
        c.cookies.set("lp_session", cookie)
    r = c.get("/auth/verify")
    assert (r.status_code, r.content) == (401, b"")


def test_verify__cookie_de_pre_session__401(fabrique: sessionmaker[Session]) -> None:
    compte = creer_compte(fabrique)
    c = client(fabrique)
    c.post("/auth/connexion", json={"email": compte.email, "mot_de_passe": MOT_DE_PASSE})
    pre = c.cookies["lp_pre"]
    autre = client(fabrique)
    autre.cookies.set("lp_session", pre)
    assert autre.get("/auth/verify").status_code == 401


def test_verify__utilisateur_suspendu__401_meme_session_non_revoquee(fabrique: sessionmaker[Session]) -> None:
    c, compte = _connecte(fabrique)
    with fabrique() as s, s.begin():
        s.execute(update(UTILISATEUR).where(UTILISATEUR.c.id == compte.id).values(statut="suspendu"))
    assert _session_active(fabrique, compte)["revoquee_le"] is None
    assert c.get("/auth/verify").status_code == 401


def test_verify__role_change__en_tetes_portent_le_nouveau_role(fabrique: sessionmaker[Session]) -> None:
    c, compte = _connecte(fabrique)
    with fabrique() as s, s.begin():
        s.execute(update(UTILISATEUR).where(UTILISATEUR.c.id == compte.id).values(role="operateur"))
    assert c.get("/auth/verify").headers["X-Role"] == "operateur"
