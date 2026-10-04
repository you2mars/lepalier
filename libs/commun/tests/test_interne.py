from __future__ import annotations

from decimal import Decimal
from typing import Any

import httpx
import pytest
from fastapi import Depends, FastAPI, Request
from fastapi.testclient import TestClient
from opentelemetry.sdk.trace import TracerProvider

from commun.erreurs import ErreurApi, installer_gestionnaires
from commun.interne import (
    DELAI_SECONDES,
    ClientInterne,
    ClientInterneAsync,
    ErreurServiceInterne,
    ServiceIndisponible,
    ServiceInterneMiddleware,
    empreinte_jeton,
    exiger_service,
    service_appelant,
)
from commun.trace import TraceMiddleware

JETON_FACTURATION = "jeton-facturation-vers-documents"
EMPREINTES = {"facturation": empreinte_jeton(JETON_FACTURATION), "envois": empreinte_jeton("jeton-envois")}


def _appele() -> FastAPI:
    app = FastAPI()
    installer_gestionnaires(app)
    app.add_middleware(ServiceInterneMiddleware, empreintes=EMPREINTES)
    app.add_middleware(TraceMiddleware)

    @app.get("/internal/healthz")
    def sante() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/internal/ref/lots")
    def lots(request: Request, appelant: str = Depends(service_appelant)) -> dict[str, Any]:
        return {
            "appelant": appelant,
            "request_id": request.headers.get("x-request-id"),
            "traceparent": request.headers.get("traceparent"),
        }

    @app.post("/internal/files")
    async def deposer(request: Request) -> dict[str, Any]:
        return {"recu": await request.json()}

    @app.get("/internal/reserve", dependencies=[Depends(exiger_service("envois"))])
    def reserve() -> dict[str, str]:
        return {"ok": "oui"}

    @app.get("/internal/conflit")
    def conflit() -> None:
        raise ErreurApi(409, "deja_emis", "Ce document a déjà été émis.")

    @app.get("/lots")
    def publique() -> dict[str, str]:
        return {"ok": "oui"}

    return app


APPELE = _appele()


def _client(jeton: str = JETON_FACTURATION, appelant: str = "facturation") -> ClientInterne:
    http = TestClient(APPELE, base_url="http://documents:8000")
    return ClientInterne(appelant=appelant, url_base="http://documents:8000", jeton=jeton, client=http)


# --- côté appelé -------------------------------------------------------------------------------------


def test_middleware__healthz_libre_sans_jeton() -> None:
    assert TestClient(APPELE).get("/internal/healthz").status_code == 200


def test_middleware__routes_publiques_non_concernees() -> None:
    assert TestClient(APPELE).get("/lots").status_code == 200


@pytest.mark.parametrize(
    "entetes",
    [
        {},
        {"X-Service-Appelant": "facturation"},
        {"X-Service-Appelant": "facturation", "Authorization": "Bearer mauvais"},
        {"X-Service-Appelant": "envois", "Authorization": f"Bearer {JETON_FACTURATION}"},
        {"X-Service-Appelant": "inconnu", "Authorization": f"Bearer {JETON_FACTURATION}"},
        {"X-Service-Appelant": "facturation", "Authorization": JETON_FACTURATION},
    ],
)
def test_middleware__jeton_absent_faux_ou_d_un_autre_service__401(entetes: dict[str, str]) -> None:
    r = TestClient(APPELE).get("/internal/ref/lots", headers=entetes)
    assert r.status_code == 401
    assert r.json()["code"] == "service_non_authentifie"


def test_service_appelant__sans_middleware__refus_par_defaut() -> None:
    app = FastAPI()
    installer_gestionnaires(app)

    @app.get("/internal/ref")
    def ref(appelant: str = Depends(service_appelant)) -> dict[str, str]:
        return {"appelant": appelant}

    assert TestClient(app).get("/internal/ref").status_code == 401


# --- client synchrone ----------------------------------------------------------------------------------


def test_client__lecture__jeton_appelant_et_request_id_transmis() -> None:
    corps = _client().get("/internal/ref/lots")
    assert corps["appelant"] == "facturation"
    assert len(corps["request_id"]) == 32


def test_client__trace_otel_propagee_par_traceparent() -> None:
    traceur = TracerProvider().get_tracer("essai")
    with traceur.start_as_current_span("appel") as span:
        attendu = format(span.get_span_context().trace_id, "032x")
        corps = _client().get("/internal/ref/lots")
    assert corps["request_id"] == attendu
    assert attendu in corps["traceparent"]


def test_client__ecriture__montants_decimaux_en_chaines() -> None:
    corps = _client().post("/internal/files", {"montant": Decimal("650.00"), "nom": "bail.pdf"})
    assert corps == {"recu": {"montant": "650.00", "nom": "bail.pdf"}}


