"""L'image Playwright de test_plateforme.py porte la même version que @playwright/test du front.

Sinon `npx --no-install playwright test` lance des navigateurs d'une autre version que la bibliothèque.
Lancé par `make test` (aucun Docker requis).
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]


def _image_playwright() -> str:
    """Valeur de la constante, lue sans exécuter le module."""
    arbre = ast.parse((RACINE / "scripts/tests/test_plateforme.py").read_text())
    (valeur,) = [
        n.value
        for n in arbre.body
        if isinstance(n, ast.Assign) and [getattr(c, "id", None) for c in n.targets] == ["IMAGE_PLAYWRIGHT"]
    ]
    return str(ast.literal_eval(valeur))


def test_image_playwright__meme_version_que_le_front__et_figee_par_empreinte() -> None:
    trouve = re.fullmatch(
        r"mcr\.microsoft\.com/playwright:v(\d+\.\d+\.\d+)-noble@sha256:[0-9a-f]{64}", _image_playwright()
    )
    assert trouve is not None
    paquet = json.loads((RACINE / "front/package.json").read_text())
    verrou = json.loads((RACINE / "front/package-lock.json").read_text())["packages"]
    assert {
        trouve.group(1),
        paquet["devDependencies"]["@playwright/test"],
        verrou["node_modules/@playwright/test"]["version"],
        verrou["node_modules/playwright"]["version"],
    } == {trouve.group(1)}
