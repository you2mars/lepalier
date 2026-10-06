"""make dev-up, make tick… : adresse de la VM (APP_URL_PUBLIQUE) lue dans le certificat de make dev-certs.

Une seule source : l'adresse saisie (ou détectée) une fois par make dev-certs. Dossiers temporaires seulement.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(shutil.which("openssl") is None, reason="openssl requis")

RACINE = Path(__file__).resolve().parents[2]


def _make(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["make", *arguments], cwd=RACINE, capture_output=True, text=True, check=False)


def test_adresse_vm__lue_dans_le_certificat_et_transmise_a_compose(tmp_path: Path) -> None:
    assert _make("dev-certs", f"DEV_CERTS={tmp_path}", "IP=192.168.1.20").returncode == 0
    r = _make("-n", "tick", f"DEV_CERTS={tmp_path}")
    assert 'LEPALIER_URL_PUBLIQUE="https://192.168.1.20" docker compose -f compose.dev.yml' in r.stdout


def test_adresse_vm__sans_certificat__vide_et_dev_up_refuse(tmp_path: Path) -> None:
    r = _make("-n", "dev-up", f"DEV_CERTS={tmp_path}")
    assert 'LEPALIER_URL_PUBLIQUE=""' in r.stdout
    assert "lancez d'abord make dev-certs" in r.stdout
