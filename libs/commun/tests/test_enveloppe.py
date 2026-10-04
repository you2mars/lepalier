import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, get_args

import pytest
from jsonschema import Draft202012Validator
from opentelemetry.sdk.trace import TracerProvider
from pydantic import ValidationError

from commun.enveloppe import Enveloppe, Producteur, nouvelle_enveloppe
from commun.ids import uuid7
from commun.trace import trace_id_courant

CONTRATS = Path(__file__).resolve().parents[3] / "contracts"
SCHEMA = json.loads((CONTRATS / "enveloppe.schema.json").read_text())
VALIDATEUR = Draft202012Validator(SCHEMA, format_checker=Draft202012Validator.FORMAT_CHECKER)


def _enveloppe(**surcharges: Any) -> Enveloppe:
    champs: dict[str, Any] = {
        "type": "utilisateur.cree",
        "version": 1,
        "producer": "identity",
        "aggregate_id": uuid7(),
        "payload": {"role": "gerant"},
    }
    champs.update(surcharges)
    return nouvelle_enveloppe(**champs)


def test_enveloppe__conforme_au_contrat_json_schema() -> None:
    donnees = json.loads(_enveloppe().en_json())
    assert list(VALIDATEUR.iter_errors(donnees)) == []


def test_enveloppe__conforme_au_contrat_avec_causation() -> None:
    donnees = json.loads(_enveloppe(cause=_enveloppe()).en_json())
    assert list(VALIDATEUR.iter_errors(donnees)) == []


def test_producteurs__identiques_au_contrat() -> None:
    assert list(get_args(Producteur)) == SCHEMA["properties"]["producer"]["enum"]


def test_enveloppe__identifiant_uuid7_et_horodatage_utc() -> None:
    env = _enveloppe()
    assert env.id.version == 7
    assert env.occurred_at.utcoffset() == timedelta(0)
    assert abs(datetime.now(UTC) - env.occurred_at) < timedelta(seconds=5)


def test_enveloppe__sujet_nats() -> None:
    assert _enveloppe().sujet() == "evt.identity.utilisateur.cree.v1"
    assert (
        _enveloppe(producer="charges-eau", type="releve.saisi", version=2).sujet()
        == "evt.charges-eau.releve.saisi.v2"
    )


def test_enveloppe__sans_cause__nouvelle_trace() -> None:
    env = _enveloppe()
    assert env.causation_id is None
    assert len(env.trace_id) == 32


def test_enveloppe__avec_cause__herite_trace_et_causation() -> None:
    parent = _enveloppe()
    enfant = _enveloppe(type="utilisateur.suspendu", cause=parent)
    assert enfant.trace_id == parent.trace_id
    assert enfant.causation_id == parent.id


def test_enveloppe__trace_otel_active_reprise() -> None:
    traceur = TracerProvider().get_tracer("essai")
    with traceur.start_as_current_span("requete") as span:
        attendu = format(span.get_span_context().trace_id, "032x")
        assert trace_id_courant() == attendu
        assert _enveloppe().trace_id == attendu


def test_enveloppe__payload_montants_dates_et_uuid_en_chaines() -> None:
    uid = uuid7()
    env = _enveloppe(
        payload={
            "montant": Decimal("650"),
            "lignes": [{"total": Decimal("1.5")}],
            "le": date(2026, 11, 3),
            "id": uid,
        }
    )
    assert json.loads(env.en_json())["payload"] == {
        "montant": "650.00",
        "lignes": [{"total": "1.50"}],
        "le": "2026-11-03",
        "id": str(uid),
    }


@pytest.mark.parametrize("payload", [{"montant": 650.0}, {"lignes": [{"total": 1.5}]}, {"x": {"y": [0.1]}}])
def test_enveloppe__payload_flottant_refuse(payload: dict[str, Any]) -> None:
    with pytest.raises(ValidationError, match="flottant"):
        _enveloppe(payload=payload)


def test_enveloppe__aller_retour_json() -> None:
    env = _enveloppe(payload={"montant": Decimal("12.30"), "nom_affiche": "Mme Durand"})
    assert Enveloppe.depuis_json(env.en_json()) == env


@pytest.mark.parametrize(
    "surcharges",
    [{"type": "UtilisateurCree"}, {"type": "utilisateur"}, {"producer": "inconnu"}, {"version": 0}],
)
def test_enveloppe__champs_invalides_refuses(surcharges: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        _enveloppe(**surcharges)


def test_enveloppe__depuis_json_refuse_champ_inconnu_et_date_naive() -> None:
    donnees = json.loads(_enveloppe().en_json())
    with pytest.raises(ValidationError):
        Enveloppe.depuis_json(json.dumps({**donnees, "intrus": 1}).encode())
    with pytest.raises(ValidationError):
        Enveloppe.depuis_json(json.dumps({**donnees, "occurred_at": "2026-10-04T12:00:00"}).encode())
