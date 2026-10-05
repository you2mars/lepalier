"""Section G : clés d'idempotence sur les écritures de /utilisateurs*, jamais sur /auth/* (TEC-API-02)."""

from __future__ import annotations

import json
import uuid
from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, insert, select
from sqlalchemy.orm import Session, sessionmaker

from app.libelles import message
from app.models import IDEMPOTENCE, JOB, JOURNAL, JOURNAL_SVC, OUTBOX, UTILISATEUR
from commun.idempotence import empreinte_requete

from .aides import MOT_DE_PASSE, Compte, application, client, creer_compte, entetes, lignes

pytestmark = pytest.mark.integration

INVITATION = {"email": "durand@essai.local", "nom_affiche": "Mme Durand", "role": "associe"}


def _gerant(fabrique: sessionmaker[Session], nom: str = "M. Martin") -> Compte:
    return creer_compte(fabrique, role="gerant", nom_affiche=nom)


def _avec_cle(gerant: Compte, cle: uuid.UUID) -> dict[str, Any]:
    return {**entetes(gerant), "Idempotency-Key": str(cle)}


def _ecritures(cible: uuid.UUID) -> list[tuple[str, str, dict[str, Any] | None]]:
    return [
        ("POST", "/utilisateurs/inviter", INVITATION),
        ("POST", f"/utilisateurs/{cible}/renvoyer-invitation", None),
        ("PATCH", f"/utilisateurs/{cible}", {"role": "operateur"}),
        ("POST", f"/utilisateurs/{cible}/reinitialiser-acces", None),
    ]


@pytest.mark.parametrize("rang", range(4))
def test_utilisateurs__ecritures_sans_cle_d_idempotence__400(
    fabrique: sessionmaker[Session], rang: int
) -> None:
    gerant = _gerant(fabrique)
    cible = creer_compte(fabrique, email="cible@essai.local", statut="invite")
    methode, chemin, corps = _ecritures(cible.id)[rang]
    sans_cle = {k: v for k, v in entetes(gerant).items() if k != "Idempotency-Key"}
    r = client(fabrique).request(methode, chemin, json=corps, headers=sans_cle)
    assert (r.status_code, r.json()["message"]) == (400, message("idempotence.cle_manquante"))
    assert lignes(fabrique, JOURNAL) == []
    assert lignes(fabrique, JOB) == []


def test_idempotence__ecriture_utilisateurs_sans_cle__400_message(fabrique: sessionmaker[Session]) -> None:
    gerant = _gerant(fabrique)
    r = client(fabrique).post(
        "/utilisateurs/inviter",
        json=INVITATION,
        headers={**entetes(gerant), "Idempotency-Key": "pas-une-cle"},
    )
    assert r.status_code == 400
    assert r.json()["message"] == message("idempotence.cle_manquante")
    assert lignes(fabrique, UTILISATEUR, UTILISATEUR.c.email == INVITATION["email"]) == []


def test_idempotence__meme_cle_meme_corps__reponse_rejouee_sans_second_effet(
    fabrique: sessionmaker[Session],
) -> None:
    gerant = _gerant(fabrique)
    cible = creer_compte(fabrique)
    c, cle = client(fabrique), uuid.uuid4()
    premiere = c.patch(
        f"/utilisateurs/{cible.id}", json={"statut": "suspendu"}, headers=_avec_cle(gerant, cle)
    )
    seconde = c.patch(
        f"/utilisateurs/{cible.id}", json={"statut": "suspendu"}, headers=_avec_cle(gerant, cle)
    )
    assert (premiere.status_code, seconde.status_code) == (200, 200)
    assert seconde.json() == premiere.json()
    assert len(lignes(fabrique, OUTBOX)) == 1
    assert len(lignes(fabrique, JOURNAL, JOURNAL.c.action == "utilisateur.suspendu")) == 1


def test_idempotence__invitation_rejouee__un_seul_compte_un_seul_email(
    fabrique: sessionmaker[Session],
) -> None:
    gerant = _gerant(fabrique)
    c, cle = client(fabrique), uuid.uuid4()
    reponses = [
        c.post("/utilisateurs/inviter", json=INVITATION, headers=_avec_cle(gerant, cle)) for _ in range(2)
    ]
    assert [r.status_code for r in reponses] == [201, 201]
    assert reponses[0].json() == reponses[1].json()
    assert len(lignes(fabrique, JOB, JOB.c.type == "courriel.invitation")) == 1


