from __future__ import annotations

import hashlib
import time
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, insert
from sqlalchemy.orm import Session, sessionmaker

from app.db import url_base
from app.main import application, creer_app
from app.models import ETAT_WORKER, JOB, JOBS, OUTBOX_SVC
from app.settings import Settings
from commun.enveloppe import nouvelle_enveloppe
from commun.identite import entetes_signes
from commun.ids import uuid7
from commun.secrets import SecretInvalide

CLE = b"k" * 32
JETON = "jeton-essai-facturation"
ORIGINE = "https://lepalier.essai"
REGLAGES = Settings(service_name="essai", origines_autorisees=[ORIGINE])


def _app(fabrique: sessionmaker[Session]) -> FastAPI:
    app = creer_app(
        cles_hmac=[CLE],
        empreintes={"facturation": hashlib.sha256(JETON.encode()).digest()},
        fabrique_session=fabrique,
        reglages=REGLAGES,
    )

    @app.get("/essai")
    def lire() -> dict[str, str]:
        return {"ok": "oui"}

    @app.post("/essai")
    def ecrire() -> dict[str, str]:
        return {"ok": "oui"}

    @app.get("/internal/ref/essai")
    def interne() -> dict[str, str]:
        return {"ok": "oui"}

    return app


def _identite() -> dict[str, str]:
    return entetes_signes(uuid7(), "gerant", int(time.time()) + 60, CLE)


# --- middlewares câblés dans le bon ordre ------------------------------------------------------------


@pytest.mark.integration
def test_app__route_metier__identite_exigee(fabrique: sessionmaker[Session]) -> None:
    client = TestClient(_app(fabrique))
    refus = client.get("/essai", headers={"X-Request-Id": "req-1"})
    assert refus.status_code == 401
    assert refus.headers["X-Trace-Id"] == refus.json()["trace_id"] == "req-1"
    assert client.get("/essai", headers=_identite()).status_code == 200


@pytest.mark.integration
def test_app__route_interne__jeton_de_service_exige_identite_utilisateur_inutile(
    fabrique: sessionmaker[Session],
) -> None:
    client = TestClient(_app(fabrique))
    assert client.get("/internal/ref/essai").status_code == 401
    jeton = {"X-Service-Appelant": "facturation", "Authorization": f"Bearer {JETON}"}
    assert client.get("/internal/ref/essai", headers=jeton).status_code == 200


@pytest.mark.integration
def test_app__ecriture_d_une_autre_origine__refusee(fabrique: sessionmaker[Session]) -> None:
    client = TestClient(_app(fabrique))
    assert (
        client.post("/essai", headers={**_identite(), "Origin": "https://pirate.exemple"}).status_code == 403
    )
    assert client.post("/essai", headers={**_identite(), "Origin": ORIGINE}).status_code == 200


# --- santé (TEC-OPS-06) -------------------------------------------------------------------------------


@pytest.mark.integration
def test_healthz__sans_secret_ni_identite__worker_absent__degrade(fabrique: sessionmaker[Session]) -> None:
    r = TestClient(_app(fabrique)).get("/internal/healthz")
    assert r.status_code == 200
    assert r.json() == {
        "service": "essai",
        "status": "degrade",
        "base": "ok",
        "worker": "absent",
        "jobs_en_echec": 0,
        "outbox_en_attente": 0,
    }
    assert "X-Request-Id" in r.headers


@pytest.mark.integration
def test_healthz__worker_recent_rien_en_echec__ok(fabrique: sessionmaker[Session]) -> None:
    with fabrique() as s, s.begin():
        s.execute(insert(ETAT_WORKER).values(nom="essai", vu_le=func.now()))
        OUTBOX_SVC.ajouter(
            s,
            nouvelle_enveloppe(
                type="essai.cree", version=1, producer="identity", aggregate_id=uuid7(), payload={}
            ),
        )
    corps = TestClient(_app(fabrique)).get("/internal/healthz").json()
    assert (corps["status"], corps["worker"], corps["outbox_en_attente"]) == ("ok", "ok", 1)


