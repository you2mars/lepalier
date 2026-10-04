import json
from pathlib import Path
from typing import get_args

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from hypothesis import given
from hypothesis import strategies as st

from commun.erreurs import installer_gestionnaires
from commun.identite import (
    Identite,
    IdentiteInvalide,
    IdentiteMiddleware,
    Role,
    entetes_signes,
    exiger_role,
    identite_courante,
    signer,
    verifier,
)
from commun.ids import uuid7

CLE = b"k" * 32
ANCIENNE_CLE = b"o" * 32
MAINTENANT = 1_800_000_000
UTILISATEUR = uuid7()


def _entetes(role: Role = "gerant", exp: int = MAINTENANT + 60, cle: bytes = CLE) -> dict[str, str]:
    return entetes_signes(UTILISATEUR, role, exp, cle)


def test_roles__identiques_au_contrat() -> None:
    enums = json.loads((Path(__file__).resolve().parents[3] / "contracts" / "enums.json").read_text())
    assert list(get_args(Role)) == enums["role"]


def test_verifier__aller_retour() -> None:
    assert verifier(_entetes(), [CLE], MAINTENANT) == Identite(UTILISATEUR, "gerant", MAINTENANT + 60)


def test_verifier__casse_des_entetes_indifferente() -> None:
    entetes = {nom.upper(): valeur for nom, valeur in _entetes().items()}
    assert verifier(entetes, [CLE], MAINTENANT).role == "gerant"


def test_verifier__rotation_de_cle() -> None:
    entetes = _entetes(cle=ANCIENNE_CLE)
    assert verifier(entetes, [CLE, ANCIENNE_CLE], MAINTENANT).user_id == UTILISATEUR
    with pytest.raises(IdentiteInvalide):
        verifier(entetes, [CLE], MAINTENANT)


def _alterer(entetes: dict[str, str], nom: str) -> dict[str, str]:
    valeur = entetes[nom]
    nouvelles = {
        "X-User-Id": str(uuid7()),
        "X-Role": "associe" if valeur == "gerant" else "gerant",
        "X-Auth-Exp": str(int(valeur) + 1) if nom == "X-Auth-Exp" else valeur,
        "X-Auth-Sig": valeur[:-1] + ("0" if valeur[-1] != "0" else "1"),
    }
    return {**entetes, nom: nouvelles[nom]}


@given(
    st.sampled_from(["X-User-Id", "X-Role", "X-Auth-Exp", "X-Auth-Sig"]),
    st.sampled_from(["gerant", "associe"]),
)
def test_verifier__toute_alteration_refusee(nom: str, role: Role) -> None:
    with pytest.raises(IdentiteInvalide):
        verifier(_alterer(_entetes(role=role), nom), [CLE], MAINTENANT)


@pytest.mark.parametrize("manquant", ["X-User-Id", "X-Role", "X-Auth-Exp", "X-Auth-Sig"])
def test_verifier__entete_manquant(manquant: str) -> None:
    entetes = _entetes()
    del entetes[manquant]
    with pytest.raises(IdentiteInvalide):
        verifier(entetes, [CLE], MAINTENANT)


@pytest.mark.parametrize("exp", [MAINTENANT - 1, MAINTENANT, MAINTENANT + 3601])
def test_verifier__expiration_passee_ou_trop_lointaine(exp: int) -> None:
    with pytest.raises(IdentiteInvalide):
        verifier(_entetes(exp=exp), [CLE], MAINTENANT)


def test_verifier__role_inconnu_meme_bien_signe() -> None:
    exp = MAINTENANT + 60
    entetes = {
        "X-User-Id": str(UTILISATEUR),
        "X-Role": "admin",
        "X-Auth-Exp": str(exp),
        "X-Auth-Sig": signer(UTILISATEUR, "admin", exp, CLE),
    }
    with pytest.raises(IdentiteInvalide):
        verifier(entetes, [CLE], MAINTENANT)


