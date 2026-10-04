"""Clés d'identity (ADR 0007) : signature des en-têtes, chiffrement du secret TOTP, pseudonymisation."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from app.engines.chiffrement import Cle, lire_cles
from commun.secrets import SecretInvalide, lire_cles_hmac, lire_secret


@dataclass(frozen=True)
class ClesCompte:
    hmac: list[bytes]
    chiffrement: list[Cle] = field(default_factory=list)
    pseudonymisation: bytes = b""


def charger_cles(dossier: Path) -> ClesCompte:
    """Lit les trois secrets d'identity ; un secret absent, trop ouvert ou illisible arrête le démarrage."""
    hmac = lire_cles_hmac(dossier / "cle_hmac_identite")
    chiffrement = lire_cles(lire_secret(dossier / "cle_chiffrement_identity"))
    try:
        pseudonymisation = bytes.fromhex(lire_secret(dossier / "cle_pseudonymisation_identity"))
    except ValueError as exc:
        raise SecretInvalide("cle_pseudonymisation_identity : hexadécimal attendu") from exc
    if len(pseudonymisation) != 32:
        raise SecretInvalide("cle_pseudonymisation_identity : 32 octets attendus")
    return ClesCompte(hmac=hmac, chiffrement=chiffrement, pseudonymisation=pseudonymisation)
