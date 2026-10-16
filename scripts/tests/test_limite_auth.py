"""Limite de débit de /api/identity/auth/ (ADR 0006, N13) : réglable pour les seuls essais de la plateforme.

La valeur réelle (10 par minute) est écrite explicitement dans chaque fichier Compose qui démarre nginx ; le
gabarit nginx n'a aucune valeur par défaut ; la valeur d'essai n'apparaît que dans compose.essai.yml.
Lancé par `make test`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

RACINE = Path(__file__).resolve().parents[2]
GABARIT = RACINE / "deploy" / "nginx" / "templates" / "lepalier.conf.template"
NGINX_DEV = RACINE / "deploy" / "nginx" / "nginx.dev.conf"
ESSAI = RACINE / "scripts" / "tests" / "plateforme" / "compose.essai.yml"
VALEUR_REELLE = "10r/m"
VALEUR_ESSAI = "600r/m"
VARIABLE = "LEPALIER_LIMITE_AUTH"


def _services(fichier: Path) -> dict[str, Any]:
    return dict((yaml.safe_load(fichier.read_text()) or {}).get("services") or {})


def _environnement(service: dict[str, Any]) -> dict[str, str]:
    env = service.get("environment") or {}
    if isinstance(env, list):
        return dict(ligne.split("=", 1) for ligne in env)
    return {cle: str(valeur) for cle, valeur in env.items()}


# fichiers Compose de la plateforme réelle (dev et production), jamais celui des essais
FICHIERS_REELS = sorted(RACINE.glob("compose*.yml"))


def test_gabarit__limite_lue_dans_la_variable_sans_valeur_par_defaut() -> None:
    gabarit = GABARIT.read_text()
    assert f"limit_req_zone $binary_remote_addr zone=auth:10m rate=${{{VARIABLE}}};" in gabarit
    assert f"${{{VARIABLE}:-" not in gabarit
    assert "zone=auth:" not in NGINX_DEV.read_text()


def test_fichiers_reels_trouves() -> None:
    assert {f.name for f in FICHIERS_REELS} >= {"compose.dev.yml", "compose.prod.yml"}


@pytest.mark.parametrize("fichier", FICHIERS_REELS, ids=lambda f: f.name)
def test_compose_reel__valeur_reelle_explicite_jamais_celle_des_essais(fichier: Path) -> None:
    assert VALEUR_ESSAI not in fichier.read_text()
    nginx = _services(fichier).get("nginx")
    if nginx is None:
        # compose.prod.yml n'a pas encore de nginx : le contrôle s'appliquera dès qu'il en aura un
        assert fichier.name != "compose.dev.yml"
        return
    assert _environnement(nginx).get(VARIABLE) == VALEUR_REELLE


def test_compose_essai__valeur_haute_pour_les_seuls_essais() -> None:
    assert _environnement(_services(ESSAI)["nginx"]).get(VARIABLE) == VALEUR_ESSAI
