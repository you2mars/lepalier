"""Section A : connexion et pré-session (liste validée le 4 octobre 2026)."""

from __future__ import annotations

import threading
from datetime import timedelta
from typing import Any

import pytest
from argon2 import PasswordHasher
from argon2.low_level import Type
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, sessionmaker

from app.api.auth import IP_INCONNUE
from app.engines.chiffrement import pseudonymiser
from app.libelles import message
from app.models import IDEMPOTENCE, JOB, JOURNAL, SESSION, TENTATIVE_CONNEXION, UTILISATEUR
from app.services import connexion as service_connexion

from .aides import CLES, IP, MOT_DE_PASSE, ORIGINE, Compte, application, client, creer_compte, lignes, valeur

pytestmark = pytest.mark.integration


def _connexion(c: TestClient, email: str, mot_de_passe: str = MOT_DE_PASSE, **entetes: str) -> Any:
    return c.post("/auth/connexion", json={"email": email, "mot_de_passe": mot_de_passe}, headers=entetes)


def _code(c: TestClient, code: str) -> Any:
    return c.post("/auth/code", json={"code": code})


def _connecte(fabrique: sessionmaker[Session], compte: Compte) -> TestClient:
    c = client(fabrique)
    assert _connexion(c, compte.email).status_code == 200
    assert _code(c, compte.code_totp()).status_code == 200
    return c


def _sessions(fabrique: sessionmaker[Session], compte: Compte) -> list[dict[str, object]]:
    return lignes(fabrique, SESSION, SESSION.c.utilisateur_id == compte.id)


# --- connexion (mot de passe) --------------------------------------------------------------------


def test_connexion__identifiants_corrects__pre_session_seulement(fabrique: sessionmaker[Session]) -> None:
    compte = creer_compte(fabrique)
    c = client(fabrique)
    r = _connexion(c, compte.email)
    assert r.status_code == 200
    assert r.json() == {"etape": "code"}
    assert "lp_pre" in c.cookies and "lp_session" not in c.cookies
    assert [s["etat"] for s in _sessions(fabrique, compte)] == ["pre_totp"]
    assert c.get("/auth/verify").status_code == 401


@pytest.mark.parametrize("cas", ["mot_de_passe_faux", "compte_inconnu", "compte_invite"])
def test_connexion__mauvais_mot_de_passe__message_unique_sous_le_champ(
    fabrique: sessionmaker[Session], cas: str
) -> None:
    compte = creer_compte(fabrique, statut="invite" if cas == "compte_invite" else "actif")
    email = "personne@essai.local" if cas == "compte_inconnu" else compte.email
    mot_de_passe = "un autre mot de passe" if cas == "mot_de_passe_faux" else MOT_DE_PASSE
    r = _connexion(client(fabrique), email, mot_de_passe)
    assert r.status_code == 401
    corps = r.json()
    assert corps["code"] == "identifiants_incorrects"
    assert corps["message"] == message("connexion.identifiants_incorrects")
    assert corps["details"] == {
        "champs": [{"champ": "mot_de_passe", "message": message("connexion.identifiants_incorrects")}]
    }


