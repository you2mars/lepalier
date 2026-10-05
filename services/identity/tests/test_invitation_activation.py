"""Section D : invitation et activation (liste du 4 octobre 2026, ADR 0006)."""

from __future__ import annotations

import base64
import re
import threading
import time
import uuid
from datetime import timedelta
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, insert, select, text, update
from sqlalchemy.orm import Session, sessionmaker

from app.courriels.textes import invitation
from app.engines import codes_secours, totp
from app.engines.jetons import empreinte
from app.engines.mot_de_passe import Motif
from app.libelles import message, message_mot_de_passe
from app.models import CODE_SECOURS, INVITATION, JOB, JOURNAL, OUTBOX, SESSION, UTILISATEUR
from commun.ids import uuid7

from .aides import ORIGINE, Compte, ExpediteurMemoire, client, creer_compte, entetes, executer_jobs, lignes

pytestmark = pytest.mark.integration

EMAIL = "durand@essai.local"
MOT_DE_PASSE_NEUF = "les tilleuls fleurissent en juin"
CONTRAT_NOM = re.compile(
    r"^[^@\u0000-\u001f\u007f-\u009f\u2028-\u202e\u2066-\u2069]*"
    r"[^\s@\u0000-\u001f\u007f-\u009f\u2028-\u202e\u2066-\u2069]"
    r"[^@\u0000-\u001f\u007f-\u009f\u2028-\u202e\u2066-\u2069]*$(?!\n)"
)
NOMS_REFUSES = [
    "",
    "   ",
    "jean@exemple.fr",
    "x" * 61,
    "Mme Durand\nObjet : faux",
    "Mme\tDurand",
    "Mme\x85Durand",
    "Mme\u2028Durand",
    "Mme \u202eDurand",
    "\u2066Mme Durand",
]


def _gerant(fabrique: sessionmaker[Session]) -> Compte:
    return creer_compte(fabrique, role="gerant", nom_affiche="M. Martin")


def _inviter(c: TestClient, gerant: Compte, **corps: Any) -> Any:
    return c.post(
        "/utilisateurs/inviter",
        json={"email": EMAIL, "nom_affiche": "Mme Durand", "role": "associe", **corps},
        headers=entetes(gerant),
    )


def _jeton(expediteur: ExpediteurMemoire, rang: int = -1) -> str:
    _, courriel = expediteur.envoyes[rang]
    trouve = re.search(r"/activation#([A-Za-z0-9_-]{43})", courriel.corps)
    assert trouve is not None
    return trouve.group(1)


def _invite(fabrique: sessionmaker[Session]) -> tuple[Compte, uuid.UUID, str, ExpediteurMemoire]:
    """Gérant, utilisateur invité, jeton du lien reçu par e-mail, expéditeur."""
    gerant = _gerant(fabrique)
    r = _inviter(client(fabrique), gerant)
    assert r.status_code == 201
    expediteur = ExpediteurMemoire()
    executer_jobs(fabrique, expediteur)
    return gerant, uuid.UUID(r.json()["id"]), _jeton(expediteur), expediteur


def _secret(uri: str) -> bytes:
    brut = parse_qs(urlparse(uri).query)["secret"][0]
    return base64.b32decode(brut + "=" * (-len(brut) % 8))


def _debut(c: TestClient, jeton: str) -> Any:
    return c.post("/auth/activation/debut", json={"jeton": jeton})


def _fin(c: TestClient, jeton: str, **corps: Any) -> Any:
    if "code" not in corps:
        secret = _secret(_debut(c, jeton).json()["uri_otpauth"])
        corps["code"] = totp.code(secret, totp.pas_a(time.time()))
    return c.post(
        "/auth/activation/fin",
        json={"jeton": jeton, "mot_de_passe": MOT_DE_PASSE_NEUF, "nom_affiche": "Mme Durand", **corps},
    )


def _refus(r: Any, statut: int, cle: str) -> None:
    assert r.status_code == statut, r.text
    assert r.json()["message"] == message(cle) or any(
        champ["message"] == message(cle) for champ in r.json()["details"].get("champs", [])
    )


# --- invitation (gérant) -----------------------------------------------------------------------------


