"""Section E : réinitialisation du mot de passe (liste du 4 octobre 2026, ADR 0006)."""

from __future__ import annotations

import re
import statistics
import time
from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, sessionmaker

from app.courriels.textes import mot_de_passe_change, reinitialisation
from app.engines.jetons import empreinte
from app.engines.mot_de_passe import Motif
from app.libelles import message, message_mot_de_passe
from app.models import APPAREIL, JOB, JOURNAL, REINITIALISATION, SESSION, TENTATIVE_CONNEXION, UTILISATEUR

from .aides import (
    MOT_DE_PASSE,
    ORIGINE,
    Compte,
    ExpediteurMemoire,
    client,
    creer_compte,
    executer_jobs,
    lignes,
)

pytestmark = pytest.mark.integration

EMAIL = "durand@essai.local"
NOUVEAU = "les tilleuls fleurissent en juin"


def _demander(c: TestClient, email: str = EMAIL) -> Any:
    return c.post("/auth/reinitialisation/demande", json={"email": email})


def _jeton(expediteur: ExpediteurMemoire, rang: int = -1) -> str:
    _, courriel = expediteur.envoyes[rang]
    trouve = re.search(r"/reinitialisation#([A-Za-z0-9_-]{43})", courriel.corps)
    assert trouve is not None
    return trouve.group(1)


def _lien(fabrique: sessionmaker[Session], email: str = EMAIL) -> tuple[Compte, str, ExpediteurMemoire]:
    compte = creer_compte(fabrique, email=email)
    assert _demander(client(fabrique), email).status_code == 202
    expediteur = ExpediteurMemoire()
    executer_jobs(fabrique, expediteur)
    return compte, _jeton(expediteur), expediteur


def _fin(c: TestClient, jeton: str, code: str, mot_de_passe: str = NOUVEAU) -> Any:
    return c.post(
        "/auth/reinitialisation/fin", json={"jeton": jeton, "mot_de_passe": mot_de_passe, "code": code}
    )


def _refus(r: Any, statut: int, cle: str) -> None:
    assert r.status_code == statut, r.text
    assert r.json()["message"] == message(cle)


def _jobs(fabrique: sessionmaker[Session], type_: str) -> list[dict[str, object]]:
    return lignes(fabrique, JOB, JOB.c.type == type_)


# --- demande -----------------------------------------------------------------------------------------


def test_demande__message_identique_compte_existant_inconnu_invite_ou_suspendu(
    fabrique: sessionmaker[Session],
) -> None:
    creer_compte(fabrique, email=EMAIL)
    creer_compte(fabrique, email="invite@essai.local", statut="invite")
    creer_compte(fabrique, email="suspendu@essai.local", statut="suspendu")
    reponses = [
        _demander(client(fabrique), email)
        for email in (EMAIL, "personne@essai.local", "invite@essai.local", "suspendu@essai.local")
    ]
    assert {(r.status_code, r.text) for r in reponses} == {
        (202, f'{{"message":"{message("reinitialisation.demande_envoyee")}"}}')
    }
    assert len(_jobs(fabrique, "courriel.reinitialisation")) == 1


def test_demande__temps_comparable__travail_factice_pour_compte_inconnu(
    fabrique: sessionmaker[Session],
) -> None:
    for i in range(8):
        creer_compte(fabrique, email=f"compte{i}@essai.local")
    c = client(fabrique)
    connus: list[float] = []
    inconnus: list[float] = []
    for i in range(8):
        for email, durees in ((f"compte{i}@essai.local", connus), (f"inconnu{i}@essai.local", inconnus)):
            debut = time.perf_counter()
            _demander(c, email)
            durees.append(time.perf_counter() - debut)
    assert abs(statistics.median(connus) - statistics.median(inconnus)) < 0.05