def test_connexion__compte_inconnu__verification_factice_appelee(
    fabrique: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    appels: list[str] = []

    def espion(mot_de_passe: str) -> bool:
        appels.append(mot_de_passe)
        return False

    monkeypatch.setattr(service_connexion, "verifier_factice", espion)
    _connexion(client(fabrique), "personne@essai.local")
    assert appels == [MOT_DE_PASSE]
    assert valeur(fabrique, select(func.count()).select_from(JOURNAL)) == 0


def test_connexion__echec__tentative_hmac_ip_etape_enregistree(fabrique: sessionmaker[Session]) -> None:
    compte = creer_compte(fabrique, email="Associe@Essai.local")
    _connexion(client(fabrique), "  associe@essai.LOCAL ", "un autre mot de passe")
    (tentative,) = lignes(fabrique, TENTATIVE_CONNEXION)
    assert tentative["cle_compte"] == pseudonymiser("associe@essai.local", CLES.pseudonymisation)
    assert str(tentative["ip"]) == IP
    assert (tentative["etape"], tentative["reussie"], tentative["utilisateur_id"]) == (
        "mot_de_passe",
        False,
        compte.id,
    )
    with fabrique() as s:
        texte = str(s.execute(select(TENTATIVE_CONNEXION)).all()) + str(s.execute(select(JOURNAL)).all())
    assert "associe@essai" not in texte.lower()


def _cinq_echecs(c: TestClient, email: str) -> None:
    for _ in range(5):
        assert _connexion(c, email, "un autre mot de passe").status_code == 401


def test_connexion__couple_verrouille__trop_d_essais_sans_verification(
    fabrique: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    compte = creer_compte(fabrique)
    c = client(fabrique)
    _cinq_echecs(c, compte.email)
    verifications: list[str] = []
    origine = service_connexion.verifier

    def espion(hache: str, mot_de_passe: str) -> bool:
        verifications.append(mot_de_passe)
        return origine(hache, mot_de_passe)

    monkeypatch.setattr(service_connexion, "verifier", espion)
    r = _connexion(c, compte.email)
    assert r.status_code == 429
    assert (r.json()["code"], r.json()["message"]) == ("trop_d_essais", message("connexion.trop_d_essais"))
    assert verifications == []
    assert valeur(fabrique, select(func.count()).select_from(TENTATIVE_CONNEXION)) == 5


def test_connexion__couple_verrouille__autre_ip_non_bloquee(fabrique: sessionmaker[Session]) -> None:
    compte = creer_compte(fabrique)
    _cinq_echecs(client(fabrique), compte.email)
    assert _connexion(client(fabrique, ip="10.0.0.7"), compte.email).status_code == 200


def test_connexion__compte_inconnu_verrouille__meme_message_et_meme_delai(
    fabrique: sessionmaker[Session],
) -> None:
    c = client(fabrique)
    _cinq_echecs(c, "personne@essai.local")
    r = _connexion(c, "personne@essai.local")
    assert r.status_code == 429
    assert r.json()["message"] == message("connexion.trop_d_essais")


def test_connexion__verrou_leve_15_min_apres_le_5e_echec(fabrique: sessionmaker[Session]) -> None:
    compte = creer_compte(fabrique)
    c = client(fabrique)
    _cinq_echecs(c, compte.email)
    with fabrique() as s, s.begin():
        s.execute(
            update(TENTATIVE_CONNEXION).values(
                cree_le=TENTATIVE_CONNEXION.c.cree_le - timedelta(minutes=15, seconds=1)
            )
        )
    assert _connexion(c, compte.email).status_code == 200


@pytest.mark.parametrize("saisie", [MOT_DE_PASSE + " ", " " + MOT_DE_PASSE, MOT_DE_PASSE.replace(" ", "  ")])
def test_connexion__mot_de_passe_avec_espace_final__accepte(
    fabrique: sessionmaker[Session], saisie: str
) -> None:
    compte = creer_compte(fabrique)
    assert _connexion(client(fabrique), compte.email, saisie).status_code == 200


def test_connexion__mot_de_passe_ancien_format__rehache_apres_succes(fabrique: sessionmaker[Session]) -> None:
    ancien = PasswordHasher(time_cost=1, memory_cost=8192, parallelism=1, type=Type.ID).hash(MOT_DE_PASSE)
    compte = creer_compte(fabrique, mot_de_passe_hache=ancien)
    assert _connexion(client(fabrique), compte.email).status_code == 200
    nouveau = valeur(fabrique, select(UTILISATEUR.c.mot_de_passe_hache).where(UTILISATEUR.c.id == compte.id))
    assert isinstance(nouveau, str)
    assert nouveau.startswith("$argon2id$v=19$m=19456,t=2,p=1$")


# --- code (second facteur) -------------------------------------------------------------------------


def test_code__totp_juste__session_complete_et_pre_session_revoquee_rotation(
    fabrique: sessionmaker[Session],
) -> None:
    compte = creer_compte(fabrique)
    c = client(fabrique)
    _connexion(c, compte.email)
    pre = c.cookies["lp_pre"]
    r = _code(c, compte.code_totp())
    assert r.status_code == 200
    assert r.json() == {"nom_affiche": "Mme Durand", "role": "associe"}
    assert "lp_session" in c.cookies and "lp_pre" not in c.cookies
    assert c.cookies["lp_session"] != pre
    sessions = {s["etat"]: s for s in _sessions(fabrique, compte)}
    assert sessions["pre_totp"]["motif_revocation"] == "rotation"
    assert sessions["active"]["revoquee_le"] is None
    assert (
        valeur(fabrique, select(UTILISATEUR.c.totp_dernier_pas).where(UTILISATEUR.c.id == compte.id))
        is not None
    )
    assert c.get("/auth/verify").status_code == 200


def test_code__meme_code_rejoue__refuse(fabrique: sessionmaker[Session]) -> None:
    compte = creer_compte(fabrique)
    code = compte.code_totp()
    premier = client(fabrique)
    _connexion(premier, compte.email)
    assert _code(premier, code).status_code == 200
    c = client(fabrique)
    _connexion(c, compte.email)
    r = _code(c, code)
    assert r.status_code == 401
    assert r.json()["message"] == message("code.incorrect")


def test_code__deux_requetes_simultanees_meme_code__une_seule_session(
    fabrique: sessionmaker[Session],
) -> None:
    compte = creer_compte(fabrique)
    clients = [client(fabrique), client(fabrique)]
    for c in clients:
        _connexion(c, compte.email)
    code = compte.code_totp()
    statuts: list[int] = []
    fils = [threading.Thread(target=lambda c=c: statuts.append(_code(c, code).status_code)) for c in clients]
    for f in fils:
        f.start()
    for f in fils:
        f.join()
    assert sorted(statuts) == [200, 401]
    assert sum(1 for s in _sessions(fabrique, compte) if s["etat"] == "active") == 1


def test_code__code_de_secours__accepte_une_fois_puis_refuse(fabrique: sessionmaker[Session]) -> None:
    compte = creer_compte(fabrique)
    secours = compte.codes[1].lower().replace("-", " ")
    c = client(fabrique)
    _connexion(c, compte.email)
    assert _code(c, secours).status_code == 200
    c2 = client(fabrique)
    _connexion(c2, compte.email)
    assert _code(c2, secours).status_code == 401


def test_code__cinq_codes_faux__pre_session_revoquee_essais_totp(fabrique: sessionmaker[Session]) -> None:
    compte = creer_compte(fabrique)
    c = client(fabrique, ip="10.0.0.9")
    _connexion(c, compte.email)
    for saisie in ["000000", "111111", "ABCD-EFGH-JKMN", "222222"]:
        r = _code(c, saisie)
        assert (r.status_code, r.json()["code"]) == (401, "code_incorrect")
    r = _code(c, "333333")
    assert (r.status_code, r.json()["code"], r.json()["message"]) == (
        401,
        "trop_de_codes",
        message("code.trop_de_codes"),
    )
    (pre,) = _sessions(fabrique, compte)
    assert (pre["motif_revocation"], pre["essais_totp"]) == ("essais_totp", 5)
    etapes = [
        str(t["etape"])
        for t in lignes(fabrique, TENTATIVE_CONNEXION, TENTATIVE_CONNEXION.c.etape != "mot_de_passe")
    ]
    assert sorted(etapes) == ["secours", "totp", "totp", "totp", "totp"]
    assert _code(c, compte.code_totp()).status_code == 401


def test_code__pre_session_de_plus_de_5_min__refusee_reconnexion_demandee(
    fabrique: sessionmaker[Session],
) -> None:
    compte = creer_compte(fabrique)
    c = client(fabrique)
    _connexion(c, compte.email)
    with fabrique() as s, s.begin():
        s.execute(update(SESSION).values(expire_le=func.now() - timedelta(seconds=1)))
    r = _code(c, compte.code_totp())
    assert (r.status_code, r.json()["code"], r.json()["message"]) == (
        401,
        "delai_depasse",
        message("code.delai_depasse"),
    )


def test_code__pre_session_deja_promue__refusee(fabrique: sessionmaker[Session]) -> None:
    compte = creer_compte(fabrique)
    c = client(fabrique)
    _connexion(c, compte.email)
    pre = c.cookies["lp_pre"]
    assert _code(c, compte.code_totp()).status_code == 200
    autre = client(fabrique)
    autre.cookies.set("lp_pre", pre)
    r = _code(autre, compte.code_totp(30))
    assert r.status_code == 401
    assert r.json()["code"] == "delai_depasse"


def test_code__compte_suspendu_apres_code_juste__refus_et_alerte_gerant(
    fabrique: sessionmaker[Session],
) -> None:
    compte = creer_compte(fabrique, statut="suspendu")
    c = client(fabrique)
    assert _connexion(c, compte.email).status_code == 200
    r = _code(c, compte.code_totp())
    assert (r.status_code, r.json()["code"], r.json()["message"]) == (
        403,
        "compte_suspendu",
        message("connexion.compte_suspendu"),
    )
    assert "lp_session" not in c.cookies
    (job,) = lignes(fabrique, JOB, JOB.c.type == "courriel.alerte_compte_suspendu")
    assert job["payload"]["utilisateur_id"] == str(compte.id)  # type: ignore[index]
    assert set(job["payload"]) == {"utilisateur_id", "instant"}  # type: ignore[call-overload]
    assert all(s["etat"] == "pre_totp" and s["revoquee_le"] is not None for s in _sessions(fabrique, compte))


def test_code__couple_verrouille_pendant_l_etape_code__trop_d_essais(fabrique: sessionmaker[Session]) -> None:
    compte = creer_compte(fabrique)
    c = client(fabrique)
    for _ in range(4):
        _connexion(c, compte.email, "un autre mot de passe")
    assert _connexion(c, compte.email).status_code == 200
    assert _code(c, "000000").status_code == 401
    r = _code(c, compte.code_totp())
    assert (r.status_code, r.json()["code"]) == (429, "trop_d_essais")
    assert "lp_session" not in c.cookies


def test_code__sans_pre_session__delai_depasse(fabrique: sessionmaker[Session]) -> None:
    r = client(fabrique).post("/auth/code", json={"code": "123456"})
    assert (r.status_code, r.json()["code"]) == (401, "delai_depasse")


# --- cookies, déconnexion, origine, idempotence ----------------------------------------------------


def _attributs(reponse: Any, nom: str) -> str:
    entetes = [
        v for k, v in reponse.headers.multi_items() if k.lower() == "set-cookie" and v.startswith(f"{nom}=")
    ]
    assert entetes, f"cookie {nom} absent"
    return entetes[-1].lower()


def test_cookies__httponly_secure_samesite_strict_path(fabrique: sessionmaker[Session]) -> None:
    compte = creer_compte(fabrique)
    c = client(fabrique)
    r1 = _connexion(c, compte.email)
    r2 = _code(c, compte.code_totp())
    for reponse, nom in [(r1, "lp_pre"), (r2, "lp_session"), (r2, "lp_appareil")]:
        attributs = _attributs(reponse, nom)
        for attendu in ("httponly", "secure", "samesite=strict", "path=/"):
            assert attendu in attributs, (nom, attendu)
    assert "max-age=300" in _attributs(r1, "lp_pre")
    assert "max-age=31536000" in _attributs(r2, "lp_appareil")


def test_deconnexion__session_revoquee_cookie_efface_verify_401(fabrique: sessionmaker[Session]) -> None:
    compte = creer_compte(fabrique)
    c = _connecte(fabrique, compte)
    session = c.cookies["lp_session"]
    r = c.post("/auth/deconnexion")
    assert r.status_code == 204
    assert 'lp_session=""' in _attributs(r, "lp_session") or "max-age=0" in _attributs(r, "lp_session")
    ancien = client(fabrique)
    ancien.cookies.set("lp_session", session)
    assert ancien.get("/auth/verify").status_code == 401
    active = next(s for s in _sessions(fabrique, compte) if s["etat"] == "active")
    assert active["motif_revocation"] == "deconnexion"
    assert c.post("/auth/deconnexion").status_code == 204


@pytest.mark.parametrize("route", ["/auth/connexion", "/auth/code", "/auth/deconnexion"])
def test_ecritures_auth__origine_etrangere__403(fabrique: sessionmaker[Session], route: str) -> None:
    r = client(fabrique).post(route, json={}, headers={"Origin": "https://pirate.exemple"})
    assert (r.status_code, r.json()["code"]) == (403, "forbidden_origin")
    assert client(fabrique).post("/auth/deconnexion", headers={"Origin": ORIGINE}).status_code == 204


def test_auth__aucune_cle_d_idempotence_exigee_ni_stockee(fabrique: sessionmaker[Session]) -> None:
    compte = creer_compte(fabrique)
    c = _connecte(fabrique, compte)
    c.post("/auth/deconnexion")
    assert valeur(fabrique, select(func.count()).select_from(IDEMPOTENCE)) == 0


def test_journal__connexion_reussie_echec_et_deconnexion__avec_ip(fabrique: sessionmaker[Session]) -> None:
    compte = creer_compte(fabrique)
    _connexion(client(fabrique), compte.email, "un autre mot de passe")
    c = _connecte(fabrique, compte)
    c.post("/auth/deconnexion")
    journal = lignes(fabrique, JOURNAL, JOURNAL.c.enregistrement_id == compte.id)
    assert sorted(str(j["action"]) for j in journal) == [
        "connexion.deconnexion",
        "connexion.echec",
        "connexion.reussie",
    ]
    assert all(str(j["ip"]) == IP for j in journal)
    auteurs = {j["action"]: j["utilisateur_id"] for j in journal}
    assert auteurs == {
        "connexion.echec": None,
        "connexion.reussie": compte.id,
        "connexion.deconnexion": compte.id,
    }


@pytest.mark.parametrize("entete", [None, "pas une adresse", "999.1.1.1", ""])
def test_ip__absente_ou_mal_formee__adresse_inconnue_sans_erreur(
    fabrique: sessionmaker[Session], entete: str | None
) -> None:
    """Sans X-Real-IP valable, le client de test se présente comme « testclient », pas une adresse."""
    compte = creer_compte(fabrique)
    c = TestClient(application(fabrique), base_url="https://testserver")
    entetes = {} if entete is None else {"X-Real-IP": entete}
    r = c.post(
        "/auth/connexion", json={"email": compte.email, "mot_de_passe": "faux faux faux"}, headers=entetes
    )
    assert r.status_code == 401
    (tentative,) = lignes(fabrique, TENTATIVE_CONNEXION, TENTATIVE_CONNEXION.c.utilisateur_id == compte.id)
    assert str(tentative["ip"]) == IP_INCONNUE