def test_inviter__gerant__utilisateur_invite_origine_invitation_job_sans_jeton(
    fabrique: sessionmaker[Session],
) -> None:
    gerant = _gerant(fabrique)
    r = _inviter(client(fabrique), gerant)
    assert r.status_code == 201
    uid = uuid.UUID(r.json()["id"])
    assert r.json() == {
        "id": str(uid),
        "email": EMAIL,
        "nom_affiche": "Mme Durand",
        "role": "associe",
        "statut": "invite",
    }
    (u,) = lignes(fabrique, UTILISATEUR, UTILISATEUR.c.id == uid)
    assert (u["statut"], u["origine"], u["invite_par"]) == ("invite", "invitation", gerant.id)
    assert (u["mot_de_passe_hache"], u["totp_secret_chiffre"]) == (None, None)
    (job,) = lignes(fabrique, JOB, JOB.c.type == "courriel.invitation")
    assert job["payload"] == {"utilisateur_id": str(uid)}
    (journal,) = lignes(fabrique, JOURNAL, JOURNAL.c.action == "utilisateur.invite")
    assert (journal["utilisateur_id"], journal["enregistrement_id"]) == (gerant.id, uid)
    assert lignes(fabrique, OUTBOX) == []
    assert lignes(fabrique, INVITATION) == []


@pytest.mark.parametrize("role", ["associe", "operateur"])
def test_inviter__non_gerant__403_rien_n_est_cree(fabrique: sessionmaker[Session], role: str) -> None:
    autre = creer_compte(fabrique, role=role)
    r = client(fabrique).post(
        "/utilisateurs/inviter",
        json={"email": EMAIL, "nom_affiche": "Mme Durand", "role": "associe"},
        headers=entetes(autre, role),  # type: ignore[arg-type]
    )
    assert r.status_code == 403
    assert lignes(fabrique, UTILISATEUR, UTILISATEUR.c.email == EMAIL) == []


@pytest.mark.parametrize("nom", NOMS_REFUSES)
def test_inviter__nom_affiche_avec_arobase_vide_61_caracteres_ou_controle__422_message(
    fabrique: sessionmaker[Session], nom: str
) -> None:
    r = _inviter(client(fabrique), _gerant(fabrique), nom_affiche=nom)
    _refus(r, 422, "nom_affiche.invalide")
    assert r.json()["details"]["champs"][0]["champ"] == "nom_affiche"
    assert lignes(fabrique, UTILISATEUR, UTILISATEUR.c.email == EMAIL) == []


def test_inviter__nom_affiche_espaces_autour__retires(fabrique: sessionmaker[Session]) -> None:
    r = _inviter(client(fabrique), _gerant(fabrique), nom_affiche="  Mme Durand  ")
    assert r.json()["nom_affiche"] == "Mme Durand"


@pytest.mark.parametrize(
    "email",
    [
        "durand",
        "durand@",
        "@essai.local",
        "du rand@essai.local",
        "a@b@c.fr",
        "durand@essai.local\n",
        "durand@essai.local\r\nBcc: autre@essai.local",
        "dur\tand@essai.local",
        "durand\x00@essai.local",
        "durand\x7f@essai.local",
        "durand\x85@essai.local",
        "durand\u202e@essai.local",
        "\u2066durand@essai.local",
        "élodie@essai.local",
        "durand@essai.l\u043ecal",
        "durand@essai.local\u00a0",
    ],
)
def test_inviter__email_mal_forme_controle_ou_non_ascii__422_message(
    fabrique: sessionmaker[Session], email: str
) -> None:
    r = _inviter(client(fabrique), _gerant(fabrique), email=email)
    _refus(r, 422, "utilisateurs.email_invalide")
    assert r.json()["details"]["champs"][0]["champ"] == "email"


def test_inviter__email_deja_utilise_sans_tenir_compte_de_la_casse__409_message(
    fabrique: sessionmaker[Session],
) -> None:
    gerant = _gerant(fabrique)
    assert _inviter(client(fabrique), gerant).status_code == 201
    r = _inviter(client(fabrique), gerant, email="  Durand@Essai.LOCAL ")
    _refus(r, 409, "utilisateurs.email_deja_utilise")
    assert r.json()["details"]["champs"][0]["champ"] == "email"
    assert len(lignes(fabrique, UTILISATEUR, func.lower(UTILISATEUR.c.email) == EMAIL)) == 1


