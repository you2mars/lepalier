"""Section F : administration des utilisateurs par le gérant, droits, journal et événements (ADR 0006)."""

from __future__ import annotations

import base64
import json
import re
import threading
import time
import uuid
from datetime import timedelta
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator, FormatChecker
from sqlalchemy import func, select, text, update
from sqlalchemy.orm import Session, sessionmaker

from app.courriels.textes import acces_reinitialise
from app.engines import totp
from app.libelles import message
from app.models import (
    APPAREIL,
    CODE_SECOURS,
    INVITATION,
    JOB,
    JOURNAL,
    JOURNAL_SVC,
    OUTBOX,
    SESSION,
    UTILISATEUR,
)

from .aides import (
    MOT_DE_PASSE,
    ORIGINE,
    Compte,
    ExpediteurMemoire,
    application,
    client,
    creer_compte,
    entetes,
    executer_jobs,
    lignes,
)

pytestmark = pytest.mark.integration

CONTRATS = Path(__file__).resolve().parents[3] / "contracts" / "events" / "utilisateur"
ROLES = ("gerant", "associe", "operateur")


def _gerant(fabrique: sessionmaker[Session], nom: str = "M. Martin") -> Compte:
    return creer_compte(fabrique, role="gerant", nom_affiche=nom)


def _patch(c: TestClient, auteur: Compte, cible: uuid.UUID, **corps: Any) -> Any:
    return c.patch(f"/utilisateurs/{cible}", json=corps, headers=entetes(auteur))


def _reinitialiser(c: TestClient, auteur: Compte, cible: uuid.UUID) -> Any:
    return c.post(f"/utilisateurs/{cible}/reinitialiser-acces", headers=entetes(auteur))


def _refus(r: Any, statut: int, cle: str) -> None:
    assert r.status_code == statut, r.text
    assert r.json()["message"] == message(cle)


def _connecter(fabrique: sessionmaker[Session], compte: Compte, decalage: int = 0) -> TestClient:
    c = client(fabrique)
    c.post("/auth/connexion", json={"email": compte.email, "mot_de_passe": MOT_DE_PASSE})
    assert c.post("/auth/code", json={"code": compte.code_totp(decalage)}).status_code == 200
    return c


def _evenements(fabrique: sessionmaker[Session], type_: str) -> list[dict[str, Any]]:
    return lignes(fabrique, OUTBOX, OUTBOX.c.type == type_)


# --- droits (TEC-API-01, APP-USR-05) ------------------------------------------------------------------

ROUTES = [
    ("GET", "/moi"),
    ("GET", "/utilisateurs"),
    ("POST", "/utilisateurs/inviter"),
    ("POST", "/utilisateurs/{id}/renvoyer-invitation"),
    ("PATCH", "/utilisateurs/{id}"),
    ("POST", "/utilisateurs/{id}/reinitialiser-acces"),
    ("GET", "/utilisateurs/{id}"),
    ("POST", "/utilisateurs/{id}/annuler-invitation"),
]


def test_droits__toutes_les_routes_hors_auth_sont_dans_la_matrice(fabrique: sessionmaker[Session]) -> None:
    chemins = application(fabrique).openapi()["paths"]
    declarees = {
        (methode.upper(), chemin)
        for chemin, operations in chemins.items()
        if not chemin.startswith(("/auth/", "/internal/"))
        for methode in operations
    }
    assert declarees == {(m, p.replace("{id}", "{utilisateur_id}")) for m, p in ROUTES}