def test_demande__compte_actif__job_d_envoi_sans_jeton_stocke(fabrique: sessionmaker[Session]) -> None:
    compte, jeton, expediteur = _lien(fabrique)
    (job,) = _jobs(fabrique, "courriel.reinitialisation")
    assert job["payload"] == {"utilisateur_id": str(compte.id)}
    assert expediteur.envoyes == [
        (EMAIL, reinitialisation("Mme Durand", f"{ORIGINE}/reinitialisation#{jeton}"))
    ]
    (lien,) = lignes(fabrique, REINITIALISATION)
    assert lien["empreinte"] == empreinte(jeton)
    with fabrique() as s:
        for table in (JOB, JOURNAL):
            for ligne in s.execute(select(table)).mappings():
                assert jeton not in repr(dict(ligne))


def test_demande__quatrieme_dans_l_heure__ignoree_meme_message(fabrique: sessionmaker[Session]) -> None:
    creer_compte(fabrique, email=EMAIL)
    reponses = [_demander(client(fabrique)) for _ in range(4)]
    assert len({(r.status_code, r.text) for r in reponses}) == 1
    assert len(_jobs(fabrique, "courriel.reinitialisation")) == 3


def test_demande__une_heure_apres__de_nouveau_acceptee(fabrique: sessionmaker[Session]) -> None:
    creer_compte(fabrique, email=EMAIL)
    for _ in range(3):
        _demander(client(fabrique))
    with fabrique() as s, s.begin():
        s.execute(update(JOB).values(cree_le=func.now() - timedelta(hours=1, seconds=1)))
    _demander(client(fabrique))
    assert len(_jobs(fabrique, "courriel.reinitialisation")) == 4


def test_demande__adresse_sans_tenir_compte_de_la_casse(fabrique: sessionmaker[Session]) -> None:
    creer_compte(fabrique, email=EMAIL)
    _demander(client(fabrique), "  Durand@Essai.LOCAL ")
    assert len(_jobs(fabrique, "courriel.reinitialisation")) == 1


def test_demande__nouvelle_demande__lien_precedent_invalide(fabrique: sessionmaker[Session]) -> None:
    compte, ancien, expediteur = _lien(fabrique)
    _demander(client(fabrique))
    _refus(_fin(client(fabrique), ancien, compte.code_totp()), 410, "reinitialisation.lien_invalide")
    executer_jobs(fabrique, expediteur)
    assert _fin(client(fabrique), _jeton(expediteur), compte.code_totp(30)).status_code == 204


def test_job_reinitialisation__compte_suspendu_entre_temps__aucun_email(
    fabrique: sessionmaker[Session],
) -> None:
    compte = creer_compte(fabrique, email=EMAIL)
    _demander(client(fabrique))
    with fabrique() as s, s.begin():
        s.execute(update(UTILISATEUR).where(UTILISATEUR.c.id == compte.id).values(statut="suspendu"))
    expediteur = ExpediteurMemoire()
    assert executer_jobs(fabrique, expediteur) == ["termine"]
    assert (expediteur.envoyes, lignes(fabrique, REINITIALISATION)) == ([], [])


# --- fin ---------------------------------------------------------------------------------------------


def test_fin__lien_1_h__expire_a_1_h_plus_1_s(fabrique: sessionmaker[Session]) -> None:
    compte, jeton, _ = _lien(fabrique)
    (lien,) = lignes(fabrique, REINITIALISATION)
    assert lien["expire_le"] - lien["cree_le"] == timedelta(hours=1)  # type: ignore[operator]
    with fabrique() as s, s.begin():
        s.execute(update(REINITIALISATION).values(expire_le=func.now() - timedelta(seconds=1)))
    _refus(_fin(client(fabrique), jeton, compte.code_totp()), 410, "reinitialisation.lien_invalide")


@pytest.mark.parametrize("sorte", ["totp", "secours"])
def test_fin__code_totp_ou_de_secours_exige(fabrique: sessionmaker[Session], sorte: str) -> None:
    compte, jeton, _ = _lien(fabrique)
    c = client(fabrique)
    _refus(_fin(c, jeton, ""), 400, "code.incorrect")
    _refus(_fin(c, jeton, "000000"), 400, "code.incorrect")
    code = compte.code_totp() if sorte == "totp" else compte.codes[0]
    assert _fin(c, jeton, code).status_code == 204


