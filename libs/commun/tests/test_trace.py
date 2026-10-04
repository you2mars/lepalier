from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from opentelemetry.sdk.trace import TracerProvider

from commun.enveloppe import nouvelle_enveloppe
from commun.erreurs import ErreurApi, installer_gestionnaires
from commun.identite import IdentiteMiddleware
from commun.ids import uuid7
from commun.trace import TraceMiddleware, trace_id_courant


def _app() -> FastAPI:
    app = FastAPI()
    installer_gestionnaires(app)
    app.add_middleware(IdentiteMiddleware, cles=[b"k" * 32], prefixes_publics=("/internal/", "/public/"))
    app.add_middleware(TraceMiddleware)

    @app.get("/public/evenement")
    def evenement() -> dict[str, str]:
        env = nouvelle_enveloppe(
            type="utilisateur.cree", version=1, producer="identity", aggregate_id=uuid7(), payload={}
        )
        return {"trace_id": env.trace_id}

    @app.get("/public/erreur")
    def erreur() -> None:
        raise ErreurApi(409, "conflit", "Déjà enregistré.")

    return app


CLIENT = TestClient(_app())


def test_trace_middleware__x_request_id_valide__repris_et_sert_de_trace() -> None:
    r = CLIENT.get("/public/evenement", headers={"X-Request-Id": "abc-123"})
    assert r.headers["X-Request-Id"] == "abc-123"
    assert r.headers["X-Trace-Id"] == "abc-123"


def test_trace_middleware__sans_x_request_id__identifiant_genere() -> None:
    r = CLIENT.get("/public/evenement")
    assert len(r.headers["X-Request-Id"]) == 32
    assert r.headers["X-Trace-Id"] == r.headers["X-Request-Id"]


@pytest.mark.parametrize("valeur", [b"a b", b"x" * 129, "é".encode("latin-1"), b"a;b"])
def test_trace_middleware__x_request_id_douteux__remplace(valeur: bytes) -> None:
    r = CLIENT.get("/public/evenement", headers={"X-Request-Id": valeur})
    assert r.headers["X-Request-Id"].encode("latin-1") != valeur
    assert len(r.headers["X-Request-Id"]) == 32


def test_trace_middleware__cycle_de_vie_non_http__transmis() -> None:
    with TestClient(_app()) as client:
        assert client.get("/public/evenement").status_code == 200


def test_trace_middleware__evenement_cree_dans_une_route_synchrone__meme_trace() -> None:
    r = CLIENT.get("/public/evenement", headers={"X-Request-Id": "req-42"})
    assert r.json()["trace_id"] == "req-42"


def test_trace_middleware__corps_d_erreur_et_en_tete__meme_trace() -> None:
    r = CLIENT.get("/public/erreur", headers={"X-Request-Id": "req-409"})
    assert r.status_code == 409
    assert r.json()["trace_id"] == r.headers["X-Trace-Id"] == "req-409"


def test_trace_middleware__refus_d_un_autre_middleware__en_tetes_presents() -> None:
    r = CLIENT.get("/lots", headers={"X-Request-Id": "req-401"})
    assert r.status_code == 401
    assert r.headers["X-Request-Id"] == "req-401"
    assert r.json()["trace_id"] == r.headers["X-Trace-Id"] == "req-401"


def test_trace_middleware__route_inconnue__en_tetes_presents() -> None:
    r = CLIENT.get("/internal/inconnue")
    assert r.status_code == 404
    assert r.json()["trace_id"] == r.headers["X-Trace-Id"]


def test_trace_middleware__aucune_fuite_de_trace_apres_la_requete() -> None:
    CLIENT.get("/public/evenement", headers={"X-Request-Id": "req-fuite"})
    assert trace_id_courant() != "req-fuite"


def test_trace_middleware__trace_otel_active__prioritaire_sur_x_request_id() -> None:
    traceur = TracerProvider().get_tracer("essai")
    with traceur.start_as_current_span("requete") as span:
        attendu = format(span.get_span_context().trace_id, "032x")
        r = CLIENT.get("/public/evenement", headers={"X-Request-Id": "req-otel"})
    assert r.headers["X-Request-Id"] == "req-otel"
    assert r.headers["X-Trace-Id"] == attendu
