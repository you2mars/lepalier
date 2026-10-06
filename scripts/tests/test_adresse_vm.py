"""make dev-certs écrit l'adresse de la VM (LEPALIER_URL_PUBLIQUE) dans .env, lu par Docker Compose pour
toute commande (up, ps, logs, exec, make tick…). Fichiers temporaires seulement (ENV_FICHIER), jamais le .env
du dépôt.
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


def _certs(dossier: Path, ip: str, *autres: str) -> subprocess.CompletedProcess[str]:
    return _make(
        "dev-certs", f"DEV_CERTS={dossier / 'certs'}", f"ENV_FICHIER={dossier / '.env'}", f"IP={ip}", *autres
    )


def test_dev_certs__adresse_de_la_vm_ecrite_dans_env(tmp_path: Path) -> None:
    r = _certs(tmp_path, "192.168.1.20")
    assert r.returncode == 0, r.stdout + r.stderr
    assert (tmp_path / ".env").read_text() == "LEPALIER_URL_PUBLIQUE=https://192.168.1.20\n"


def test_dev_certs__autres_lignes_conservees_et_jamais_en_double(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("AUTRE_REGLAGE=1\nLEPALIER_URL_PUBLIQUE=https://10.0.0.9\n")
    _certs(tmp_path, "192.168.1.20")
    _certs(tmp_path, "192.168.1.20", "FORCE=1")
    assert (tmp_path / ".env").read_text() == "AUTRE_REGLAGE=1\nLEPALIER_URL_PUBLIQUE=https://192.168.1.20\n"


def test_dev_certs__certificat_deja_present__adresse_du_certificat_reecrite(tmp_path: Path) -> None:
    """Sans FORCE, le certificat est gardé : .env reçoit son adresse, pas celle passée en paramètre."""
    _certs(tmp_path, "192.168.1.20")
    (tmp_path / ".env").write_text("")
    r = _certs(tmp_path, "192.168.1.99")
    assert "Certificat déjà présent" in r.stdout
    assert (tmp_path / ".env").read_text() == "LEPALIER_URL_PUBLIQUE=https://192.168.1.20\n"


def test_compose_dev__le_makefile_ne_passe_plus_la_variable() -> None:
    """Compose lit .env lui-même : make tick, make logs… fonctionnent comme docker compose tapé à la main."""
    r = _make("-n", "tick")
    assert "LEPALIER_URL_PUBLIQUE" not in r.stdout
    assert "docker compose -f compose.dev.yml" in r.stdout