@pytest.mark.parametrize(
    ("mot_de_passe", "motif"),
    [("court", Motif.TROP_COURT), ("durand aime les fleurs", Motif.ADRESSE_EMAIL)],
)
def test_fin__mot_de_passe_refuse__message_du_motif(
    fabrique: sessionmaker[Session], mot_de_passe: str, motif: Motif
) -> None:
    compte, jeton, _ = _lien(fabrique)
    r = _fin(client(fabrique), jeton, compte.code_totp(), mot_de_passe)
    assert r.status_code == 422
    assert r.json()["details"]["champs"] == [
        {"champ": "mot_de_passe", "message": message_mot_de_passe(motif)}
    ]
    assert _fin(client(fabrique), jeton, compte.code_totp()).status_code == 204


def test_fin__sessions_appareils_et_tous_les_liens_revoques_email_info(
    fabrique: sessionmaker[Session],
) -> None:
    compte, jeton, expediteur = _lien(fabrique)
    ancien = client(fabrique)
    ancien.post("/auth/connexion", json={"email": EMAIL, "mot_de_passe": MOT_DE_PASSE})
    ancien.post("/auth/code", json={"code": compte.code_totp(-30)})
    assert ancien.get("/auth/verify").status_code == 200
    assert _fin(client(fabrique), jeton, compte.code_totp()).status_code == 204

    assert ancien.get("/auth/verify").status_code == 401
    sessions = lignes(fabrique, SESSION, SESSION.c.utilisateur_id == compte.id)
    assert sessions and all(s["revoquee_le"] is not None for s in sessions)
    assert {s["motif_revocation"] for s in sessions} <= {"reinitialisation", "rotation"}
    assert all(
        a["revoque_le"] is not None
        for a in lignes(fabrique, APPAREIL, APPAREIL.c.utilisateur_id == compte.id)
    )
    (u,) = lignes(fabrique, UTILISATEUR, UTILISATEUR.c.id == compte.id)
    assert u["mot_de_passe_change_le"] is not None
    (lien,) = lignes(fabrique, REINITIALISATION)
    assert lien["utilisee_le"] is not None
    (journal,) = lignes(fabrique, JOURNAL, JOURNAL.c.action == "utilisateur.mot_de_passe_reinitialise")
    assert journal["enregistrement_id"] == compte.id

    (job,) = _jobs(fabrique, "courriel.mot_de_passe_change")
    assert set(job["payload"]) == {"utilisateur_id", "instant"}  # type: ignore[call-overload]
    executer_jobs(fabrique, expediteur)
    assert expediteur.envoyes[-1] == (EMAIL, mot_de_passe_change("Mme Durand", u["mot_de_passe_change_le"]))  # type: ignore[arg-type]

    nouveau = client(fabrique)
    assert (
        nouveau.post("/auth/connexion", json={"email": EMAIL, "mot_de_passe": MOT_DE_PASSE}).status_code
        == 401
    )
    assert nouveau.post("/auth/connexion", json={"email": EMAIL, "mot_de_passe": NOUVEAU}).status_code == 200


def test_fin__lien_reutilise__refuse(fabrique: sessionmaker[Session]) -> None:
    compte, jeton, _ = _lien(fabrique)
    assert _fin(client(fabrique), jeton, compte.code_totp()).status_code == 204
    _refus(_fin(client(fabrique), jeton, compte.codes[1]), 410, "reinitialisation.lien_invalide")


@pytest.mark.parametrize("statut", ["suspendu", "invite"])
def test_fin__compte_plus_actif__lien_refuse(fabrique: sessionmaker[Session], statut: str) -> None:
    compte, jeton, _ = _lien(fabrique)
    with fabrique() as s, s.begin():
        s.execute(update(UTILISATEUR).where(UTILISATEUR.c.id == compte.id).values(statut=statut))
    _refus(_fin(client(fabrique), jeton, compte.code_totp()), 410, "reinitialisation.lien_invalide")


