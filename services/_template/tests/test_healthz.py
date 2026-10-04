from fastapi.testclient import TestClient

from app.main import app


def test_healthz__sans_dependance__repond_ok() -> None:
    client = TestClient(app)
    r = client.get("/internal/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
