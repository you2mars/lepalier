"""Refus des parcours de compte : message lu dans contracts/libelles, rattaché au champ concerné (UX-19)."""

from __future__ import annotations

from typing import Any

from app.libelles import message
from commun.erreurs import ErreurApi


def refuser(statut: int, code: str, cle: str, champ: str | None = None) -> ErreurApi:
    return refuser_texte(statut, code, message(cle), champ)


def refuser_texte(statut: int, code: str, texte: str, champ: str | None = None) -> ErreurApi:
    details: dict[str, Any] = {"champs": [{"champ": champ, "message": texte}]} if champ else {}
    return ErreurApi(statut, code, texte, details)
