import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from commun.origine import OrigineMiddleware

ORIGINE = "https://192.168.1.20"


def _app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(OrigineMiddleware, origines_autorisees=[ORIGINE])

    @app.get("/lots")
    def lire() -> dict[str, str]:
        return {"ok": "oui"}

    @app.post("/lots")
    def creer() -> dict[str, str]:
        return {"ok": "oui"}

    @app.post("/internal/ref")
    def interne() -> dict[str, str]:
        return {"ok": "oui"}

    return app


CLIENT = TestClient(_app())


@pytest.mark.parametrize(
    "entetes",
    [
        {},
        {"Origin": ORIGINE},
        {"Origin": ORIGINE, "Sec-Fetch-Site": "same-origin"},
        {"Sec-Fetch-Site": "none"},
    ],
)
def test_ecriture__meme_origine_ou_hors_navigateur__acceptee(entetes: dict[str, str]) -> None:
    assert CLIENT.post("/lots", headers=entetes).status_code == 200


@pytest.mark.parametrize(
    "entetes",
    [
        {"Origin": "https://pirate.example"},
        {"Origin": "null"},
        {"Sec-Fetch-Site": "cross-site"},
        {"Origin": ORIGINE, "Sec-Fetch-Site": "same-site"},
    ],
)
def test_ecriture__autre_origine__refusee(entetes: dict[str, str]) -> None:
    r = CLIENT.post("/lots", headers=entetes)
    assert r.status_code == 403
    corps = r.json()
    assert corps["code"] == "forbidden_origin"
    assert (
        corps["message"]
        == "Cette demande ne vient pas de LePalier et a été refusée. Rechargez la page puis réessayez."
    )


def test_lecture__autre_origine__non_concernee() -> None:
    assert CLIENT.get("/lots", headers={"Origin": "https://pirate.example"}).status_code == 200


def test_routes_internes__exemptees() -> None:
    assert CLIENT.post("/internal/ref", headers={"Origin": "https://pirate.example"}).status_code == 200
