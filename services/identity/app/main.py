from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import timedelta

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.auth import routeur as routeur_auth
from app.api.utilisateurs import routeur as routeur_utilisateurs
from app.api.utilisateurs import routeur_moi
from app.db import fabrique
from app.models import ETAT_WORKER, JOBS, OUTBOX
from app.securite import ClesCompte, charger_cles
from app.settings import Settings, settings
from commun.erreurs import installer_gestionnaires
from commun.identite import IdentiteMiddleware
from commun.interne import ServiceInterneMiddleware
from commun.origine import OrigineMiddleware
from commun.secrets import lire_empreintes
from commun.trace import TraceMiddleware

SEUIL_WORKER = timedelta(seconds=60)


def creer_app(
    *,
    cles_hmac: Sequence[bytes],
    empreintes: Mapping[str, bytes],
    fabrique_session: Callable[[], Session],
    reglages: Settings = settings,
    cles: ClesCompte | None = None,
) -> FastAPI:
    app = FastAPI(
        title=f"svc-{reglages.service_name}",
        docs_url=None,
        redoc_url=None,
        openapi_url="/internal/openapi.json",
    )
    installer_gestionnaires(app)
    # Du plus externe au plus interne : Trace, Origine, ServiceInterne, Identite.
    # add_middleware place le dernier ajouté à l'extérieur : ordre inverse ici.
    app.add_middleware(IdentiteMiddleware, cles=cles_hmac, prefixes_publics=reglages.prefixes_publics)
    app.add_middleware(ServiceInterneMiddleware, empreintes=empreintes)
    app.add_middleware(OrigineMiddleware, origines_autorisees=reglages.origines_autorisees)
    app.add_middleware(TraceMiddleware)

    @app.get("/internal/healthz")
    def healthz() -> JSONResponse:
        """Santé du service (TEC-OPS-06), agrégée par reporting sous /api/reporting/sante."""
        try:
            with fabrique_session() as session:
                maintenant = session.scalar(select(func.now()))
                vu_le = session.scalar(
                    select(ETAT_WORKER.c.vu_le).where(ETAT_WORKER.c.nom == reglages.service_name)
                )
                jobs_en_echec = JOBS.compter_en_echec(session)
                outbox_en_attente = session.scalar(
                    select(func.count()).select_from(OUTBOX).where(OUTBOX.c.relaye_le.is_(None))
                )
        except SQLAlchemyError:
            return JSONResponse(
                {"service": reglages.service_name, "status": "ko", "base": "ko"}, status_code=503
            )
        if vu_le is None or maintenant is None:
            worker = "absent"
        else:
            worker = "ok" if maintenant - vu_le <= SEUIL_WORKER else "en_retard"
        statut = "ok" if worker == "ok" and jobs_en_echec == 0 else "degrade"
        return JSONResponse(
            {
                "service": reglages.service_name,
                "status": statut,
                "base": "ok",
                "worker": worker,
                "jobs_en_echec": jobs_en_echec,
                "outbox_en_attente": outbox_en_attente,
            }
        )

    app.state.fabrique = fabrique_session
    app.state.cles = cles or ClesCompte(hmac=list(cles_hmac))
    app.include_router(routeur_auth)
    app.include_router(routeur_utilisateurs)
    app.include_router(routeur_moi)
    return app


def application(reglages: Settings = settings) -> FastAPI:
    """Point d'entrée uvicorn (--factory) : lit les secrets montés ; un secret absent ou trop ouvert arrête le
    démarrage (ADR 0007)."""
    dossier = reglages.secrets_dir
    cles = charger_cles(dossier)
    return creer_app(
        cles_hmac=cles.hmac,
        empreintes=lire_empreintes(dossier, reglages.service_name),
        fabrique_session=fabrique(),
        reglages=reglages,
        cles=cles,
    )