def test_verifier__expiration_mal_formee() -> None:
    with pytest.raises(IdentiteInvalide):
        verifier({**_entetes(), "X-Auth-Exp": "demain"}, [CLE], MAINTENANT)


def test_verifier__identifiant_mal_forme_meme_bien_signe() -> None:
    exp = MAINTENANT + 60
    entetes = {
        "X-User-Id": "pas-un-uuid",
        "X-Role": "gerant",
        "X-Auth-Exp": str(exp),
        "X-Auth-Sig": signer("pas-un-uuid", "gerant", exp, CLE),
    }
    with pytest.raises(IdentiteInvalide, match="identifiant"):
        verifier(entetes, [CLE], MAINTENANT)


def test_verifier__aucune_cle_configuree() -> None:
    with pytest.raises(IdentiteInvalide):
        verifier(_entetes(), [], MAINTENANT)


def _app() -> FastAPI:
    app = FastAPI()
    installer_gestionnaires(app)
    app.add_middleware(IdentiteMiddleware, cles=[CLE], horloge=lambda: MAINTENANT)

    @app.get("/internal/healthz")
    def sante() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/lots")
    def lire(identite: Identite = Depends(identite_courante)) -> dict[str, str]:  # noqa: B008
        return {"role": identite.role, "user_id": str(identite.user_id)}

    @app.post("/lots", dependencies=[Depends(exiger_role("gerant"))])
    def creer() -> dict[str, str]:
        return {"ok": "oui"}

    @app.post("/paiements", dependencies=[Depends(exiger_role("gerant", "operateur"))])
    def payer() -> dict[str, str]:
        return {"ok": "oui"}

    return app


CLIENT = TestClient(_app())


def test_middleware__routes_internes_sans_identite() -> None:
    assert CLIENT.get("/internal/healthz").status_code == 200


def test_middleware__sans_entetes__401_format_commun() -> None:
    r = CLIENT.get("/lots")
    assert r.status_code == 401
    corps = r.json()
    assert corps["code"] == "unauthenticated"
    assert corps["message"] == "Votre session a expiré ou n'est pas reconnue. Reconnectez-vous."
    assert corps["details"] == {}
    assert corps["trace_id"]


def test_middleware__entetes_forges_sans_signature__401() -> None:
    r = CLIENT.get("/lots", headers={"X-User-Id": str(UTILISATEUR), "X-Role": "gerant"})
    assert r.status_code == 401


def test_middleware__identite_valide_transmise_a_la_route() -> None:
    r = CLIENT.get("/lots", headers=_entetes(role="associe"))
    assert r.status_code == 200
    assert r.json() == {"role": "associe", "user_id": str(UTILISATEUR)}


MATRICE = [
    ("/lots", "gerant", 200),
    ("/lots", "associe", 403),
    ("/lots", "operateur", 403),
    ("/paiements", "gerant", 200),
    ("/paiements", "associe", 403),
    ("/paiements", "operateur", 200),
]


@pytest.mark.parametrize(("route", "role", "statut"), MATRICE)
def test_exiger_role__matrice(route: str, role: Role, statut: int) -> None:
    assert CLIENT.post(route, headers=_entetes(role=role)).status_code == statut


@pytest.mark.parametrize(
    ("route", "message"),
    [
        ("/lots", "Cette action est réservée au gérant."),
        ("/paiements", "Cette action est réservée au gérant ou à l'opérateur."),
    ],
)
def test_exiger_role__message_explicite(route: str, message: str) -> None:
    corps = CLIENT.post(route, headers=_entetes(role="associe")).json()
    assert corps["code"] == "forbidden"
    assert corps["message"] == message


def test_identite_courante__sans_middleware__refus_par_defaut() -> None:
    app = FastAPI()
    installer_gestionnaires(app)

    @app.get("/lots")
    def lire(identite: Identite = Depends(identite_courante)) -> dict[str, str]:  # noqa: B008
        return {"role": identite.role}

    r = TestClient(app).get("/lots", headers=_entetes())
    assert r.status_code == 401
    assert r.json()["code"] == "unauthenticated"