@pytest.mark.parametrize(("methode", "chemin"), ROUTES)
@pytest.mark.parametrize("role", [*ROLES, None])
def test_droits__matrice_role_x_route(
    fabrique: sessionmaker[Session], methode: str, chemin: str, role: str | None
) -> None:
    cible = creer_compte(fabrique, email="cible@essai.local", statut="invite")
    auteur = creer_compte(fabrique, role=role or "associe")
    corps: dict[str, Any] | None = {
        "/utilisateurs/inviter": {
            "email": "nouveau@essai.local",
            "nom_affiche": "M. Nouveau",
            "role": "associe",
        },
        "/utilisateurs/{id}": {"role": "operateur"},
    }.get(chemin)
    r = client(fabrique).request(
        methode,
        chemin.replace("{id}", str(cible.id)),
        json=corps,
        headers=entetes(auteur, role) if role else {},  # type: ignore[arg-type]
    )
    if role is None:
        assert r.status_code == 401
    elif chemin == "/moi" or role == "gerant":
        assert r.status_code < 300, r.text
    else:
        assert r.status_code == 403
        assert r.json()["message"] == "Cette action est réservée au gérant."
        (u,) = lignes(fabrique, UTILISATEUR, UTILISATEUR.c.id == cible.id)
        assert u["role"] == "associe"


@pytest.mark.parametrize("role", ROLES)
def test_droits__entetes_forges_sans_signature__401(fabrique: sessionmaker[Session], role: str) -> None:
    gerant = _gerant(fabrique)
    forges = {"X-User-Id": str(gerant.id), "X-Role": role, "X-Auth-Exp": str(int(time.time()) + 60)}
    c = client(fabrique)
    assert c.get("/utilisateurs", headers=forges).status_code == 401
    assert c.get("/moi", headers={**forges, "X-Auth-Sig": "0" * 64}).status_code == 401


# --- /moi et liste -----------------------------------------------------------------------------------


@pytest.mark.parametrize("role", ROLES)
def test_moi__nom_affiche_et_role_jamais_l_email_des_autres(
    fabrique: sessionmaker[Session], role: str
) -> None:
    autre = creer_compte(fabrique, email="autre@essai.local", nom_affiche="M. Autre")
    moi = creer_compte(fabrique, role=role)
    r = client(fabrique).get("/moi", headers=entetes(moi, role))  # type: ignore[arg-type]
    assert r.json() == {"id": str(moi.id), "email": moi.email, "nom_affiche": "Mme Durand", "role": role}
    assert autre.email not in r.text


def test_moi__compte_suspendu_entre_temps__401(fabrique: sessionmaker[Session]) -> None:
    moi = creer_compte(fabrique, statut="suspendu")
    assert client(fabrique).get("/moi", headers=entetes(moi, "associe")).status_code == 401


def test_lister__gerant__statuts_en_mots_sans_secret(fabrique: sessionmaker[Session]) -> None:
    gerant = _gerant(fabrique)
    creer_compte(fabrique, email="invite@essai.local", nom_affiche="Mme Invitée", statut="invite")
    creer_compte(fabrique, email="suspendu@essai.local", nom_affiche="M. Suspendu", statut="suspendu")
    r = client(fabrique).get("/utilisateurs", headers=entetes(gerant))
    assert r.status_code == 200
    par_nom = {u["nom_affiche"]: u for u in r.json()["utilisateurs"]}
    assert {n: (u["statut"], u["statut_libelle"]) for n, u in par_nom.items()} == {
        "M. Martin": ("actif", message("statut.actif")),
        # compte invité créé sans invitation ni envoi en attente
        "Mme Invitée": ("invite", message("statut.invitation_expiree")),
        "M. Suspendu": ("suspendu", message("statut.suspendu")),
    }
    assert set(par_nom["M. Martin"]) == {
        "id",
        "email",
        "nom_affiche",
        "role",
        "statut",
        "statut_libelle",
        "invitation_envoyee_le",
        "invitation_expire_le",
    }
    assert [u["nom_affiche"] for u in r.json()["utilisateurs"]] == ["M. Martin", "M. Suspendu", "Mme Invitée"]
    for mot in ("hache", "totp", "secret", "argon", "$argon2"):
        assert mot not in r.text


def _statut_affiche(fabrique: sessionmaker[Session], gerant: Compte, cible: uuid.UUID) -> tuple[str, str]:
    (u,) = [
        u
        for u in client(fabrique).get("/utilisateurs", headers=entetes(gerant)).json()["utilisateurs"]
        if u["id"] == str(cible)
    ]
    return u["statut"], u["statut_libelle"]


