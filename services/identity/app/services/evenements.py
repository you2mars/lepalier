"""Événements `utilisateur.*` v1 (contrats dans contracts/events/utilisateur) écrits dans l'outbox."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import OUTBOX_SVC
from commun.enveloppe import Enveloppe
from commun.ids import uuid7
from commun.trace import trace_id_courant


def publier(s: Session, fait: str, u: Any, par: UUID | None, instant: datetime, **autres: Any) -> None:
    """`u` : ligne utilisateur après l'action ; jamais d'adresse e-mail ni de secret dans le payload."""
    OUTBOX_SVC.ajouter(
        s,
        Enveloppe(
            id=uuid7(),
            type=f"utilisateur.{fait}",
            version=1,
            occurred_at=instant,
            producer="identity",
            aggregate_id=u["id"],
            trace_id=trace_id_courant(),
            payload={
                "utilisateur_id": u["id"],
                "role": u["role"],
                "associe_id": u["associe_id"],
                "nom_affiche": u["nom_affiche"],
                **autres,
                "par_utilisateur_id": par,
            },
        ),
    )
