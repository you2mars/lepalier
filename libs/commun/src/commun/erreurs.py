"""Format d'erreur commun à tous les services (TEC-API-03) : {code, message, details, trace_id}.

Les messages sont en français clair (UX-5) : ils peuvent être affichés tels quels par le front.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import Scope

from commun.trace import trace_id_courant

MESSAGE_INTERNE = "Une erreur inattendue est survenue. Réessayez dans quelques instants."
MESSAGE_VALIDATION = "Certaines informations sont incorrectes. Corrigez les champs signalés."

_HTTP: dict[int, tuple[str, str]] = {
    401: ("unauthenticated", "Votre session a expiré ou n'est pas reconnue. Reconnectez-vous."),
    403: ("forbidden", "Votre rôle ne permet pas cette action."),
    404: ("not_found", "Cette page ou cette information n'existe pas."),
    405: ("method_not_allowed", "Cette opération n'est pas possible ici."),
}

_VALIDATION: dict[str, str] = {
    "missing": "Ce champ est obligatoire.",
    "extra_forbidden": "Ce champ n'est pas attendu.",
    "string_too_short": "Ce champ ne peut pas être vide.",
    "json_invalid": "Les informations envoyées sont illisibles.",
}


class ErreurApi(Exception):
    """Erreur prévue, renvoyée telle quelle au client avec son statut HTTP."""

    def __init__(self, statut: int, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.statut = statut
        self.code = code
        self.message = message
        self.details = details or {}


def trace_id_de(scope: Scope) -> str:
    """trace_id de la requête : trace OpenTelemetry active, sinon X-Request-Id posé par nginx."""
    for nom, valeur in scope.get("headers", []):
        if nom == b"x-request-id":
            return trace_id_courant(valeur.decode("latin-1"))
    return trace_id_courant()


def reponse_erreur(
    scope: Scope, statut: int, code: str, message: str, details: dict[str, Any] | None = None
) -> JSONResponse:
    corps = {"code": code, "message": message, "details": details or {}, "trace_id": trace_id_de(scope)}
    return JSONResponse(corps, status_code=statut)


def _message_validation(erreur: dict[str, Any]) -> str:
    if erreur["type"] == "value_error":
        cause = erreur.get("ctx", {}).get("error")
        if cause is not None:
            return str(cause)
    return _VALIDATION.get(erreur["type"], "Cette valeur n'est pas valide.")


def _champ(erreur: dict[str, Any]) -> str:
    chemin = [str(p) for p in erreur.get("loc", ()) if p not in ("body", "query", "path", "header")]
    return ".".join(chemin) or "corps"


def installer_gestionnaires(app: FastAPI) -> None:
    """Branche le format commun sur les erreurs prévues, de validation, HTTP et inattendues."""

    @app.exception_handler(ErreurApi)
    async def _erreur_api(request: Request, exc: ErreurApi) -> JSONResponse:
        return reponse_erreur(request.scope, exc.statut, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        champs = [{"champ": _champ(e), "message": _message_validation(e)} for e in exc.errors()]
        return reponse_erreur(request.scope, 422, "invalid", MESSAGE_VALIDATION, {"champs": champs})

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code, message = _HTTP.get(exc.status_code, ("http_error", MESSAGE_INTERNE))
        return reponse_erreur(request.scope, exc.status_code, code, message)

    @app.exception_handler(Exception)
    async def _inattendue(request: Request, exc: Exception) -> JSONResponse:
        return reponse_erreur(request.scope, 500, "internal", MESSAGE_INTERNE)