@pytest.mark.parametrize("cas", ["aucun_lien", "expire", "invalide"])
def test_lister__invite_sans_lien_valable__invitation_expiree(
    fabrique: sessionmaker[Session], cas: str
) -> None:
    gerant = _gerant(fabrique)
    r = client(fabrique).post(
        "/utilisateurs/inviter",
        json={"email": "durand@essai.local", "nom_affiche": "Mme Durand", "role": "associe"},
        headers=entetes(gerant),
    )
    cible = uuid.UUID(r.json()["id"])
    if cas != "aucun_lien":
        executer_jobs(fabrique, ExpediteurMemoire())
    with fabrique() as s, s.begin():
        if cas == "aucun_lien":
            # e-mail jamais parti : job en échec définitif, aucun lien créé
            s.execute(update(JOB).values(statut="echec"))
        else:
            champ = {"expire": "expire_le", "invalide": "invalidee_le"}[cas]
            s.execute(update(INVITATION).values({champ: func.now() - timedelta(seconds=1)}))
    assert _statut_affiche(fabrique, gerant, cible) == ("invite", message("statut.invitation_expiree"))


def test_lister__invite_lien_valable_ou_envoi_en_attente__invitation_envoyee(
    fabrique: sessionmaker[Session],
) -> None:
    """Avant le passage du job d'envoi (ou pendant une panne SMTP), l'invitation n'est pas expirée."""
    gerant = _gerant(fabrique)
    r = client(fabrique).post(
        "/utilisateurs/inviter",
        json={"email": "durand@essai.local", "nom_affiche": "Mme Durand", "role": "associe"},
        headers=entetes(gerant),
    )
    cible = uuid.UUID(r.json()["id"])
    assert _statut_affiche(fabrique, gerant, cible) == ("invite", message("statut.invite"))
    assert executer_jobs(fabrique, ExpediteurMemoire(en_panne=True)) == ["reporte"]
    assert _statut_affiche(fabrique, gerant, cible) == ("invite", message("statut.invite"))
    with fabrique() as s, s.begin():
        s.execute(update(JOB).values(planifie_pour=func.now()))
    executer_jobs(fabrique, ExpediteurMemoire())
    assert _statut_affiche(fabrique, gerant, cible) == ("invite", message("statut.invite"))


# --- rôle -------------------------------------------------------------------------------------------


def test_changer_role__publie_role_change_avec_ancien_role_et_auteur_journalise(
    fabrique: sessionmaker[Session],
) -> None:
    gerant = _gerant(fabrique)
    cible = creer_compte(fabrique)
    r = _patch(client(fabrique), gerant, cible.id, role="operateur")
    assert (r.status_code, r.json()["role"]) == (200, "operateur")
    (evt,) = _evenements(fabrique, "utilisateur.role_change")
    assert evt["payload"] == {
        "utilisateur_id": str(cible.id),
        "role": "operateur",
        "associe_id": None,
        "nom_affiche": "Mme Durand",
        "ancien_role": "associe",
        "par_utilisateur_id": str(gerant.id),
    }
    (journal,) = lignes(fabrique, JOURNAL, JOURNAL.c.action == "utilisateur.role_change")
    assert (journal["utilisateur_id"], journal["avant"], journal["apres"]) == (
        gerant.id,
        {"role": "associe"},
        {"role": "operateur"},
    )


def test_changer_role__meme_role__aucun_evenement_ni_journal(fabrique: sessionmaker[Session]) -> None:
    gerant = _gerant(fabrique)
    cible = creer_compte(fabrique)
    assert _patch(client(fabrique), gerant, cible.id, role="associe").status_code == 200
    assert lignes(fabrique, OUTBOX) == []
    assert lignes(fabrique, JOURNAL, JOURNAL.c.action == "utilisateur.role_change") == []


def test_changer_role__compte_invite__role_change_sans_evenement(fabrique: sessionmaker[Session]) -> None:
    """utilisateur.cree, publié à l'activation, portera le rôle du moment."""
    gerant = _gerant(fabrique)
    cible = creer_compte(fabrique, statut="invite")
    assert _patch(client(fabrique), gerant, cible.id, role="operateur").json()["role"] == "operateur"
    assert lignes(fabrique, OUTBOX) == []


