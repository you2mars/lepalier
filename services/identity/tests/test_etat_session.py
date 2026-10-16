"""GET /auth/etat-session : pourquoi la session du détenteur du cookie n'est plus valable (Q1, R0-07).

Le front l'appelle après un 401 en cours de navigation. Seul « accès suspendu » est distingué ; un cookie
absent, inconnu, expiré, révoqué pour un autre motif (ou même valable) reçoit la même réponse que pour une
session expirée : la route n'apprend rien d'autre à qui ne détient pas la session.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, update
from sqlalchemy.orm import Session, sessionmaker

from app.libelles import message
from app.models import IDEMPOTENCE, SESSION, UTILISATEUR
from commun.identite import MESSAGE_NON_AUTHENTIFIE

from .aides import MOT_DE_PASSE, Compte, client, creer_compte, entetes, lignes

pytestmark = pytest.mark.integration

EXPIREE = {"code": "session_expiree", "message": MESSAGE_NON_AUTHENTIFIE}


def _connecte(fabrique: sessionmaker[Session], **options: str) -> tuple[TestClient, Compte]:
    compte = creer_compte(fabrique, **options)
    c = client(fabrique)
    c.post("/auth/connexion", json={"email": compte.email, "mot_de_passe": MOT_DE_PASSE})
    assert c.post("/auth/code", json={"code": compte.code_totp()}).status_code == 200
    return c, compte


def _etat(c: TestClient) -> tuple[int, dict[str, str]]:
    r = c.get("/auth/etat-session")
    return r.status_code, r.json()


def test_etat_session__acces_suspendu__message_de_suspension(fabrique: sessionmaker[Session]) -> None:
    """Suspension par un gérant (route réelle) : la session est révoquée avec le motif « suspension »."""
    gerant = creer_compte(fabrique, role="gerant", nom_affiche="M. Martin")
    c, compte = _connecte(fabrique)
    assert (
        client(fabrique)
        .patch(f"/utilisateurs/{compte.id}", json={"statut": "suspendu"}, headers=entetes(gerant))
        .status_code
        == 200
    )
    assert c.get("/auth/verify").status_code == 401
    assert _etat(c) == (200, {"code": "compte_suspendu", "message": message("connexion.compte_suspendu")})


@pytest.mark.parametrize("cookie", [None, "", "inconnu", "x" * 43])
def test_etat_session__sans_cookie_ou_cookie_inconnu__session_expiree(
    fabrique: sessionmaker[Session], cookie: str | None
) -> None:
    c = client(fabrique)
    if cookie is not None:
        c.cookies.set("lp_session", cookie)
    assert _etat(c) == (200, EXPIREE)


@pytest.mark.parametrize(
    "cas", ["expiree", "deconnexion", "rotation", "reinitialisation", "totp_reinitialise"]
)
def test_etat_session__expiree_ou_revoquee_pour_un_autre_motif__session_expiree(
    fabrique: sessionmaker[Session], cas: str
) -> None:
    c, compte = _connecte(fabrique)
    valeurs: dict[str, object] = (
        {"expire_le": func.now() - timedelta(seconds=1)}
        if cas == "expiree"
        else {"revoquee_le": func.now(), "motif_revocation": cas}
    )
    with fabrique() as s, s.begin():
        s.execute(update(SESSION).where(SESSION.c.utilisateur_id == compte.id).values(**valeurs))
    assert _etat(c) == (200, EXPIREE)


def test_etat_session__suspendu_puis_reactive__session_expiree(fabrique: sessionmaker[Session]) -> None:
    """L'ancienne session reste révoquée, mais l'accès n'est plus suspendu : il suffit de se reconnecter."""
    c, compte = _connecte(fabrique)
    with fabrique() as s, s.begin():
        s.execute(
            update(SESSION)
            .where(SESSION.c.utilisateur_id == compte.id)
            .values(revoquee_le=func.now(), motif_revocation="suspension")
        )
    assert _etat(c) == (200, EXPIREE)


def test_etat_session__session_valable__meme_reponse(fabrique: sessionmaker[Session]) -> None:
    c, _ = _connecte(fabrique)
    assert _etat(c) == (200, EXPIREE)


def test_etat_session__suspendu_sans_revocation_par_suspension__session_expiree(
    fabrique: sessionmaker[Session],
) -> None:
    """Un statut suspendu ne suffit pas : seule une session coupée par la suspension est concernée."""
    c, compte = _connecte(fabrique)
    with fabrique() as s, s.begin():
        s.execute(update(UTILISATEUR).where(UTILISATEUR.c.id == compte.id).values(statut="suspendu"))
        s.execute(
            update(SESSION)
            .where(SESSION.c.utilisateur_id == compte.id)
            .values(revoquee_le=func.now(), motif_revocation="deconnexion")
        )
    assert _etat(c) == (200, EXPIREE)


def test_etat_session__reponses_identiques_octet_pour_octet(fabrique: sessionmaker[Session]) -> None:
    inconnu = client(fabrique)
    inconnu.cookies.set("lp_session", "inconnu")
    c, _ = _connecte(fabrique)
    assert inconnu.get("/auth/etat-session").content == c.get("/auth/etat-session").content


def test_etat_session__aucune_ecriture_ni_cle_d_idempotence(fabrique: sessionmaker[Session]) -> None:
    c, compte = _connecte(fabrique)
    avant = lignes(fabrique, SESSION, SESSION.c.utilisateur_id == compte.id)
    c.get("/auth/etat-session")
    assert lignes(fabrique, SESSION, SESSION.c.utilisateur_id == compte.id) == avant
    assert lignes(fabrique, IDEMPOTENCE) == []