# --- e-mail d'invitation (job) -----------------------------------------------------------------------


def test_job_invitation__genere_jeton_stocke_empreinte_envoie_meme_transaction(
    fabrique: sessionmaker[Session],
) -> None:
    gerant, uid, jeton, expediteur = _invite(fabrique)
    ((destinataire, courriel),) = expediteur.envoyes
    assert destinataire == EMAIL
    assert courriel == invitation("Mme Durand", "M. Martin", f"{ORIGINE}/activation#{jeton}")
    (lien,) = lignes(fabrique, INVITATION, INVITATION.c.utilisateur_id == uid)
    assert lien["empreinte"] == empreinte(jeton)
    assert lien["par_utilisateur_id"] == gerant.id
    assert lien["expire_le"] - lien["cree_le"] == timedelta(days=7)  # type: ignore[operator]


def test_job_invitation__aucun_jeton_dans_job_payload_ni_journal(fabrique: sessionmaker[Session]) -> None:
    _, _, jeton, _ = _invite(fabrique)
    with fabrique() as s:
        for table in (JOB, JOURNAL):
            for ligne in s.execute(select(table)).mappings():
                assert jeton not in repr(dict(ligne))


def test_job_invitation__connexion_perdue_apres_envoi__nouvel_essai_nouveau_jeton_precedent_invalide(
    fabrique: sessionmaker[Session],
) -> None:
    gerant = _gerant(fabrique)
    _inviter(client(fabrique), gerant)
    expediteur = ExpediteurMemoire(perdu_apres_envoi=True)
    assert executer_jobs(fabrique, expediteur) == ["reporte"]
    assert lignes(fabrique, INVITATION) == []
    with fabrique() as s, s.begin():
        s.execute(update(JOB).values(planifie_pour=func.now()))
    expediteur.perdu_apres_envoi = False
    assert executer_jobs(fabrique, expediteur) == ["termine"]
    perdu, recu = _jeton(expediteur, 0), _jeton(expediteur, 1)
    assert perdu != recu
    c = client(fabrique)
    _refus(_debut(c, perdu), 410, "invitation.lien_invalide")
    assert _debut(c, recu).status_code == 200


def test_renvoyer_invitation__invalide_le_lien_precedent(fabrique: sessionmaker[Session]) -> None:
    gerant, uid, ancien, expediteur = _invite(fabrique)
    r = client(fabrique).post(f"/utilisateurs/{uid}/renvoyer-invitation", headers=entetes(gerant))
    assert r.status_code == 202
    c = client(fabrique)
    _refus(_debut(c, ancien), 410, "invitation.lien_invalide")
    executer_jobs(fabrique, expediteur)
    assert _debut(c, _jeton(expediteur)).status_code == 200
    (journal,) = lignes(fabrique, JOURNAL, JOURNAL.c.action == "utilisateur.invitation_renvoyee")
    assert journal["utilisateur_id"] == gerant.id


def test_renvoyer_invitation__compte_deja_active__409_message(fabrique: sessionmaker[Session]) -> None:
    gerant = _gerant(fabrique)
    actif = creer_compte(fabrique)
    r = client(fabrique).post(f"/utilisateurs/{actif.id}/renvoyer-invitation", headers=entetes(gerant))
    _refus(r, 409, "invitation.deja_activee")
    assert lignes(fabrique, JOB, JOB.c.type == "courriel.invitation") == []


def test_renvoyer_invitation__utilisateur_inconnu__404(fabrique: sessionmaker[Session]) -> None:
    r = client(fabrique).post(
        f"/utilisateurs/{uuid.uuid4()}/renvoyer-invitation", headers=entetes(_gerant(fabrique))
    )
    assert r.status_code == 404


# --- activation : début ------------------------------------------------------------------------------