def test_changer_role__dernier_gerant__409_message(fabrique: sessionmaker[Session]) -> None:
    gerant = _gerant(fabrique)
    _refus(_patch(client(fabrique), gerant, gerant.id, role="associe"), 409, "utilisateurs.dernier_gerant")
    (u,) = lignes(fabrique, UTILISATEUR, UTILISATEUR.c.id == gerant.id)
    assert u["role"] == "gerant"


def test_changer_role__un_autre_gerant_actif_reste__autorise(fabrique: sessionmaker[Session]) -> None:
    gerant, autre = _gerant(fabrique), _gerant(fabrique, "Mme Leroy")
    assert _patch(client(fabrique), gerant, autre.id, role="associe").status_code == 200


def test_utilisateur_inconnu__404(fabrique: sessionmaker[Session]) -> None:
    gerant = _gerant(fabrique)
    assert _patch(client(fabrique), gerant, uuid.uuid4(), role="associe").status_code == 404
    assert _reinitialiser(client(fabrique), gerant, uuid.uuid4()).status_code == 404


def test_modifier__corps_vide_ou_statut_inconnu__422(fabrique: sessionmaker[Session]) -> None:
    gerant = _gerant(fabrique)
    cible = creer_compte(fabrique)
    assert _patch(client(fabrique), gerant, cible.id).status_code == 422
    assert _patch(client(fabrique), gerant, cible.id, statut="invite").status_code == 422


# --- suspension et réactivation ---------------------------------------------------------------------


def test_suspendre__sessions_revoquees_motif_suspension_publie_suspendu(
    fabrique: sessionmaker[Session],
) -> None:
    gerant = _gerant(fabrique)
    cible = creer_compte(fabrique)
    session_cible = _connecter(fabrique, cible)
    r = _patch(client(fabrique), gerant, cible.id, statut="suspendu")
    assert (r.status_code, r.json()["statut"], r.json()["statut_libelle"]) == (
        200,
        "suspendu",
        message("statut.suspendu"),
    )
    assert session_cible.get("/auth/verify").status_code == 401
    sessions = lignes(fabrique, SESSION, SESSION.c.utilisateur_id == cible.id, SESSION.c.etat == "active")
    assert [s["motif_revocation"] for s in sessions] == ["suspension"]
    (u,) = lignes(fabrique, UTILISATEUR, UTILISATEUR.c.id == cible.id)
    assert u["suspendu_le"] is not None
    (evt,) = _evenements(fabrique, "utilisateur.suspendu")
    assert evt["payload"]["par_utilisateur_id"] == str(gerant.id)


@pytest.mark.parametrize("soi_meme", [True, False])
def test_suspendre__dernier_gerant_ou_soi_meme_dernier__409(
    fabrique: sessionmaker[Session], soi_meme: bool
) -> None:
    gerant = _gerant(fabrique)
    auteur = gerant
    if not soi_meme:
        # un gérant dont les en-têtes sont encore valables mais qui vient d'être suspendu
        auteur = _gerant(fabrique, "Mme Leroy")
        with fabrique() as s, s.begin():
            s.execute(update(UTILISATEUR).where(UTILISATEUR.c.id == auteur.id).values(statut="suspendu"))
    attendu = "utilisateurs.se_suspendre" if soi_meme else "utilisateurs.dernier_gerant"
    _refus(_patch(client(fabrique), auteur, gerant.id, statut="suspendu"), 409, attendu)
    assert lignes(fabrique, OUTBOX) == []


def test_suspendre__son_propre_acces_meme_avec_d_autres_gerants__409_message(
    fabrique: sessionmaker[Session],
) -> None:
    gerant, _ = _gerant(fabrique), _gerant(fabrique, "Mme Leroy")
    _refus(_patch(client(fabrique), gerant, gerant.id, statut="suspendu"), 409, "utilisateurs.se_suspendre")
    (u,) = lignes(fabrique, UTILISATEUR, UTILISATEUR.c.id == gerant.id)
    assert u["statut"] == "actif"


