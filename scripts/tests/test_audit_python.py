"""scripts/audit_python.py (étape 6, TEC-SEC-13) : échec sur une vulnérabilité haute, critique ou de gravité
inconnue ; les autres sont signalées sans bloquer. Aucun accès réseau ici : les fiches OSV sont fournies."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

RACINE = Path(__file__).resolve().parents[2]


def _module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("audit_python", RACINE / "scripts" / "audit_python.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


AUDIT = _module()


@pytest.mark.parametrize(
    ("fiche", "attendue"),
    [
        ({"database_specific": {"severity": "CRITICAL"}}, "critique"),
        ({"database_specific": {"severity": "HIGH"}}, "haute"),
        ({"database_specific": {"severity": "MODERATE"}}, "moyenne"),
        ({"database_specific": {"severity": "LOW"}}, "faible"),
        ({"database_specific": {"severity": "high"}}, "haute"),
        (
            {"severity": [{"type": "CVSS_V3", "score": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"}]},
            "inconnue",
        ),
        ({}, "inconnue"),
    ],
)
def test_gravite__lue_dans_la_fiche_osv(fiche: dict[str, Any], attendue: str) -> None:
    assert AUDIT.gravite(fiche) == attendue


def test_gravite__la_plus_forte_de_la_fiche_et_de_ses_alias() -> None:
    fiches = {
        "PYSEC-2026-1": {"id": "PYSEC-2026-1", "aliases": ["GHSA-aaaa-bbbb-cccc"]},
        "GHSA-aaaa-bbbb-cccc": {"database_specific": {"severity": "HIGH"}},
    }
    assert AUDIT.gravite_avec_alias("PYSEC-2026-1", ["GHSA-aaaa-bbbb-cccc"], fiches.get) == "haute"


def test_gravite__alias_introuvables__inconnue() -> None:
    assert AUDIT.gravite_avec_alias("PYSEC-2026-2", ["CVE-2026-1"], lambda _: None) == "inconnue"


@pytest.mark.parametrize(
    ("gravites", "code"),
    [([], 0), (["faible", "moyenne"], 0), (["moyenne", "haute"], 1), (["critique"], 1), (["inconnue"], 1)],
)
def test_decision__echec_sur_haute_critique_ou_inconnue(gravites: list[str], code: int) -> None:
    assert AUDIT.code_de_sortie(gravites) == code


def test_rapport__une_ligne_par_vulnerabilite_avec_gravite_et_correctif() -> None:
    ligne = AUDIT.ligne_rapport("identity", "jinja2", "3.1.0", "GHSA-x", "haute", ["3.1.6"])
    assert ligne == "identity : jinja2 3.1.0, GHSA-x, gravité haute, corrigée en 3.1.6"
    sans_correctif = AUDIT.ligne_rapport("commun", "paquet", "1.0", "PYSEC-1", "inconnue", [])
    assert sans_correctif == "commun : paquet 1.0, PYSEC-1, gravité inconnue, aucune version corrigée connue"
