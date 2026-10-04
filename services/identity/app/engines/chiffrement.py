"""Chiffrement du secret TOTP et pseudonymisation des e-mails (ADR 0007, complément du 4 octobre 2026).

Format chiffré : 1 octet de version de clé, nonce de 12 octets, texte chiffré et étiquette AES-256-GCM. La
donnée associée (identifiant de l'utilisateur) empêche de déchiffrer un secret recopié sur une autre ligne.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from collections.abc import Sequence
from dataclasses import dataclass

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

TAILLE_CLE = 32
TAILLE_NONCE = 12
TAILLE_ETIQUETTE = 16


class CleInvalide(ValueError):
    """Fichier de clés illisible (sans valeur de clé dans le message)."""


class DechiffrementImpossible(Exception):
    """Données altérées, tronquées, d'une autre ligne, ou chiffrées avec une clé retirée."""


@dataclass(frozen=True)
class Cle:
    version: int
    valeur: bytes


def lire_cles(texte: str) -> list[Cle]:
    """Une ligne « <version> <clé hexadécimale> » par clé ; la première chiffre, les suivantes déchiffrent."""
    cles: list[Cle] = []
    for numero, ligne in enumerate(texte.splitlines(), start=1):
        if not ligne.strip():
            continue
        morceaux = ligne.split()
        if len(morceaux) != 2 or not morceaux[0].isdigit() or not 1 <= int(morceaux[0]) <= 255:
            raise CleInvalide(f"ligne {numero} : « <version de 1 à 255> <clé hexadécimale> » attendu")
        try:
            valeur = bytes.fromhex(morceaux[1])
        except ValueError as exc:
            raise CleInvalide(f"ligne {numero} : clé illisible (hexadécimal attendu)") from exc
        if len(valeur) != TAILLE_CLE:
            raise CleInvalide(f"ligne {numero} : clé de {TAILLE_CLE} octets attendue")
        cles.append(Cle(version=int(morceaux[0]), valeur=valeur))
    if not cles:
        raise CleInvalide("aucune clé")
    if len({c.version for c in cles}) != len(cles):
        raise CleInvalide("version de clé en double")
    return cles


def chiffrer(secret: bytes, cles: Sequence[Cle], donnee_associee: bytes) -> bytes:
    if not cles:
        raise CleInvalide("aucune clé")
    cle = cles[0]
    nonce = os.urandom(TAILLE_NONCE)
    return bytes([cle.version]) + nonce + AESGCM(cle.valeur).encrypt(nonce, secret, donnee_associee)


def dechiffrer(donnees: bytes, cles: Sequence[Cle], donnee_associee: bytes) -> bytes:
    if len(donnees) < 1 + TAILLE_NONCE + TAILLE_ETIQUETTE + 1:
        raise DechiffrementImpossible("données tronquées")
    cle = next((c for c in cles if c.version == donnees[0]), None)
    if cle is None:
        raise DechiffrementImpossible(f"clé de version {donnees[0]} absente")
    nonce, chiffre = donnees[1 : 1 + TAILLE_NONCE], donnees[1 + TAILLE_NONCE :]
    try:
        return AESGCM(cle.valeur).decrypt(nonce, chiffre, donnee_associee)
    except InvalidTag as exc:
        raise DechiffrementImpossible("données altérées ou d'un autre utilisateur") from exc


def pseudonymiser(email: str, cle: bytes) -> bytes:
    """HMAC-SHA256 de l'adresse en minuscules, sans espaces autour : identifie un compte sans le révéler."""
    return hmac.new(cle, email.strip().lower().encode(), hashlib.sha256).digest()