def test_changer_son_propre_role__autre_gerant_actif__autorise(fabrique: sessionmaker[Session]) -> None:
    gerant, _ = _gerant(fabrique), _gerant(fabrique, "Mme Leroy")
    assert _patch(client(fabrique), gerant, gerant.id, role="associe").json()["role"] == "associe"


def test_dernier_gerant__deux_gerants_se_retrogradent_en_meme_temps__un_seul_reussit(
    fabrique: sessionmaker[Session],
) -> None:
    """Le premier gérant rétrograde le second dans une transaction pas encore validée ; pendant ce temps, le
    second rétrograde le premier. Le verrou sur les gérants actifs fait attendre la seconde requête, qui voit
    ensuite qu'il ne reste qu'un gérant et refuse."""
    premier, second = _gerant(fabrique), _gerant(fabrique, "Mme Leroy")
    resultat: list[Any] = []
    with fabrique() as autre, autre.begin():
        autre.execute(
            select(UTILISATEUR.c.id)
            .where(UTILISATEUR.c.role == "gerant", UTILISATEUR.c.statut == "actif")
            .order_by(UTILISATEUR.c.id)
            .with_for_update()
        )
        autre.execute(update(UTILISATEUR).where(UTILISATEUR.c.id == second.id).values(role="associe"))
        fil = threading.Thread(
            target=lambda: resultat.append(_patch(client(fabrique), second, premier.id, role="associe"))
        )
        fil.start()
        limite = time.monotonic() + 5
        with fabrique() as observateur:
            while fil.is_alive() and time.monotonic() < limite:
                attente = observateur.execute(
                    text("SELECT count(*) FROM pg_stat_activity WHERE wait_event_type = 'Lock'")
                ).scalar()
                observateur.rollback()
                if attente:
                    break
                time.sleep(0.01)
    fil.join()
    _refus(resultat[0], 409, "utilisateurs.dernier_gerant")
    restants = lignes(fabrique, UTILISATEUR, UTILISATEUR.c.role == "gerant", UTILISATEUR.c.statut == "actif")
    assert [r["id"] for r in restants] == [premier.id]


def test_reactiver__publie_reactive_anciennes_sessions_toujours_revoquees(
    fabrique: sessionmaker[Session],
) -> None:
    gerant = _gerant(fabrique)
    cible = creer_compte(fabrique)
    ancienne = _connecter(fabrique, cible)
    _patch(client(fabrique), gerant, cible.id, statut="suspendu")
    r = _patch(client(fabrique), gerant, cible.id, statut="actif")
    assert (r.status_code, r.json()["statut"]) == (200, "actif")
    assert ancienne.get("/auth/verify").status_code == 401
    (evt,) = _evenements(fabrique, "utilisateur.reactive")
    assert evt["payload"]["par_utilisateur_id"] == str(gerant.id)
    (u,) = lignes(fabrique, UTILISATEUR, UTILISATEUR.c.id == cible.id)
    assert u["suspendu_le"] is None
    assert _connecter(fabrique, cible, 30).get("/auth/verify").status_code == 200


def test_suspendre_ou_reactiver__meme_statut__aucun_evenement(fabrique: sessionmaker[Session]) -> None:
    gerant = _gerant(fabrique)
    cible = creer_compte(fabrique)
    assert _patch(client(fabrique), gerant, cible.id, statut="actif").status_code == 200
    assert lignes(fabrique, OUTBOX) == []


@pytest.mark.parametrize("statut", ["suspendu", "actif"])
def test_suspendre_ou_reactiver__compte_invite__409_message(
    fabrique: sessionmaker[Session], statut: str
) -> None:
    gerant = _gerant(fabrique)
    cible = creer_compte(fabrique, statut="invite")
    _refus(_patch(client(fabrique), gerant, cible.id, statut=statut), 409, "utilisateurs.compte_non_active")


# --- réinitialisation de l'accès (décision 3) ---------------------------------------------------------


