"""Plateforme de développement (étape 5) : images, Compose et nginx, essayés pour de vrai avec Docker.

Lancés seulement par `make test-plateforme` (LEPALIER_PLATEFORME=1), qui construit d'abord les images
locales ; `make test` les ignore. Job CI « plateforme », filtré par chemins.
"""

from __future__ import annotations

import os
import subprocess

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("LEPALIER_PLATEFORME") != "1", reason="make test-plateforme (images construites, Docker)"
)

IMAGE_IDENTITY = "ghcr.io/you2mars/identity:dev"


def _dans_l_image(image: str, *commande: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", "run", "--rm", "--network", "none", "--entrypoint", commande[0], image, *commande[1:]],
        capture_output=True,
        text=True,
        check=False,
    )


# --- bloc A : images ------------------------------------------------------------------------------------


def test_image__identity_construite_depuis_l_app_base_locale() -> None:
    """P1 : l'image d'identity repose sur ghcr.io/you2mars/app-base, construite en local par make images."""
    base = subprocess.run(
        ["docker", "image", "inspect", "--format", "{{.Id}}", "ghcr.io/you2mars/app-base:latest"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    couches_base = subprocess.run(
        ["docker", "image", "inspect", "--format", "{{json .RootFS.Layers}}", base],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    couches_identity = subprocess.run(
        ["docker", "image", "inspect", "--format", "{{json .RootFS.Layers}}", IMAGE_IDENTITY],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert couches_identity.startswith(couches_base.rstrip("]"))


def test_image__utilisateur_10001_et_python_de_l_image() -> None:
    """P2 : processus sous l'uid 10001 ; environnement construit dans l'image, pas copié depuis l'hôte."""
    r = _dans_l_image(IMAGE_IDENTITY, "sh", "-c", "id -u && readlink -f .venv/bin/python && pwd")
    assert r.returncode == 0, r.stderr
    uid, python, dossier = r.stdout.split()
    assert (uid, dossier) == ("10001", "/srv/services/identity")
    assert python.startswith("/usr/local/bin/python3.12")


def test_image__libelles_lus_depuis_contracts() -> None:
    """P2 : contracts/libelles/ est dans l'image, au chemin par défaut d'APP_LIBELLES_DIR."""
    r = _dans_l_image(
        IMAGE_IDENTITY,
        ".venv/bin/python",
        "-c",
        "from app.libelles import message; print(message('connexion.trop_d_essais'))",
    )
    assert (r.returncode, r.stdout) == (0, "Trop d'essais. Réessayez dans 15 minutes.\n"), r.stderr


def test_image__dependances_du_verrou_sans_outils_de_test() -> None:
    """P2 : versions installées = versions de uv.lock ; pytest absent ; ni secret ni cache local copiés."""
    # installation à blanc du contenu exporté de uv.lock (conditions de plateforme évaluées par uv)
    verrou = _dans_l_image(
        IMAGE_IDENTITY,
        "sh",
        "-c",
        "uv export --frozen --no-dev --no-hashes --no-emit-project --no-emit-package commun --offline "
        "> /tmp/verrou.txt "
        "&& uv pip install --dry-run --offline --no-deps -r /tmp/verrou.txt",
    )
    assert verrou.returncode == 0, verrou.stderr
    assert "Would make no changes" in verrou.stderr, verrou.stderr
    assert _dans_l_image(IMAGE_IDENTITY, ".venv/bin/python", "-c", "import pytest").returncode != 0
    copies = _dans_l_image(
        IMAGE_IDENTITY,
        "sh",
        "-c",
        "find / -xdev \\( -name .pytest_cache -o -name .mypy_cache -o -name secrets -o -name '.env*' \\) "
        "-not -path '/proc/*' -not -path '/usr/*' 2>/dev/null",
    )
    assert copies.stdout == ""


def test_image__lance_l_api_et_le_worker_sans_uv_run() -> None:
    r = _dans_l_image(IMAGE_IDENTITY, "cat", "supervisord.conf")
    assert "uv run" not in r.stdout
    assert ".venv/bin/uvicorn" in r.stdout
    assert ".venv/bin/python -m app.worker" in r.stdout


def test_image__commande_tick_presente() -> None:
    r = _dans_l_image(IMAGE_IDENTITY, ".venv/bin/python", "-m", "app.scheduler", "--help")
    assert r.returncode == 0
    assert "tick" in r.stdout