@pytest.mark.integration
def test_healthz__worker_muet_depuis_plus_d_une_minute__en_retard(fabrique: sessionmaker[Session]) -> None:
    with fabrique() as s, s.begin():
        s.execute(
            insert(ETAT_WORKER).values(nom="essai", vu_le=func.now() - func.make_interval(0, 0, 0, 0, 0, 2))
        )
    corps = TestClient(_app(fabrique)).get("/internal/healthz").json()
    assert (corps["status"], corps["worker"]) == ("degrade", "en_retard")


@pytest.mark.integration
def test_healthz__job_en_echec__degrade(fabrique: sessionmaker[Session]) -> None:
    with fabrique() as s, s.begin():
        s.execute(insert(ETAT_WORKER).values(nom="essai", vu_le=func.now()))
        s.execute(insert(JOB).values(id=uuid7(), type="essai.x", cle="1", statut="echec"))
    corps = TestClient(_app(fabrique)).get("/internal/healthz").json()
    assert (corps["status"], corps["jobs_en_echec"]) == ("degrade", 1)
    with fabrique() as s:
        assert JOBS.compter_en_echec(s) == 1


def test_healthz__base_injoignable__503() -> None:
    injoignable = sessionmaker(
        create_engine("postgresql+psycopg://x:y@127.0.0.1:1/z", connect_args={"connect_timeout": 1})
    )
    r = TestClient(_app(injoignable)).get("/internal/healthz")
    assert r.status_code == 503
    assert r.json() == {"service": "essai", "status": "ko", "base": "ko"}


# --- démarrage à partir des secrets montés (ADR 0007) -------------------------------------------------


def _secret(dossier: Path, nom: str, contenu: str, mode: int = 0o400) -> None:
    chemin = dossier / nom
    chemin.write_text(contenu)
    chemin.chmod(mode)


def test_application__secrets_montes__demarre(tmp_path: Path) -> None:
    _secret(tmp_path, "cle_hmac_identite", "ab" * 32)
    _secret(tmp_path, "empreinte_facturation_vers_essai", hashlib.sha256(JETON.encode()).hexdigest())
    _secret(tmp_path, "cle_chiffrement_identity", "1 " + "cd" * 32)
    _secret(tmp_path, "cle_pseudonymisation_identity", "ef" * 32)
    app = application(Settings(service_name="essai", secrets_dir=tmp_path))
    assert isinstance(app, FastAPI)


@pytest.mark.parametrize(
    ("nom", "contenu"),
    [
        ("cle_chiffrement_identity", None),
        ("cle_pseudonymisation_identity", None),
        ("cle_pseudonymisation_identity", "zz"),
        ("cle_pseudonymisation_identity", "ab" * 16),
    ],
)
def test_application__cle_d_identity_absente_ou_illisible__refus_de_demarrer(
    tmp_path: Path, nom: str, contenu: str | None
) -> None:
    _secret(tmp_path, "cle_hmac_identite", "ab" * 32)
    _secret(tmp_path, "cle_chiffrement_identity", "1 " + "cd" * 32)
    _secret(tmp_path, "cle_pseudonymisation_identity", "ef" * 32)
    if contenu is None:
        (tmp_path / nom).unlink()
    else:
        (tmp_path / nom).chmod(0o600)
        (tmp_path / nom).write_text(contenu)
    with pytest.raises(SecretInvalide):
        application(Settings(service_name="essai", secrets_dir=tmp_path))


def test_application__cle_hmac_absente__refus_de_demarrer(tmp_path: Path) -> None:
    with pytest.raises(SecretInvalide, match="introuvable"):
        application(Settings(service_name="essai", secrets_dir=tmp_path))


def test_application__secret_lisible_par_le_groupe__refus_de_demarrer(tmp_path: Path) -> None:
    _secret(tmp_path, "cle_hmac_identite", "ab" * 32, mode=0o440)
    with pytest.raises(SecretInvalide, match="ADR 0007"):
        application(Settings(service_name="essai", secrets_dir=tmp_path))


def test_url_base__mot_de_passe_lu_dans_le_secret_mdp_base(tmp_path: Path) -> None:
    reglages = Settings(
        database_url="postgresql+psycopg://svc_essai@postgres:5432/essai", secrets_dir=tmp_path
    )
    assert url_base(reglages).password is None
    _secret(tmp_path, "mdp_base", "mdp-du-secret\n")
    url = url_base(reglages)
    assert url.password == "mdp-du-secret"
    assert "mdp-du-secret" not in str(url)