def test_reinitialiser_acces__retour_invite_mot_de_passe_et_totp_effaces(
    fabrique: sessionmaker[Session],
) -> None:
    gerant = _gerant(fabrique)
    cible = creer_compte(fabrique)
    session_cible = _connecter(fabrique, cible)
    assert _reinitialiser(client(fabrique), gerant, cible.id).status_code == 202
    (u,) = lignes(fabrique, UTILISATEUR, UTILISATEUR.c.id == cible.id)
    assert (u["statut"], u["mot_de_passe_hache"], u["totp_secret_chiffre"], u["totp_dernier_pas"]) == (
        "invite",
        None,
        None,
        None,
    )
    assert all(
        c["invalide_le"] is not None or c["utilise_le"] is not None
        for c in lignes(fabrique, CODE_SECOURS, CODE_SECOURS.c.utilisateur_id == cible.id)
    )
    sessions = lignes(fabrique, SESSION, SESSION.c.utilisateur_id == cible.id, SESSION.c.etat == "active")
    assert [s["motif_revocation"] for s in sessions] == ["totp_reinitialise"]
    assert session_cible.get("/auth/verify").status_code == 401
    assert all(
        a["revoque_le"] is not None for a in lignes(fabrique, APPAREIL, APPAREIL.c.utilisateur_id == cible.id)
    )
    (journal,) = lignes(fabrique, JOURNAL, JOURNAL.c.action == "utilisateur.acces_reinitialise")
    assert journal["utilisateur_id"] == gerant.id
    (job,) = lignes(fabrique, JOB, JOB.c.type == "courriel.acces_reinitialise")
    assert job["payload"] == {"utilisateur_id": str(cible.id), "par_utilisateur_id": str(gerant.id)}
    executer_jobs(fabrique, ExpediteurMemoire())
    (lien,) = lignes(fabrique, INVITATION, INVITATION.c.utilisateur_id == cible.id)
    assert lien["expire_le"] - lien["cree_le"] == timedelta(days=7)  # type: ignore[operator]
    assert lien["par_utilisateur_id"] == gerant.id


def test_reinitialiser_acces__email_texte_valide_mot_pour_mot(fabrique: sessionmaker[Session]) -> None:
    gerant = _gerant(fabrique)
    cible = creer_compte(fabrique)
    _reinitialiser(client(fabrique), gerant, cible.id)
    expediteur = ExpediteurMemoire()
    executer_jobs(fabrique, expediteur)
    ((destinataire, courriel),) = expediteur.envoyes
    trouve = re.search(r"/activation#([A-Za-z0-9_-]{43})", courriel.corps)
    assert trouve is not None
    assert destinataire == cible.email
    assert courriel == acces_reinitialise("Mme Durand", f"{ORIGINE}/activation#{trouve.group(1)}")


def test_reinitialiser_acces__son_propre_acces__refus_explicite(fabrique: sessionmaker[Session]) -> None:
    gerant, _ = _gerant(fabrique), _gerant(fabrique, "Mme Leroy")
    _refus(_reinitialiser(client(fabrique), gerant, gerant.id), 409, "utilisateurs.son_propre_acces")
    (u,) = lignes(fabrique, UTILISATEUR, UTILISATEUR.c.id == gerant.id)
    assert u["statut"] == "actif"


def test_reinitialiser_acces__dernier_gerant_par_un_autre_gerant__autorise(
    fabrique: sessionmaker[Session],
) -> None:
    """Le gérant visé était le seul autre gérant actif : il reste celui qui agit."""
    gerant, autre = _gerant(fabrique), _gerant(fabrique, "Mme Leroy")
    assert _reinitialiser(client(fabrique), gerant, autre.id).status_code == 202


def test_reinitialiser_acces__compte_suspendu__409_message(fabrique: sessionmaker[Session]) -> None:
    gerant = _gerant(fabrique)
    cible = creer_compte(fabrique, statut="suspendu")
    _refus(_reinitialiser(client(fabrique), gerant, cible.id), 409, "utilisateurs.acces_suspendu")
    (u,) = lignes(fabrique, UTILISATEUR, UTILISATEUR.c.id == cible.id)
    assert u["mot_de_passe_hache"] is not None