@pytest.mark.parametrize(
    "chemin", ["/lots", "/api/documents/files", "internal/ref", "http://autre/internal/x"]
)
def test_client__chemin_hors_internal__refuse_avant_tout_appel(chemin: str) -> None:
    with pytest.raises(ValueError, match="/internal/"):
        _client().get(chemin)


def test_client__jeton_refuse__erreur_service_interne_401() -> None:
    with pytest.raises(ErreurServiceInterne) as exc:
        _client(jeton="mauvais").get("/internal/ref/lots")
    assert exc.value.statut == 401
    assert exc.value.code == "service_non_authentifie"


def test_client__service_non_autorise_pour_la_ressource__403() -> None:
    with pytest.raises(ErreurServiceInterne) as exc:
        _client().get("/internal/reserve")
    assert exc.value.statut == 403
    assert exc.value.code == "service_non_autorise"


def test_client__service_autorise_pour_la_ressource__200() -> None:
    assert _client(jeton="jeton-envois", appelant="envois").get("/internal/reserve") == {"ok": "oui"}


def test_client__erreur_metier_de_l_appele__transmise() -> None:
    with pytest.raises(ErreurServiceInterne) as exc:
        _client().get("/internal/conflit")
    assert (exc.value.statut, exc.value.code, exc.value.message) == (
        409,
        "deja_emis",
        "Ce document a déjà été émis.",
    )


def _client_en_panne(reponse: httpx.Response | None = None) -> tuple[ClientInterne, list[str]]:
    appels: list[str] = []

    def gerer(requete: httpx.Request) -> httpx.Response:
        appels.append(requete.method)
        if reponse is None:
            raise httpx.ConnectTimeout("délai dépassé", request=requete)
        return reponse

    http = httpx.Client(transport=httpx.MockTransport(gerer), base_url="http://documents:8000")
    client = ClientInterne(appelant="facturation", url_base="http://documents:8000", jeton="j", client=http)
    return client, appels


def test_client__lecture_injoignable__une_seule_nouvelle_tentative_puis_indisponible() -> None:
    client, appels = _client_en_panne()
    with pytest.raises(ServiceIndisponible):
        client.get("/internal/ref/lots")
    assert appels == ["GET", "GET"]


def test_client__ecriture_injoignable__aucune_nouvelle_tentative() -> None:
    client, appels = _client_en_panne()
    with pytest.raises(ServiceIndisponible) as exc:
        client.post("/internal/files", {"nom": "bail.pdf"})
    assert appels == ["POST"]
    assert exc.value.statut == 503


@pytest.mark.parametrize("statut", [502, 503, 504])
def test_client__appele_indisponible__service_indisponible(statut: int) -> None:
    client, appels = _client_en_panne(httpx.Response(statut, text="Bad Gateway"))
    with pytest.raises(ServiceIndisponible):
        client.get("/internal/ref/lots")
    assert appels == ["GET"]


def test_client__reponse_d_erreur_illisible__code_generique() -> None:
    client, _ = _client_en_panne(httpx.Response(500, text="<html>"))
    with pytest.raises(ErreurServiceInterne) as exc:
        client.get("/internal/ref/lots")
    assert (exc.value.statut, exc.value.code) == (500, "erreur_interne")


def test_client__reponse_vide__none() -> None:
    client, _ = _client_en_panne(httpx.Response(204))
    assert client.post("/internal/files", {}) is None


def test_client__delai_par_defaut_5_secondes() -> None:
    client = ClientInterne(appelant="facturation", url_base="http://documents:8000", jeton="j")
    assert DELAI_SECONDES == 5.0
    assert client.http.timeout == httpx.Timeout(5.0)
    client.fermer()


# --- client asynchrone --------------------------------------------------------------------------------


def _client_async(transport: httpx.AsyncBaseTransport | None = None) -> ClientInterneAsync:
    http = httpx.AsyncClient(
        transport=transport or httpx.ASGITransport(app=APPELE), base_url="http://documents:8000"
    )
    return ClientInterneAsync(
        appelant="facturation", url_base="http://documents:8000", jeton=JETON_FACTURATION, client=http
    )


async def test_client_async__lecture_et_ecriture() -> None:
    client = _client_async()
    assert (await client.get("/internal/ref/lots"))["appelant"] == "facturation"
    assert await client.post("/internal/files", {"montant": Decimal("1.50")}) == {"recu": {"montant": "1.50"}}
    await client.fermer()


async def test_client_async__ecriture_injoignable__aucune_nouvelle_tentative() -> None:
    appels: list[str] = []

    def gerer(requete: httpx.Request) -> httpx.Response:
        appels.append(requete.method)
        raise httpx.ConnectError("refusé", request=requete)

    client = _client_async(httpx.MockTransport(gerer))
    with pytest.raises(ServiceIndisponible):
        await client.post("/internal/files", {})
    with pytest.raises(ServiceIndisponible):
        await client.get("/internal/ref/lots")
    assert appels == ["POST", "GET", "GET"]
    with pytest.raises(ValueError, match="/internal/"):
        await client.get("/lots")
