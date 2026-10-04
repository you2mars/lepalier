"""Identifiant de trace propagé dans les réponses et les événements (TEC-API-06, TEC-JOB-08).

`TraceMiddleware` (le plus externe) adopte le `X-Request-Id` posé par nginx, s'il est sain, et ajoute
`X-Request-Id` et `X-Trace-Id` à chaque réponse, y compris les refus des autres middlewares. Le `trace_id`
de la requête est porté par une variable de contexte : les événements créés pendant la requête en héritent.
"""

from __future__ import annotations

import re
from contextvars import ContextVar

from opentelemetry import trace
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from commun.ids import uuid7

_TRACE_REQUETE: ContextVar[str | None] = ContextVar("trace_requete", default=None)
_REQUEST_ID_SAIN = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


def trace_id_otel() -> str | None:
    """trace_id de la trace OpenTelemetry active (32 caractères hexadécimaux), sinon None."""
    contexte = trace.get_current_span().get_span_context()
    if contexte.is_valid:
        return format(contexte.trace_id, "032x")
    return None


def trace_id_courant(repli: str | None = None) -> str:
    """trace_id actif (OpenTelemetry, sinon requête en cours), sinon `repli`, sinon un nouvel identifiant."""
    return trace_id_otel() or _TRACE_REQUETE.get() or repli or uuid7().hex


class TraceMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        recu = next((v.decode("latin-1") for n, v in scope["headers"] if n == b"x-request-id"), "")
        request_id = recu if _REQUEST_ID_SAIN.fullmatch(recu) else uuid7().hex
        trace_id = trace_id_otel() or request_id
        etat = scope.setdefault("state", {})
        etat["request_id"], etat["trace_id"] = request_id, trace_id

        async def envoyer(message: Message) -> None:
            if message["type"] == "http.response.start":
                entetes = MutableHeaders(scope=message)
                entetes["X-Request-Id"] = request_id
                entetes["X-Trace-Id"] = trace_id
            await send(message)

        jeton = _TRACE_REQUETE.set(trace_id)
        try:
            await self.app(scope, receive, envoyer)
        finally:
            _TRACE_REQUETE.reset(jeton)