def test_reactivation_apres_reinitialisation__aucun_second_utilisateur_cree(
    fabrique: sessionmaker[Session],
) -> None:
    gerant = _gerant(fabrique)
    cible = creer_compte(fabrique)
    with fabrique() as s, s.begin():
        s.execute(update(UTILISATEUR).where(UTILISATEUR.c.id == cible.id).values(active_le=func.now()))
    _reinitialiser(client(fabrique), gerant, cible.id)
    expediteur = ExpediteurMemoire()
    executer_jobs(fabrique, expediteur)
    jeton = re.search(r"/activation#([A-Za-z0-9_-]{43})", expediteur.envoyes[0][1].corps).group(1)  # type: ignore[union-attr]
    c = client(fabrique)
    uri = c.post("/auth/activation/debut", json={"jeton": jeton}).json()["uri_otpauth"]
    brut = parse_qs(urlparse(uri).query)["secret"][0]
    secret = base64.b32decode(brut + "=" * (-len(brut) % 8))
    r = c.post(
        "/auth/activation/fin",
        json={
            "jeton": jeton,
            "mot_de_passe": "un tout nouveau mot de passe",
            "code": totp.code(secret, totp.pas_a(time.time())),
        },
    )
    assert r.status_code == 200, r.text
    assert _evenements(fabrique, "utilisateur.cree") == []
    (u,) = lignes(fabrique, UTILISATEUR, UTILISATEUR.c.id == cible.id)
    assert u["statut"] == "actif"


# --- journal, événements, origine -------------------------------------------------------------------


def test_journal__chaque_action_avec_auteur_ip_et_trace(fabrique: sessionmaker[Session]) -> None:
    gerant = _gerant(fabrique)
    cible = creer_compte(fabrique)
    c = client(fabrique, ip="10.4.4.4")
    trace = "4bf92f3577b34da6a3ce929d0e0e4736"
    en_tete = {"X-Request-Id": trace}
    for corps in ({"role": "operateur"}, {"statut": "suspendu"}, {"statut": "actif"}):
        c.patch(f"/utilisateurs/{cible.id}", json=corps, headers={**entetes(gerant), **en_tete})
    c.post(f"/utilisateurs/{cible.id}/reinitialiser-acces", headers={**entetes(gerant), **en_tete})
    actions = {j["action"]: j for j in lignes(fabrique, JOURNAL, JOURNAL.c.enregistrement_id == cible.id)}
    for action in (
        "utilisateur.role_change",
        "utilisateur.suspendu",
        "utilisateur.reactive",
        "utilisateur.acces_reinitialise",
    ):
        ligne = actions[action]
        assert (ligne["utilisateur_id"], str(ligne["ip"]), ligne["trace_id"]) == (
            gerant.id,
            "10.4.4.4",
            trace,
        )


def test_evenements__chaque_evenement_publie_conforme_au_schema(fabrique: sessionmaker[Session]) -> None:
    gerant = _gerant(fabrique)
    cible = creer_compte(fabrique, nom_affiche="Mme Durand-Leroy")
    c = client(fabrique)
    for corps in ({"role": "operateur"}, {"statut": "suspendu"}, {"statut": "actif"}):
        assert _patch(c, gerant, cible.id, **corps).status_code == 200
    evenements = lignes(fabrique, OUTBOX)
    assert sorted(str(e["type"]) for e in evenements) == [
        "utilisateur.reactive",
        "utilisateur.role_change",
        "utilisateur.suspendu",
    ]
    for evt in evenements:
        fait = str(evt["type"]).split(".")[1]
        schema = json.loads((CONTRATS / f"{fait}.v1.json").read_text())
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(evt["payload"])
        assert (evt["version"], evt["producteur"], evt["cle_agregat"]) == (1, "identity", cible.id)


