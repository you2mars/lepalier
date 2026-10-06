"""Q7 : annuler une invitation envoyée par erreur (statut `annule`, migration 0006).

Le lien est invalidé, l'action journalisée, aucun événement publié (un invité n'a jamais été publié) ; la
personne disparaît de la liste et son adresse peut être invitée de nouveau.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlalchemy.orm import Session, sessionmaker

from app.libelles import message
from app.models import INVITATION, JOB, JOURNAL, OUTBOX, UTILISATEUR

from .aides import (
    MOT_DE_PASSE,
    Compte,
    ExpediteurMemoire,
    client,
    creer_compte,
    entetes,
    executer_jobs,
    lignes,
)

pytestmark = pytest.mark.integration

INVITATION_DURAND = {"email": "durand@essai.local", "nom_affiche": "Mme Durand", "role": "associe"}


def _gerant(fabrique: sessionmaker[Session]) -> Compte:
    return creer_compte(fabrique, role="gerant", nom_affiche="M. Martin")


def _inviter(c: TestClient, gerant: Compte, **corps: Any) -> Any:
    return c.post("/utilisateurs/inviter", json={**INVITATION_DURAND, **corps}, headers=entetes(gerant))


def _annuler(c: TestClient, gerant: Compte, cible: str | uuid.UUID) -> Any:
    return c.post(f"/utilisateurs/{cible}/annuler-invitation", headers=entetes(gerant))


def _jeton(expediteur: ExpediteurMemoire) -> str:
    trouve = re.search(r"/activation#([A-Za-z0-9_-]{43})", expediteur.envoyes[-1][1].corps)
    assert trouve is not None
    return trouve.group(1)


def test_annuler__invite__statut_annule_lien_invalide_journal_sans_evenement(
    fabrique: sessionmaker[Session],
) -> None:
    gerant = _gerant(fabrique)
    c = client(fabrique)
    cible = _inviter(c, gerant).json()["id"]
    expediteur = ExpediteurMemoire()
    executer_jobs(fabrique, expediteur)
    jeton = _jeton(expediteur)

    r = _annuler(c, gerant, cible)
    assert (r.status_code, r.content) == (204, b"")
    (u,) = lignes(fabrique, UTILISATEUR, UTILISATEUR.c.id == uuid.UUID(cible))
    assert u["statut"] == "annule"
    (lien,) = lignes(fabrique, INVITATION)
    assert lien["invalidee_le"] is not None
    debut = c.post("/auth/activation/debut", json={"jeton": jeton})
    assert (debut.status_code, debut.json()["message"]) == (410, message("invitation.lien_invalide"))
    (journal,) = lignes(fabrique, JOURNAL, JOURNAL.c.action == "utilisateur.invitation_annulee")
    assert (journal["utilisateur_id"], journal["avant"], journal["apres"]) == (
        gerant.id,
        {"statut": "invite"},
        {"statut": "annule"},
    )
    assert lignes(fabrique, OUTBOX) == []


def test_annuler__disparait_de_la_liste_et_de_la_fiche(fabrique: sessionmaker[Session]) -> None:
    gerant = _gerant(fabrique)
    c = client(fabrique)
    cible = _inviter(c, gerant).json()["id"]
    _annuler(c, gerant, cible)
    noms = [u["nom_affiche"] for u in c.get("/utilisateurs", headers=entetes(gerant)).json()["utilisateurs"]]
    assert noms == ["M. Martin"]
    assert c.get(f"/utilisateurs/{cible}", headers=entetes(gerant)).status_code == 404


def test_annuler__meme_adresse_invitee_de_nouveau(fabrique: sessionmaker[Session]) -> None:
    gerant = _gerant(fabrique)
    c = client(fabrique)
    _annuler(c, gerant, _inviter(c, gerant).json()["id"])
    r = _inviter(c, gerant, email="Durand@Essai.local", role="operateur")
    assert r.status_code == 201
    assert (r.json()["statut"], r.json()["role"]) == ("invite", "operateur")


def test_annuler__envoi_encore_en_attente__aucun_email(fabrique: sessionmaker[Session]) -> None:
    gerant = _gerant(fabrique)
    c = client(fabrique)
    _annuler(c, gerant, _inviter(c, gerant).json()["id"])
    expediteur = ExpediteurMemoire()
    executer_jobs(fabrique, expediteur)
    assert expediteur.envoyes == []
    assert lignes(fabrique, INVITATION) == []


@pytest.mark.parametrize("statut", ["actif", "suspendu"])
def test_annuler__compte_deja_active__409_message(fabrique: sessionmaker[Session], statut: str) -> None:
    gerant = _gerant(fabrique)
    cible = creer_compte(fabrique, statut=statut)
    r = _annuler(client(fabrique), gerant, cible.id)
    assert (r.status_code, r.json()["message"]) == (409, message("invitation.annulation_impossible"))
    (u,) = lignes(fabrique, UTILISATEUR, UTILISATEUR.c.id == cible.id)
    assert u["statut"] == statut


def test_annuler__inconnu_ou_deja_annule__404(fabrique: sessionmaker[Session]) -> None:
    gerant = _gerant(fabrique)
    c = client(fabrique)
    assert _annuler(c, gerant, uuid.uuid4()).status_code == 404
    cible = _inviter(c, gerant).json()["id"]
    _annuler(c, gerant, cible)
    assert _annuler(c, gerant, cible).status_code == 404


@pytest.mark.parametrize(
    ("methode", "suffixe", "corps"),
    [
        ("PATCH", "", {"role": "operateur"}),
        ("POST", "/renvoyer-invitation", None),
        ("POST", "/reinitialiser-acces", None),
    ],
)
def test_annule__aucune_autre_action__404(
    fabrique: sessionmaker[Session], methode: str, suffixe: str, corps: dict[str, str] | None
) -> None:
    gerant = _gerant(fabrique)
    c = client(fabrique)
    cible = _inviter(c, gerant).json()["id"]
    _annuler(c, gerant, cible)
    r = c.request(methode, f"/utilisateurs/{cible}{suffixe}", json=corps, headers=entetes(gerant))
    assert r.status_code == 404
    assert len(lignes(fabrique, JOB, JOB.c.type == "courriel.invitation")) == 1


def test_annule__ni_connexion_ni_mot_de_passe_oublie(fabrique: sessionmaker[Session]) -> None:
    cible = creer_compte(fabrique, email="ancien@essai.local", statut="invite")
    with fabrique() as s, s.begin():
        s.execute(update(UTILISATEUR).where(UTILISATEUR.c.id == cible.id).values(statut="annule"))
    c = client(fabrique)
    r = c.post("/auth/connexion", json={"email": "ancien@essai.local", "mot_de_passe": MOT_DE_PASSE})
    assert (r.status_code, r.json()["message"]) == (401, message("connexion.identifiants_incorrects"))
    assert c.post("/auth/reinitialisation/demande", json={"email": "ancien@essai.local"}).status_code == 202
    assert lignes(fabrique, JOB, JOB.c.type == "courriel.reinitialisation") == []


def test_annuler__dernier_gerant_invite_inutile_et_sans_effet_sur_les_gerants_actifs(
    fabrique: sessionmaker[Session],
) -> None:
    """Un invité n'est jamais compté comme gérant actif : l'annuler ne touche pas la garde du dernier."""
    gerant = _gerant(fabrique)
    c = client(fabrique)
    cible = _inviter(c, gerant, role="gerant").json()["id"]
    assert _annuler(c, gerant, cible).status_code == 204


def test_adresse_reinvitee_puis_activee__connexion_et_mot_de_passe_oublie_visent_le_bon_compte(
    fabrique: sessionmaker[Session],
) -> None:
    """Deux comptes partagent alors l'adresse : l'ancien (annulé) ne doit jamais être choisi à sa place."""
    annule = creer_compte(fabrique, email="durand@essai.local", statut="invite")
    with fabrique() as s, s.begin():
        s.execute(update(UTILISATEUR).where(UTILISATEUR.c.id == annule.id).values(statut="annule"))
    actif = creer_compte(fabrique, email="Durand@essai.local")
    c = client(fabrique)
    assert (
        c.post(
            "/auth/connexion", json={"email": "durand@essai.local", "mot_de_passe": MOT_DE_PASSE}
        ).status_code
        == 200
    )
    assert c.post("/auth/code", json={"code": actif.code_totp()}).status_code == 200
    c.post("/auth/reinitialisation/demande", json={"email": "durand@essai.local"})
    (job,) = lignes(fabrique, JOB, JOB.c.type == "courriel.reinitialisation")
    assert job["payload"] == {"utilisateur_id": str(actif.id)}
