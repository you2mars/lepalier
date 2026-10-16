"""Section H : commande d'administration locale (ADR 0006, décision 5), sans route HTTP."""

from __future__ import annotations

import io
import os
import re
from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, sessionmaker

from app import admin
from app.libelles import message
from app.models import APPAREIL, CODE_SECOURS, INVITATION, JOB, JOURNAL, SESSION, UTILISATEUR
from commun.dates import heure_paris

from .aides import MOT_DE_PASSE, ORIGINE, application, client, creer_compte, lignes

pytestmark = pytest.mark.integration

EMAIL = "gerant@essai.local"


def _lancer(fabrique: sessionmaker[Session], *arguments: str) -> tuple[int, str, str]:
    sortie, erreur = io.StringIO(), io.StringIO()
    code = admin.main(list(arguments), fabrique=fabrique, url_publique=ORIGINE, sortie=sortie, erreur=erreur)
    return code, sortie.getvalue(), erreur.getvalue()


def _jeton(texte: str) -> str:
    trouve = re.search(r"/activation#([A-Za-z0-9_-]{43})", texte)
    assert trouve is not None
    return trouve.group(1)


def _creer(
    fabrique: sessionmaker[Session], email: str = EMAIL, nom: str = "M. Martin"
) -> tuple[int, str, str]:
    return _lancer(fabrique, "creer-gerant", "--email", email, "--nom", nom)


# --- créer le premier gérant ------------------------------------------------------------------------


def test_admin_creer_gerant__origine_commande_locale_invite_par_null(fabrique: sessionmaker[Session]) -> None:
    code, _, erreur = _creer(fabrique)
    assert (code, erreur) == (0, "")
    (u,) = lignes(fabrique, UTILISATEUR)
    assert (u["role"], u["statut"], u["origine"], u["invite_par"], u["nom_affiche"]) == (
        "gerant",
        "invite",
        "commande_locale",
        None,
        "M. Martin",
    )
    (journal,) = lignes(fabrique, JOURNAL, JOURNAL.c.action == "utilisateur.invite")
    assert (journal["utilisateur_id"], journal["enregistrement_id"]) == (None, u["id"])
    (lien,) = lignes(fabrique, INVITATION)
    assert lien["par_utilisateur_id"] is None
    assert lignes(fabrique, JOB) == []


def _heure_limite(fabrique: sessionmaker[Session]) -> str:
    (lien,) = lignes(
        fabrique, INVITATION, INVITATION.c.utilisee_le.is_(None), INVITATION.c.invalidee_le.is_(None)
    )
    return heure_paris(lien["expire_le"])  # type: ignore[arg-type]


def test_admin_creer_gerant__texte_affiche_mot_pour_mot(fabrique: sessionmaker[Session]) -> None:
    _, sortie, _ = _creer(fabrique)
    lien = f"{ORIGINE}/activation#{_jeton(sortie)}"
    assert sortie == (
        "Compte gérant créé pour M. Martin.\n"
        f"Lien d'activation, valable 1 heure (jusqu'à {_heure_limite(fabrique)}) et affiché une seule fois : "
        "ouvrez-le, puis suivez les étapes à l'écran.\n"
        f"{lien}\n"
    )


def test_admin__heure_limite_a_l_heure_de_paris() -> None:
    from datetime import UTC, datetime

    assert admin.consigne_lien(datetime(2026, 7, 14, 17, 42, tzinfo=UTC)).startswith(
        "Lien d'activation, valable 1 heure (jusqu'à 19 h 42)"
    )


def test_admin_creer_gerant__lien_valable_1_h_affiche_une_seule_fois(fabrique: sessionmaker[Session]) -> None:
    _, sortie, _ = _creer(fabrique)
    jeton = _jeton(sortie)
    (lien,) = lignes(fabrique, INVITATION)
    assert lien["expire_le"] - lien["cree_le"] == timedelta(hours=1)  # type: ignore[operator]
    c = client(fabrique)
    assert c.post("/auth/activation/debut", json={"jeton": jeton}).status_code == 200
    with fabrique() as s, s.begin():
        s.execute(update(INVITATION).values(expire_le=func.now() - timedelta(seconds=1)))
    r = c.post("/auth/activation/debut", json={"jeton": jeton})
    assert (r.status_code, r.json()["message"]) == (410, message("invitation.lien_invalide"))


