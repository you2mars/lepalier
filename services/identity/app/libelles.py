"""Textes affichés d'identity, lus dans contracts/libelles/identity.json : écrits une seule fois, partagés
avec le front."""

from __future__ import annotations

import json
from functools import cache
from typing import cast

from app.engines.mot_de_passe import Motif
from app.settings import settings


@cache
def libelles() -> dict[str, dict[str, str]]:
    return cast(dict[str, dict[str, str]], json.loads((settings.libelles_dir / "identity.json").read_text()))


def message_mot_de_passe(motif: Motif) -> str:
    return libelles()["mot_de_passe"][motif.value]
