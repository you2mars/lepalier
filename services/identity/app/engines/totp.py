"""Codes à usage unique basés sur le temps (TOTP, RFC 6238 ; TEC-SEC-01, ADR 0006).

SHA-1, 6 chiffres, pas de 30 s : réglages lus par toutes les applications d'authentification courantes.
Fenêtre de ±1 pas ; anti-rejeu : seul un pas strictement supérieur au dernier pas accepté est valable.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import struct
from urllib.parse import quote, urlencode

EMETTEUR = "LePalier"
PAS_SECONDES = 30
CHIFFRES = 6
TAILLE_SECRET = 20
FENETRE = 1
_SAISIE = re.compile(r"^[0-9]{6}$")


def nouveau_secret() -> bytes:
    return os.urandom(TAILLE_SECRET)


def pas_a(instant_unix: float) -> int:
    return int(instant_unix // PAS_SECONDES)


def code(secret: bytes, pas: int) -> str:
    """HOTP (RFC 4226) du compteur `pas`."""
    empreinte = hmac.new(secret, struct.pack(">Q", pas), hashlib.sha1).digest()
    decalage = empreinte[-1] & 0x0F
    valeur = struct.unpack(">I", empreinte[decalage : decalage + 4])[0] & 0x7FFFFFFF
    return str(valeur % 10**CHIFFRES).zfill(CHIFFRES)


def verifier(secret: bytes, saisie: str, maintenant_unix: float, dernier_pas: int | None) -> int | None:
    """Pas accepté (à enregistrer comme dernier pas), ou None ; espaces et tirets de saisie tolérés."""
    nettoyee = "".join(saisie.split()).replace("-", "")
    if not _SAISIE.fullmatch(nettoyee):
        return None
    courant = pas_a(maintenant_unix)
    for pas in range(courant - FENETRE, courant + FENETRE + 1):
        if dernier_pas is not None and pas <= dernier_pas:
            continue
        if hmac.compare_digest(code(secret, pas), nettoyee):
            return pas
    return None


def uri_provisionnement(secret: bytes, nom_affiche: str) -> str:
    """URI otpauth affichée en QR code par le front ; libellé = nom affiché, jamais l'adresse e-mail."""
    libelle = f"{quote(EMETTEUR, safe='')}:{quote(nom_affiche, safe='')}"
    parametres = {
        "secret": base64.b32encode(secret).decode().rstrip("="),
        "issuer": EMETTEUR,
        "algorithm": "SHA1",
        "digits": str(CHIFFRES),
        "period": str(PAS_SECONDES),
    }
    return f"otpauth://totp/{libelle}?{urlencode(parametres)}"