def test_idempotence__meme_cle_autre_corps__422_message(fabrique: sessionmaker[Session]) -> None:
    gerant = _gerant(fabrique)
    cible = creer_compte(fabrique)
    c, cle = client(fabrique), uuid.uuid4()
    c.patch(f"/utilisateurs/{cible.id}", json={"role": "operateur"}, headers=_avec_cle(gerant, cle))
    r = c.patch(f"/utilisateurs/{cible.id}", json={"statut": "suspendu"}, headers=_avec_cle(gerant, cle))
    assert (r.status_code, r.json()["message"]) == (422, message("idempotence.cle_reutilisee"))
    (u,) = lignes(fabrique, UTILISATEUR, UTILISATEUR.c.id == cible.id)
    assert (u["role"], u["statut"]) == ("operateur", "actif")


def test_idempotence__doublon_simultane__409_requete_deja_en_cours(fabrique: sessionmaker[Session]) -> None:
    """La première requête a réservé la clé et n'a pas encore répondu."""
    gerant = _gerant(fabrique)
    cle = uuid.uuid4()
    corps = json.dumps(INVITATION).encode()
    with fabrique() as s, s.begin():
        s.execute(
            insert(IDEMPOTENCE).values(
                portee=f"utilisateur:{gerant.id}",
                cle=cle,
                route="POST /utilisateurs/inviter",
                empreinte_requete=empreinte_requete("POST", "/utilisateurs/inviter", corps),
                expire_le=func.now() + timedelta(hours=24),
            )
        )
    r = client(fabrique).post(
        "/utilisateurs/inviter",
        content=corps,
        headers={**_avec_cle(gerant, cle), "Content-Type": "application/json"},
    )
    assert (r.status_code, r.json()["message"]) == (409, message("idempotence.requete_en_cours"))
    assert lignes(fabrique, UTILISATEUR, UTILISATEUR.c.email == INVITATION["email"]) == []


def test_idempotence__traitement_en_echec__reservation_liberee(
    fabrique: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    gerant = _gerant(fabrique)
    cible = creer_compte(fabrique)
    cle = uuid.uuid4()
    ecrire = JOURNAL_SVC.ecrire

    def en_panne(*_: object, **__: object) -> None:
        raise RuntimeError("panne simulée")

    monkeypatch.setattr(JOURNAL_SVC, "ecrire", en_panne)
    c = TestClient(
        application(fabrique),
        base_url="https://testserver",
        headers={"X-Real-IP": "192.168.1.20"},
        raise_server_exceptions=False,
    )
    assert (
        c.patch(
            f"/utilisateurs/{cible.id}", json={"role": "operateur"}, headers=_avec_cle(gerant, cle)
        ).status_code
        == 500
    )
    assert lignes(fabrique, IDEMPOTENCE) == []
    monkeypatch.setattr(JOURNAL_SVC, "ecrire", ecrire)
    r = c.patch(f"/utilisateurs/{cible.id}", json={"role": "operateur"}, headers=_avec_cle(gerant, cle))
    assert r.status_code == 200, r.text
    assert r.json()["role"] == "operateur"


def test_idempotence__portee_par_utilisateur__meme_cle_deux_gerants_independants(
    fabrique: sessionmaker[Session],
) -> None:
    martin, leroy = _gerant(fabrique), _gerant(fabrique, "Mme Leroy")
    c, cle = client(fabrique), uuid.uuid4()
    assert c.post("/utilisateurs/inviter", json=INVITATION, headers=_avec_cle(martin, cle)).status_code == 201
    autre = {**INVITATION, "email": "autre@essai.local"}
    assert c.post("/utilisateurs/inviter", json=autre, headers=_avec_cle(leroy, cle)).status_code == 201
    with fabrique() as s:
        portees = set(s.execute(select(IDEMPOTENCE.c.portee)).scalars())
    assert portees == {f"utilisateur:{martin.id}", f"utilisateur:{leroy.id}"}


def test_idempotence__routes_exclues__auth_entierement(fabrique: sessionmaker[Session]) -> None:
    """Parcours /auth/* sans clé, puis avec une clé : rien n'est exigé, stocké ni rejoué."""
    compte = creer_compte(fabrique)
    c = client(fabrique)
    assert (
        c.post("/auth/connexion", json={"email": compte.email, "mot_de_passe": MOT_DE_PASSE}).status_code
        == 200
    )
    assert c.post("/auth/code", json={"code": compte.code_totp()}).status_code == 200
    assert c.post("/auth/deconnexion").status_code == 204
    cle = {"Idempotency-Key": str(uuid.uuid4())}
    for _ in range(2):
        r = c.post("/auth/connexion", json={"email": compte.email, "mot_de_passe": MOT_DE_PASSE}, headers=cle)
        assert "Idempotent-Replayed" not in r.headers
    assert c.post("/auth/reinitialisation/demande", json={"email": compte.email}).status_code == 202
    assert lignes(fabrique, IDEMPOTENCE) == []