def test_admin_creer_gerant__activation_publie_utilisateur_cree_sans_auteur(
    fabrique: sessionmaker[Session],
) -> None:
    from .test_invitation_activation import _fin

    _, sortie, _ = _creer(fabrique)
    assert _fin(client(fabrique), _jeton(sortie), nom_affiche="M. Martin").status_code == 200
    from app.models import OUTBOX

    (evt,) = lignes(fabrique, OUTBOX)
    assert (evt["type"], evt["payload"]["par_utilisateur_id"], evt["payload"]["role"]) == (  # type: ignore[index]
        "utilisateur.cree",
        None,
        "gerant",
    )


def test_admin__lien_jamais_dans_journal_job_ni_fichier(
    fabrique: sessionmaker[Session], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _, sortie, erreur = _creer(fabrique)
    jeton = _jeton(sortie)
    assert jeton not in erreur
    with fabrique() as s:
        for table in (JOURNAL, JOB, INVITATION, UTILISATEUR):
            for ligne in s.execute(select(table)).mappings():
                assert jeton not in repr(dict(ligne))
    assert os.listdir(tmp_path) == []


@pytest.mark.parametrize("email", [EMAIL, "  Gerant@Essai.LOCAL "])
def test_admin_creer_gerant__email_deja_utilise__refus_sans_rien_creer(
    fabrique: sessionmaker[Session], email: str
) -> None:
    creer_compte(fabrique, email=EMAIL)
    code, sortie, erreur = _creer(fabrique, email=email)
    assert (code, sortie) == (1, "")
    assert erreur == message("utilisateurs.email_deja_utilise") + "\n"
    assert len(lignes(fabrique, UTILISATEUR)) == 1
    assert lignes(fabrique, INVITATION) == []
    assert lignes(fabrique, JOURNAL) == []


@pytest.mark.parametrize(
    ("email", "nom", "cle"),
    [
        ("pas-une-adresse", "M. Martin", "utilisateurs.email_invalide"),
        (EMAIL, "M. Martin\nObjet : faux", "nom_affiche.invalide"),
        (EMAIL, "martin@essai.local", "nom_affiche.invalide"),
    ],
)
def test_admin_creer_gerant__saisie_refusee__message_sans_rien_creer(
    fabrique: sessionmaker[Session], email: str, nom: str, cle: str
) -> None:
    code, sortie, erreur = _creer(fabrique, email=email, nom=nom)
    assert (code, sortie, erreur) == (1, "", message(cle) + "\n")
    assert lignes(fabrique, UTILISATEUR) == []


# --- réinitialiser l'accès d'un gérant bloqué ---------------------------------------------------------


def test_admin_reinitialiser_acces__gerant_bloque__sessions_revoquees_nouveau_lien(
    fabrique: sessionmaker[Session],
) -> None:
    gerant = creer_compte(fabrique, email=EMAIL, role="gerant", nom_affiche="M. Martin")
    c = client(fabrique)
    c.post("/auth/connexion", json={"email": EMAIL, "mot_de_passe": MOT_DE_PASSE})
    c.post("/auth/code", json={"code": gerant.code_totp()})
    code, sortie, erreur = _lancer(fabrique, "reinitialiser-acces", "--email", " Gerant@essai.local")
    assert (code, erreur) == (0, "")
    assert sortie == (
        "Accès de M. Martin réinitialisé : ancien mot de passe, codes de secours et codes de l'application "
        "d'authentification ne fonctionnent plus.\n"
        f"Lien d'activation, valable 1 heure (jusqu'à {_heure_limite(fabrique)}) et affiché une seule fois : "
        "ouvrez-le, puis suivez les étapes à l'écran.\n"
        f"{ORIGINE}/activation#{_jeton(sortie)}\n"
    )
    assert c.get("/auth/verify").status_code == 401
    (u,) = lignes(fabrique, UTILISATEUR)
    assert (u["statut"], u["mot_de_passe_hache"], u["totp_secret_chiffre"]) == ("invite", None, None)
    sessions = lignes(fabrique, SESSION, SESSION.c.etat == "active")
    assert [s["motif_revocation"] for s in sessions] == ["totp_reinitialise"]
    assert all(a["revoque_le"] is not None for a in lignes(fabrique, APPAREIL))
    assert all(c["invalide_le"] is not None for c in lignes(fabrique, CODE_SECOURS))
    (journal,) = lignes(fabrique, JOURNAL, JOURNAL.c.action == "utilisateur.acces_reinitialise")
    assert journal["utilisateur_id"] is None
    assert lignes(fabrique, JOB, JOB.c.type == "courriel.acces_reinitialise") == []


def test_admin_reinitialiser_acces__gerant_bloque__meme_regle_lien_1_h(
    fabrique: sessionmaker[Session],
) -> None:
    creer_compte(fabrique, email=EMAIL, role="gerant")
    _, sortie, _ = _lancer(fabrique, "reinitialiser-acces", "--email", EMAIL)
    (lien,) = lignes(fabrique, INVITATION)
    assert lien["expire_le"] - lien["cree_le"] == timedelta(hours=1)  # type: ignore[operator]
    assert lien["par_utilisateur_id"] is None
    assert client(fabrique).post("/auth/activation/debut", json={"jeton": _jeton(sortie)}).status_code == 200


def test_admin_reinitialiser_acces__lien_precedent_invalide(fabrique: sessionmaker[Session]) -> None:
    creer_compte(fabrique, email=EMAIL, role="gerant")
    _, premiere, _ = _lancer(fabrique, "reinitialiser-acces", "--email", EMAIL)
    _, seconde, _ = _lancer(fabrique, "reinitialiser-acces", "--email", EMAIL)
    c = client(fabrique)
    assert c.post("/auth/activation/debut", json={"jeton": _jeton(premiere)}).status_code == 410
    assert c.post("/auth/activation/debut", json={"jeton": _jeton(seconde)}).status_code == 200


@pytest.mark.parametrize("expire", [False, True], ids=["invitation_envoyee", "invitation_expiree"])
def test_admin_reinitialiser_acces__gerant_jamais_active__nouveau_lien_qui_active(
    fabrique: sessionmaker[Session], expire: bool
) -> None:
    """Commande proposée par make recette LOT=0 quand le gérant du jeu est encore invité."""
    _, premiere, _ = _creer(fabrique)
    if expire:
        with fabrique() as s, s.begin():
            s.execute(update(INVITATION).values(expire_le=func.now() - timedelta(minutes=1)))
    code, sortie, erreur = _lancer(fabrique, "reinitialiser-acces", "--email", EMAIL)
    assert (code, erreur) == (0, "")
    c = client(fabrique)
    assert c.post("/auth/activation/debut", json={"jeton": _jeton(premiere)}).status_code == 410
    assert c.post("/auth/activation/debut", json={"jeton": _jeton(sortie)}).status_code == 200
    (u,) = lignes(fabrique, UTILISATEUR)
    assert (u["role"], u["statut"]) == ("gerant", "invite")


@pytest.mark.parametrize("role", ["gerant", "associe", "operateur"])
def test_admin_reinitialiser_acces__tous_les_roles(fabrique: sessionmaker[Session], role: str) -> None:
    creer_compte(fabrique, email=EMAIL, role=role)
    assert _lancer(fabrique, "reinitialiser-acces", "--email", EMAIL)[0] == 0


def test_admin_reinitialiser_acces__compte_suspendu__refus_sans_rien_changer(
    fabrique: sessionmaker[Session],
) -> None:
    creer_compte(fabrique, email=EMAIL, role="gerant", statut="suspendu")
    code, sortie, erreur = _lancer(fabrique, "reinitialiser-acces", "--email", EMAIL)
    assert (code, sortie, erreur) == (1, "", message("utilisateurs.acces_suspendu") + "\n")
    (u,) = lignes(fabrique, UTILISATEUR)
    assert (u["statut"], u["mot_de_passe_hache"] is not None) == ("suspendu", True)
    assert lignes(fabrique, INVITATION) == []
    assert lignes(fabrique, JOURNAL) == []


def test_admin_reinitialiser_acces__compte_inconnu__message_sans_rien_changer(
    fabrique: sessionmaker[Session],
) -> None:
    code, sortie, erreur = _lancer(fabrique, "reinitialiser-acces", "--email", "personne@essai.local")
    assert (code, sortie) == (1, "")
    assert erreur == "Aucun compte n'a cette adresse e-mail. Vérifiez l'adresse puis recommencez.\n"
    assert lignes(fabrique, JOURNAL) == []


def test_admin__commande_inconnue_ou_incomplete__code_2(fabrique: sessionmaker[Session]) -> None:
    assert _lancer(fabrique, "supprimer-tout")[0] == 2
    assert _lancer(fabrique, "creer-gerant", "--email", EMAIL)[0] == 2


def test_admin__aucune_route_http_ne_l_expose(fabrique: sessionmaker[Session]) -> None:
    import app.main

    chemins = application(fabrique).openapi()["paths"]
    assert not any(re.search(r"admin|creer-gerant|commande", chemin) for chemin in chemins)
    assert "app.admin" not in Path(app.main.__file__).read_text()