def test_activation_debut__lien_valide__uri_otpauth_secret_chiffre_version_1(
    fabrique: sessionmaker[Session],
) -> None:
    _, uid, jeton, _ = _invite(fabrique)
    r = _debut(client(fabrique), jeton)
    assert r.status_code == 200
    assert r.json()["nom_affiche"] == "Mme Durand"
    uri = r.json()["uri_otpauth"]
    assert uri.startswith("otpauth://totp/LePalier:Mme%20Durand?")
    assert EMAIL not in uri
    (u,) = lignes(fabrique, UTILISATEUR, UTILISATEUR.c.id == uid)
    chiffre = u["totp_secret_chiffre"]
    assert chiffre[0] == 1  # type: ignore[index]
    assert _secret(uri) not in chiffre  # type: ignore[operator]
    assert u["statut"] == "invite"


def test_activation_debut__deux_appels__meme_uri_otpauth(fabrique: sessionmaker[Session]) -> None:
    _, _, jeton, _ = _invite(fabrique)
    c = client(fabrique)
    assert _debut(c, jeton).json() == _debut(client(fabrique), jeton).json()


@pytest.mark.parametrize("cas", ["expire", "utilise", "invalide", "inconnu", "mal_forme"])
def test_activation_debut__lien_expire_utilise_ou_invalide__message_explicite(
    fabrique: sessionmaker[Session], cas: str
) -> None:
    _, _, jeton, _ = _invite(fabrique)
    champ = {"expire": "expire_le", "utilise": "utilisee_le", "invalide": "invalidee_le"}.get(cas)
    if champ is not None:
        valeur = func.now() - timedelta(seconds=1)
        with fabrique() as s, s.begin():
            s.execute(update(INVITATION).values({champ: valeur}))
    saisi = {"inconnu": "A" * 43, "mal_forme": "pas un jeton"}.get(cas, jeton)
    r = _debut(client(fabrique), saisi)
    _refus(r, 410, "invitation.lien_invalide")
    assert r.json()["code"] == "lien_invalide"


# --- activation : fin --------------------------------------------------------------------------------


def test_activation_fin__code_juste_du_nouveau_secret__compte_actif(fabrique: sessionmaker[Session]) -> None:
    _, uid, jeton, _ = _invite(fabrique)
    r = _fin(client(fabrique), jeton)
    assert r.status_code == 200, r.text
    codes = r.json()["codes_secours"]
    assert len(codes) == len(set(codes)) == 10
    (u,) = lignes(fabrique, UTILISATEUR, UTILISATEUR.c.id == uid)
    assert u["statut"] == "actif"
    assert u["active_le"] is not None
    stockes = lignes(fabrique, CODE_SECOURS, CODE_SECOURS.c.utilisateur_id == uid)
    assert len(stockes) == 10
    assert all(not any(code in str(ligne["empreinte"]) for code in codes) for ligne in stockes)
    assert codes_secours.trouver(codes[3], [str(ligne["empreinte"]) for ligne in stockes]) is not None
    (lien,) = lignes(fabrique, INVITATION)
    assert lien["utilisee_le"] is not None


def test_activation_fin__code_faux__rien_n_est_active_lien_toujours_valable(
    fabrique: sessionmaker[Session],
) -> None:
    _, uid, jeton, _ = _invite(fabrique)
    c = client(fabrique)
    _debut(c, jeton)
    r = _fin(c, jeton, code="000000")
    _refus(r, 400, "activation.code_incorrect")
    assert r.json()["details"]["champs"][0]["champ"] == "code"
    (u,) = lignes(fabrique, UTILISATEUR, UTILISATEUR.c.id == uid)
    assert (u["statut"], u["mot_de_passe_hache"]) == ("invite", None)
    assert lignes(fabrique, CODE_SECOURS, CODE_SECOURS.c.utilisateur_id == uid) == []
    assert lignes(fabrique, OUTBOX) == []
    assert "lp_session" not in c.cookies
    assert _fin(c, jeton).status_code == 200


def test_activation_fin__sans_debut__code_refuse(fabrique: sessionmaker[Session]) -> None:
    _, _, jeton, _ = _invite(fabrique)
    _refus(_fin(client(fabrique), jeton, code="123456"), 400, "activation.code_incorrect")


