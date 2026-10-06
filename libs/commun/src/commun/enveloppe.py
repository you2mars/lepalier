"""Enveloppe d'événement commune (TEC-JOB-08) ; contrat : contracts/enveloppe.schema.json."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from commun.decimales import en_chaine
from commun.ids import uuid7
from commun.trace import trace_id_courant

Producteur = Literal[
    "identity", "referentiel", "facturation", "charges-eau", "documents", "envois", "veille", "reporting"
]


def normaliser_json(valeur: Any, chemin: str = "payload") -> Any:
    """Rend le payload sérialisable sans perte : Decimal en chaîne à 2 décimales, dates ISO, UUID en texte."""
    if isinstance(valeur, float):
        raise ValueError(f"{chemin} : nombre flottant refusé (TEC-STK-03), utilisez Decimal")
    if isinstance(valeur, Decimal):
        return en_chaine(valeur)
    if isinstance(valeur, datetime | date):
        return valeur.isoformat()
    if isinstance(valeur, UUID):
        return str(valeur)
    if isinstance(valeur, dict):
        return {str(k): normaliser_json(v, f"{chemin}.{k}") for k, v in valeur.items()}
    if isinstance(valeur, list | tuple):
        return [normaliser_json(v, f"{chemin}[{i}]") for i, v in enumerate(valeur)]
    return valeur


class Enveloppe(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    type: str = Field(pattern=r"^[a-z_]+\.[a-z_]+$")
    version: int = Field(ge=1)
    occurred_at: AwareDatetime
    producer: Producteur
    aggregate_id: UUID
    trace_id: str = Field(min_length=1)
    causation_id: UUID | None = None
    payload: dict[str, Any]

    @field_validator("payload", mode="before")
    @classmethod
    def _payload_sans_flottant(cls, valeur: Any) -> Any:
        return normaliser_json(valeur)

    def sujet(self) -> str:
        """Sujet NATS : evt.<service>.<type>.v<n>."""
        return f"evt.{self.producer}.{self.type}.v{self.version}"

    def en_json(self) -> bytes:
        return self.model_dump_json().encode()

    @classmethod
    def depuis_json(cls, donnees: bytes | str) -> Enveloppe:
        return cls.model_validate_json(donnees)


def nouvelle_enveloppe(
    *,
    type: str,
    version: int,
    producer: Producteur,
    aggregate_id: UUID,
    payload: dict[str, Any],
    cause: Enveloppe | None = None,
) -> Enveloppe:
    """Crée une enveloppe ; si elle répond à un événement `cause`, elle en hérite la trace et la causalité."""
    return Enveloppe(
        id=uuid7(),
        type=type,
        version=version,
        occurred_at=datetime.now(UTC),
        producer=producer,
        aggregate_id=aggregate_id,
        trace_id=cause.trace_id if cause else trace_id_courant(),
        causation_id=cause.id if cause else None,
        payload=payload,
    )
