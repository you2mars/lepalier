"""make new-service : un service généré ne garde aucune marque __…__ du gabarit (étape 5, dette des images).

Travaille uniquement dans des dossiers temporaires (GABARIT et DESTINATION), jamais dans services/.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
SCRIPT = RACINE / "scripts" / "new-service.sh"
MARQUE = re.compile(r"__[A-Z][A-Z0-9_]*__")


def _generer(destination: Path, gabarit: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "DESTINATION": str(destination)}
    if gabarit is not None:
        env["GABARIT"] = str(gabarit)
    return subprocess.run(
        ["bash", str(SCRIPT), "veille"], cwd=RACINE, env=env, capture_output=True, text=True, check=False
    )


def _marques(dossier: Path) -> list[str]:
    trouvees = []
    for fichier in dossier.rglob("*"):
        if fichier.is_file() and ".venv" not in fichier.parts:
            trouvees += [f"{fichier.relative_to(dossier)}: {m}" for m in MARQUE.findall(fichier.read_text())]
    return trouvees


def test_new_service__service_genere__aucune_marque_ni_proprietaire_d_image_a_remplacer(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "veille"
    r = _generer(destination)
    assert r.returncode == 0, r.stdout + r.stderr
    assert _marques(destination) == []
    assert "FROM ghcr.io/you2mars/app-base:" in (destination / "Dockerfile").read_text()


def test_new_service__marque_inconnue_restante__refus_sans_rien_creer(tmp_path: Path) -> None:
    gabarit = tmp_path / "gabarit"
    shutil.copytree(
        RACINE / "services" / "_template", gabarit, ignore=shutil.ignore_patterns(".venv", "__pycache__")
    )
    (gabarit / "app" / "reglage.py").write_text('PROPRIETAIRE = "__AUTRE_MARQUE__"\n')
    destination = tmp_path / "veille"
    r = _generer(destination, gabarit)
    assert r.returncode == 1
    assert "__AUTRE_MARQUE__" in r.stdout
    assert "app/reglage.py" in r.stdout
    assert not destination.exists()


def test_new_service__noms_python_en_minuscules__pas_des_marques(tmp_path: Path) -> None:
    """__init__, __future__ ou __name__ ne sont pas des marques du gabarit."""
    destination = tmp_path / "veille"
    assert _generer(destination).returncode == 0
    assert (destination / "app" / "__init__.py").exists()