def test_evenements__transaction_annulee__ni_evenement_ni_journal(
    fabrique: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    gerant = _gerant(fabrique)
    cible = creer_compte(fabrique)

    def en_panne(*_: object, **__: object) -> None:
        raise RuntimeError("panne simulée après l'écriture de l'événement")

    monkeypatch.setattr(JOURNAL_SVC, "ecrire", en_panne)
    r = TestClient(application(fabrique), base_url="https://testserver", raise_server_exceptions=False).patch(
        f"/utilisateurs/{cible.id}", json={"statut": "suspendu"}, headers=entetes(gerant)
    )
    assert r.status_code == 500
    assert lignes(fabrique, OUTBOX) == []
    (u,) = lignes(fabrique, UTILISATEUR, UTILISATEUR.c.id == cible.id)
    assert u["statut"] == "actif"
    with fabrique() as s:
        assert s.execute(select(func.count()).select_from(JOURNAL)).scalar() == 0


@pytest.mark.parametrize(
    ("methode", "chemin"),
    [r for r in ROUTES if r[0] != "GET"],
)
def test_utilisateurs__ecritures_d_une_origine_etrangere__403(
    fabrique: sessionmaker[Session], methode: str, chemin: str
) -> None:
    gerant = _gerant(fabrique)
    cible = creer_compte(fabrique, email="cible@essai.local", statut="invite")
    corps = {
        "/utilisateurs/inviter": {
            "email": "nouveau@essai.local",
            "nom_affiche": "M. Nouveau",
            "role": "associe",
        },
        "/utilisateurs/{id}": {"role": "operateur"},
    }.get(chemin)
    r = client(fabrique).request(
        methode,
        chemin.replace("{id}", str(cible.id)),
        json=corps,
        headers={**entetes(gerant), "Origin": "https://ailleurs.exemple"},
    )
    assert r.status_code == 403
    assert lignes(fabrique, JOURNAL) == []
    assert lignes(fabrique, UTILISATEUR, UTILISATEUR.c.email == "nouveau@essai.local") == []


# --- fiche d'une personne (Q6) ---------------------------------------------------------------------------


def test_fiche__gerant__meme_contenu_que_la_ligne_de_la_liste(fabrique: sessionmaker[Session]) -> None:
    gerant = _gerant(fabrique)
    cible = creer_compte(fabrique, email="cible@essai.local")
    c = client(fabrique)
    fiche = c.get(f"/utilisateurs/{cible.id}", headers=entetes(gerant))
    (ligne,) = [
        u
        for u in c.get("/utilisateurs", headers=entetes(gerant)).json()["utilisateurs"]
        if u["id"] == str(cible.id)
    ]
    assert (fiche.status_code, fiche.json()) == (200, ligne)
    assert (ligne["invitation_envoyee_le"], ligne["invitation_expire_le"]) == (None, None)


def test_fiche__invite__date_d_envoi_et_fin_de_validite_du_dernier_lien(
    fabrique: sessionmaker[Session],
) -> None:
    gerant = _gerant(fabrique)
    c = client(fabrique)
    r = c.post(
        "/utilisateurs/inviter",
        json={"email": "durand@essai.local", "nom_affiche": "Mme Durand", "role": "associe"},
        headers=entetes(gerant),
    )
    cible = r.json()["id"]
    assert c.get(f"/utilisateurs/{cible}", headers=entetes(gerant)).json()["invitation_envoyee_le"] is None
    executer_jobs(fabrique, ExpediteurMemoire())
    (lien,) = lignes(fabrique, INVITATION)
    fiche = c.get(f"/utilisateurs/{cible}", headers=entetes(gerant)).json()
    assert fiche["invitation_envoyee_le"] == lien["cree_le"].isoformat()  # type: ignore[attr-defined]
    assert fiche["invitation_expire_le"] == lien["expire_le"].isoformat()  # type: ignore[attr-defined]
    # lien expiré : les dates restent affichées, le statut devient « Invitation expirée »
    with fabrique() as s, s.begin():
        s.execute(update(INVITATION).values(expire_le=func.now() - timedelta(seconds=1)))
    fiche = c.get(f"/utilisateurs/{cible}", headers=entetes(gerant)).json()
    assert fiche["statut_libelle"] == message("statut.invitation_expiree")
    assert fiche["invitation_envoyee_le"] == lien["cree_le"].isoformat()  # type: ignore[attr-defined]


def test_fiche__inconnu__404(fabrique: sessionmaker[Session]) -> None:
    gerant = _gerant(fabrique)
    assert client(fabrique).get(f"/utilisateurs/{uuid.uuid4()}", headers=entetes(gerant)).status_code == 404
