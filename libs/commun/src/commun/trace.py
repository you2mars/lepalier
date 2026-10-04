"""Identifiant de trace propagé dans les réponses et les événements (TEC-API-06, TEC-JOB-08)."""

from __future__ import annotations

from opentelemetry import trace

from commun.ids import uuid7


def trace_id_otel() -> str | None:
    """trace_id de la trace OpenTelemetry active (32 caractères hexadécimaux), sinon None."""
    contexte = trace.get_current_span().get_span_context()
    if contexte.is_valid:
        return format(contexte.trace_id, "032x")
    return None


def trace_id_courant(repli: str | None = None) -> str:
    """trace_id actif, sinon `repli` (ex. X-Request-Id), sinon un nouvel identifiant."""
    return trace_id_otel() or repli or uuid7().hex
