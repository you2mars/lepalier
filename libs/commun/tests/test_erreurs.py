from fastapi import FastAPI
from fastapi.testclient import TestClient
from opentelemetry.sdk.trace import TracerProvider
from pydantic import BaseModel, ConfigDict, Field

from commun.decimales import Montant
from commun.erreurs import ErreurApi, installer_gestionnaires


class _Corps(BaseModel):
    model_config = ConfigDict(extra="forbid")
    montant: Montant
    libelle: str = Field(min_length=1)


def _app() -> FastAPI:
    app = FastAPI()
    installer_gestionnaires(app)

    @app.get("/metier")
    def metier() -> None:
        raise ErreurApi(409, "deja_enregistre", "Ce paiement a déjà été enregistré.", {"paiement_id": "p1"})

    @app.post("/saisie")
    def saisie(corps: _Corps) -> dict[str, str]:
        return {"montant": str(corps.montant)}

    @app.get("/panne")
    def panne() -> None:
        raise RuntimeError("détail interne à ne pas divulguer")

    return app


CLIENT = TestClient(_app(), raise_server_exceptions=False)


def _champs(corps: dict[str, object]) -> dict[str, str]:
    details = corps["details"]
    assert isinstance(details, dict)
    return {c["champ"]: c["message"] for c in details["champs"]}


def test_erreur_metier__format_commun() -> None:
    r = CLIENT.get("/metier")
    assert r.status_code == 409
    corps = r.json()
    assert set(corps) == {"code", "message", "details", "trace_id"}
    assert corps["code"] == "deja_enregistre"
    assert corps["message"] == "Ce paiement a déjà été enregistré."
    assert corps["details"] == {"paiement_id": "p1"}


def test_validation__champs_manquants_en_francais() -> None:
    r = CLIENT.post("/saisie", json={})
    assert r.status_code == 422
    corps = r.json()
    assert corps["code"] == "invalid"
    assert corps["message"] == "Certaines informations sont incorrectes. Corrigez les champs signalés."
    assert _champs(corps) == {"montant": "Ce champ est obligatoire.", "libelle": "Ce champ est obligatoire."}


def test_validation__montant_flottant_texte_vide_et_champ_inconnu() -> None:
    r = CLIENT.post("/saisie", json={"montant": 1.5, "libelle": "", "intrus": 1})
    assert r.status_code == 422
    assert _champs(r.json()) == {
        "montant": "Le montant doit être écrit avec un point et deux décimales au plus, par exemple 650.00.",
        "libelle": "Ce champ ne peut pas être vide.",
        "intrus": "Ce champ n'est pas attendu.",
    }


def test_validation__corps_illisible() -> None:
    r = CLIENT.post("/saisie", content=b"{pas du json", headers={"Content-Type": "application/json"})
    assert r.status_code == 422
    assert r.json()["code"] == "invalid"


def test_route_inconnue__404_format_commun() -> None:
    r = CLIENT.get("/inexistant")
    assert r.status_code == 404
    assert r.json()["code"] == "not_found"
    assert r.json()["message"] == "Cette page ou cette information n'existe pas."


def test_methode_non_permise__405_format_commun() -> None:
    r = CLIENT.delete("/metier")
    assert r.status_code == 405
    assert r.json()["code"] == "method_not_allowed"


def test_panne__500_sans_detail_interne() -> None:
    r = CLIENT.get("/panne")
    assert r.status_code == 500
    corps = r.json()
    assert corps["code"] == "internal"
    assert "interne" not in corps["message"]
    assert corps["message"] == "Une erreur inattendue est survenue. Réessayez dans quelques instants."
    assert corps["trace_id"]


def test_trace_id__repris_de_x_request_id_sans_trace_otel() -> None:
    assert CLIENT.get("/metier", headers={"X-Request-Id": "req-123"}).json()["trace_id"] == "req-123"


def test_trace_id__trace_otel_prioritaire() -> None:
    traceur = TracerProvider().get_tracer("essai")
    with traceur.start_as_current_span("requete") as span:
        attendu = format(span.get_span_context().trace_id, "032x")
        corps = CLIENT.get("/metier", headers={"X-Request-Id": "req-123"}).json()
    assert corps["trace_id"] == attendu
