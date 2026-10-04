"""Jetons opaques de 256 bits (session, appareil, liens d'invitation et de réinitialisation).

Le jeton n'est remis qu'au navigateur ou dans le lien ; la base n'en garde que l'empreinte SHA-256.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets

TAILLE_OCTETS = 32
# 32 octets en base64 URL sans « = » : 43 caractères
_FORME = re.compile(r"^[A-Za-z0-9_-]{43}$")


def nouveau_jeton() -> str:
    return secrets.token_urlsafe(TAILLE_OCTETS)


def empreinte(jeton: str) -> bytes:
    return hashlib.sha256(jeton.encode()).digest()


def jeton_correspond(jeton: str, empreinte_attendue: bytes) -> bool:
    """Vrai si `jeton` a pour empreinte `empreinte_attendue` ; temps constant, jamais d'exception."""
    if not _FORME.fullmatch(jeton) or len(empreinte_attendue) != hashlib.sha256().digest_size:
        return False
    return hmac.compare_digest(empreinte(jeton), empreinte_attendue)
