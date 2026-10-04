from __future__ import annotations

from fastapi import FastAPI

from app.settings import settings

app = FastAPI(title=f"svc-{settings.service_name}", docs_url=None, redoc_url=None, openapi_url="/internal/openapi.json")


@app.get("/internal/healthz")
def healthz() -> dict[str, str]:
    """Santé minimale (TEC-OPS-06) : complétée au lot 0 avec base, NATS, worker, dernier tick."""
    return {"service": settings.service_name, "status": "ok"}
