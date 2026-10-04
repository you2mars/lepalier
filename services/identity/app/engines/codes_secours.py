"""Codes de secours (TEC-SEC-01, ADR 0006) : 10 codes à usage unique, remis une seule fois, stockés hachés.

Format lisible XXXX-XXXX-XXXX en base32 de Crockford (60 bits, sans I, L, O ni U) ; à la saisie, la casse,
les espaces et les tirets sont ignorés, O vaut 0, I et L valent 1. Argon2id, comme les mots de passe : un
SHA-256 de 60 bits se casserait par force brute si la base fuitait.
"""

from __future__ import annotations

import secrets
from collections.abc import Sequence

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from argon2.low_level import Type

ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
NOMBRE = 10
LONGUEUR = 12
_CONFUSIONS = str.maketrans({"O": "0", "I": "1", "L": "1"})
_HACHEUR = PasswordHasher(
    time_cost=2, memory_cost=19456, parallelism=1, hash_len=32, salt_len=16, type=Type.ID
)


def generer() -> list[str]:
    codes: set[str] = set()
    while len(codes) < NOMBRE:
        brut = "".join(secrets.choice(ALPHABET) for _ in range(LONGUEUR))
        codes.add(f"{brut[:4]}-{brut[4:8]}-{brut[8:]}")
    return sorted(codes)


def normaliser(saisie: str) -> str | None:
    """Forme comparée (12 caractères de l'alphabet), ou None si la saisie ne peut pas être un code."""
    compacte = "".join(saisie.split()).replace("-", "").upper().translate(_CONFUSIONS)
    if len(compacte) != LONGUEUR or any(c not in ALPHABET for c in compacte):
        return None
    return compacte


def hacher(code: str) -> str:
    compacte = normaliser(code)
    if compacte is None:
        raise ValueError("code de secours mal formé")
    return _HACHEUR.hash(compacte)


def verifier(hache: str, saisie: str) -> bool:
    compacte = normaliser(saisie)
    if compacte is None:
        return False
    try:
        return _HACHEUR.verify(hache, compacte)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def trouver(saisie: str, empreintes: Sequence[str]) -> int | None:
    """Index du code disponible qui correspond à la saisie ; le service le marque ensuite comme utilisé."""
    if normaliser(saisie) is None:
        return None
    return next((i for i, hache in enumerate(empreintes) if verifier(hache, saisie)), None)