def test_fin__cinq_codes_faux__lien_invalide_echecs_inscrits(fabrique: sessionmaker[Session]) -> None:
    compte, jeton, _ = _lien(fabrique)
    c = client(fabrique)
    for code in ("000000", "111111", "AAAA-BBBB-CCCC", "222222"):
        _refus(_fin(c, jeton, code), 400, "code.incorrect")
    _refus(_fin(c, jeton, "333333"), 400, "reinitialisation.trop_de_codes")
    (lien,) = lignes(fabrique, REINITIALISATION)
    assert (lien["essais_code"], lien["invalidee_le"] is not None) == (5, True)
    _refus(_fin(c, jeton, compte.code_totp()), 410, "reinitialisation.lien_invalide")
    echecs = lignes(fabrique, TENTATIVE_CONNEXION, TENTATIVE_CONNEXION.c.utilisateur_id == compte.id)
    assert len(echecs) == 5
    assert all(not e["reussie"] for e in echecs)
    assert sorted(str(e["etape"]) for e in echecs) == ["secours"] + ["totp"] * 4
    (u,) = lignes(fabrique, UTILISATEUR, UTILISATEUR.c.id == compte.id)
    assert u["mot_de_passe_change_le"] is None


def test_demande__quatrieme_ignoree__n_invalide_pas_le_lien_en_cours(fabrique: sessionmaker[Session]) -> None:
    compte = creer_compte(fabrique, email=EMAIL)
    expediteur = ExpediteurMemoire()
    for _ in range(3):
        _demander(client(fabrique))
        executer_jobs(fabrique, expediteur)
    jeton = _jeton(expediteur)
    _demander(client(fabrique))
    assert executer_jobs(fabrique, expediteur) == []
    assert _fin(client(fabrique), jeton, compte.code_totp()).status_code == 204


@pytest.mark.parametrize("sorte", ["totp", "secours"])
def test_fin__mot_de_passe_refuse__code_non_consomme(fabrique: sessionmaker[Session], sorte: str) -> None:
    compte, jeton, _ = _lien(fabrique)
    code = compte.code_totp() if sorte == "totp" else compte.codes[0]
    assert _fin(client(fabrique), jeton, code, "court").status_code == 422
    (u,) = lignes(fabrique, UTILISATEUR, UTILISATEUR.c.id == compte.id)
    assert u["totp_dernier_pas"] is None
    (lien,) = lignes(fabrique, REINITIALISATION)
    assert lien["essais_code"] == 0
    assert lignes(fabrique, TENTATIVE_CONNEXION, TENTATIVE_CONNEXION.c.utilisateur_id == compte.id) == []
    assert _fin(client(fabrique), jeton, code).status_code == 204


def test_fin__couple_compte_ip_verrouille__trop_d_essais_avant_le_code(
    fabrique: sessionmaker[Session],
) -> None:
    compte, jeton, _ = _lien(fabrique)
    for _ in range(5):
        client(fabrique).post(
            "/auth/connexion", json={"email": EMAIL, "mot_de_passe": "un autre mot de passe"}
        )
    r = _fin(client(fabrique), jeton, compte.code_totp())
    assert r.status_code == 429
    assert r.json()["message"] == message("connexion.trop_d_essais")
    (u,) = lignes(fabrique, UTILISATEUR, UTILISATEUR.c.id == compte.id)
    assert (u["totp_dernier_pas"], u["mot_de_passe_change_le"]) == (None, None)
    (lien,) = lignes(fabrique, REINITIALISATION)
    assert (lien["essais_code"], lien["invalidee_le"]) == (0, None)
    assert _fin(client(fabrique, ip="10.9.9.9"), jeton, compte.code_totp()).status_code == 204