@pytest.mark.parametrize(
    ("mot_de_passe", "motif"),
    [
        ("court", Motif.TROP_COURT),
        ("x y " * 40, Motif.TROP_LONG),
        ("aaaaaaaaaaaaaaaa", Motif.SUITE_OU_REPETITION),
        ("lepalier est bien pratique", Motif.NOM_APPLICATION),
        ("durand aime les fleurs", Motif.ADRESSE_EMAIL),
        ("!qazxsw2#edcvfr4", Motif.COURANT),
    ],
)
def test_activation_fin__mot_de_passe_refuse__message_du_motif(
    fabrique: sessionmaker[Session], mot_de_passe: str, motif: Motif
) -> None:
    _, uid, jeton, _ = _invite(fabrique)
    r = _fin(client(fabrique), jeton, mot_de_passe=mot_de_passe)
    assert r.status_code == 422
    assert r.json()["details"]["champs"] == [
        {"champ": "mot_de_passe", "message": message_mot_de_passe(motif)}
    ]
    (u,) = lignes(fabrique, UTILISATEUR, UTILISATEUR.c.id == uid)
    assert u["statut"] == "invite"


def test_activation_fin__nom_affiche_modifiable(fabrique: sessionmaker[Session]) -> None:
    _, uid, jeton, _ = _invite(fabrique)
    r = _fin(client(fabrique), jeton, nom_affiche="  Marie Durand ")
    assert r.json()["nom_affiche"] == "Marie Durand"
    (u,) = lignes(fabrique, UTILISATEUR, UTILISATEUR.c.id == uid)
    assert u["nom_affiche"] == "Marie Durand"


@pytest.mark.parametrize("nom", NOMS_REFUSES)
def test_activation_fin__nom_affiche_invalide__422_message_rien_n_est_active(
    fabrique: sessionmaker[Session], nom: str
) -> None:
    _, uid, jeton, _ = _invite(fabrique)
    r = _fin(client(fabrique), jeton, nom_affiche=nom)
    _refus(r, 422, "nom_affiche.invalide")
    assert r.json()["details"]["champs"][0]["champ"] == "nom_affiche"
    (u,) = lignes(fabrique, UTILISATEUR, UTILISATEUR.c.id == uid)
    assert (u["statut"], u["nom_affiche"]) == ("invite", "Mme Durand")


def test_activation_fin__publie_utilisateur_cree_avec_auteur_invite_par(
    fabrique: sessionmaker[Session],
) -> None:
    gerant, uid, jeton, _ = _invite(fabrique)
    _fin(client(fabrique), jeton, nom_affiche="Marie Durand")
    (evt,) = lignes(fabrique, OUTBOX)
    assert (evt["type"], evt["version"], evt["producteur"], evt["cle_agregat"]) == (
        "utilisateur.cree",
        1,
        "identity",
        uid,
    )
    assert evt["payload"] == {
        "utilisateur_id": str(uid),
        "role": "associe",
        "associe_id": None,
        "nom_affiche": "Marie Durand",
        "par_utilisateur_id": str(gerant.id),
    }
    assert CONTRAT_NOM.search(evt["payload"]["nom_affiche"])  # type: ignore[index]
    (journal,) = lignes(fabrique, JOURNAL, JOURNAL.c.action == "utilisateur.active")
    assert (journal["utilisateur_id"], journal["enregistrement_id"]) == (uid, uid)


def test_activation_fin__lien_deja_utilise__refuse_sans_rejeu(fabrique: sessionmaker[Session]) -> None:
    _, uid, jeton, _ = _invite(fabrique)
    c = client(fabrique)
    assert _fin(c, jeton).status_code == 200
    r = c.post(
        "/auth/activation/fin",
        json={"jeton": jeton, "mot_de_passe": "un tout autre mot de passe", "code": "123456"},
    )
    _refus(r, 410, "invitation.lien_invalide")
    assert len(lignes(fabrique, OUTBOX)) == 1
    assert len(lignes(fabrique, CODE_SECOURS, CODE_SECOURS.c.utilisateur_id == uid)) == 10


def test_activation_fin__session_complete_ouverte_pre_session_inutile(
    fabrique: sessionmaker[Session],
) -> None:
    _, uid, jeton, _ = _invite(fabrique)
    c = client(fabrique)
    _fin(c, jeton)
    assert "lp_pre" not in c.cookies
    assert {"lp_session", "lp_appareil"} <= set(c.cookies.keys())
    verify = c.get("/auth/verify")
    assert (verify.status_code, verify.headers["X-User-Id"]) == (200, str(uid))
    (session,) = lignes(fabrique, SESSION, SESSION.c.utilisateur_id == uid)
    assert session["etat"] == "active"
    assert lignes(fabrique, JOB, JOB.c.type == "courriel.nouvel_appareil") == []


def test_activation_fin__reponse_porte_les_codes_et_l_etape_confirmation_codes(
    fabrique: sessionmaker[Session],
) -> None:
    _, _, jeton, _ = _invite(fabrique)
    corps = _fin(client(fabrique), jeton).json()
    assert corps["etape"] == "confirmation_codes"
    assert set(corps) == {"etape", "codes_secours", "nom_affiche", "role"}
    assert all(re.fullmatch(r"[0-9A-Z]{4}-[0-9A-Z]{4}-[0-9A-Z]{4}", code) for code in corps["codes_secours"])


def test_activation_fin__codes_absents_de_toute_reponse_ulterieure_et_du_journal(
    fabrique: sessionmaker[Session],
) -> None:
    _, _, jeton, _ = _invite(fabrique)
    c = client(fabrique)
    codes = _fin(c, jeton).json()["codes_secours"]
    ulterieures = [_debut(c, jeton), c.get("/auth/verify"), c.post("/auth/deconnexion")]
    with fabrique() as s:
        journal = [repr(dict(ligne)) for ligne in s.execute(select(JOURNAL)).mappings()]
        sortants = [repr(dict(ligne)) for ligne in s.execute(select(OUTBOX)).mappings()]
    for code in codes:
        assert all(code not in r.text and code not in str(r.headers) for r in ulterieures)
        assert all(code not in texte for texte in journal + sortants)


def test_job_invitation__compte_active_entre_temps__aucun_email_ni_lien(
    fabrique: sessionmaker[Session],
) -> None:
    r = _inviter(client(fabrique), _gerant(fabrique))
    with fabrique() as s, s.begin():
        s.execute(
            update(UTILISATEUR).where(UTILISATEUR.c.id == uuid.UUID(r.json()["id"])).values(statut="suspendu")
        )
    expediteur = ExpediteurMemoire()
    assert executer_jobs(fabrique, expediteur) == ["termine"]
    assert expediteur.envoyes == []
    assert lignes(fabrique, INVITATION) == []


def test_inviter__meme_adresse_en_meme_temps__une_seule_invitation_409_pour_l_autre(
    fabrique: sessionmaker[Session],
) -> None:
    """L'autre invitation est écrite mais pas encore validée : seul l'index unique peut trancher."""
    gerant = _gerant(fabrique)
    resultat: list[Any] = []
    with fabrique() as autre, autre.begin():
        autre.execute(
            insert(UTILISATEUR).values(
                id=uuid7(),
                email=EMAIL.upper(),
                nom_affiche="Mme Durand",
                role="associe",
                origine="invitation",
                invite_par=gerant.id,
            )
        )
        fil = threading.Thread(target=lambda: resultat.append(_inviter(client(fabrique), gerant)))
        fil.start()
        with fabrique() as observateur:
            while not observateur.execute(
                text("SELECT count(*) FROM pg_stat_activity WHERE wait_event_type = 'Lock'")
            ).scalar():
                time.sleep(0.01)
                observateur.rollback()
    fil.join()
    _refus(resultat[0], 409, "utilisateurs.email_deja_utilise")
    assert len(lignes(fabrique, UTILISATEUR, func.lower(UTILISATEUR.c.email) == EMAIL)) == 1


@pytest.mark.parametrize("email", ["marie.durand@exemple.fr", "j+lepalier@essai.local", "O'Neil@essai.local"])
def test_inviter__email_ascii_imprimable__accepte(fabrique: sessionmaker[Session], email: str) -> None:
    r = _inviter(client(fabrique), _gerant(fabrique), email=f"  {email} ")
    assert (r.status_code, r.json()["email"]) == (201, email)
