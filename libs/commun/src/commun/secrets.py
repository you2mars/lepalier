"""Lecture des secrets montés en fichiers (ADR 0007).

Un secret lisible par le groupe ou les autres est refusé : le service ne démarre pas. Les messages d'erreur ne
contiennent jamais la valeur d'un secret.
"""

from __future__ import annotations

import stat
from pathlib import Path

DOSSIER_SECRETS = Path("/run/secrets")
TAILLE_MIN_CLE_HMAC = 32
TAILLE_EMPREINTE = 32


class SecretInvalide(Exception):
    """Secret absent, vide, mal formé ou trop ouvert."""


def lire_secret(chemin: Path) -> str:
    try:
        mode = chemin.stat().st_mode
    except FileNotFoundError as exc:
        raise SecretInvalide(
            f"secret introuvable : {chemin} (en dev : make dev-secrets, puis monter le secret dans Compose)"
        ) from exc
    if mode & (stat.S_IRWXG | stat.S_IRWXO):
        raise SecretInvalide(
            f"{chemin} est accessible au groupe ou aux autres (droits {stat.S_IMODE(mode):04o}) : "
            "attendu 0400 au nom de l'utilisateur du service (ADR 0007)"
        )
    valeur = chemin.read_text().strip()
    if not valeur:
        raise SecretInvalide(f"secret vide : {chemin}")
    return valeur


def lire_cles_hmac(chemin: Path) -> list[bytes]:
    """Une clé hexadécimale par ligne : la première signe, les suivantes vérifient seulement (rotation)."""
    cles: list[bytes] = []
    for numero, ligne in enumerate(lire_secret(chemin).splitlines(), start=1):
        if not ligne.strip():
            continue
        try:
            cle = bytes.fromhex(ligne.strip())
        except ValueError as exc:
            raise SecretInvalide(f"{chemin}, ligne {numero} : clé illisible (hexadécimal attendu)") from exc
        if len(cle) < TAILLE_MIN_CLE_HMAC:
            raise SecretInvalide(
                f"{chemin}, ligne {numero} : clé trop courte ({TAILLE_MIN_CLE_HMAC} octets minimum)"
            )
        cles.append(cle)
    return cles


def lire_jeton(dossier: Path, appelant: str, appele: str) -> str:
    return lire_secret(dossier / f"jeton_{appelant}_vers_{appele}")


def lire_empreintes(dossier: Path, appele: str) -> dict[str, bytes]:
    """Empreintes des jetons acceptés par `appele`, par appelant (fichiers empreinte_*_vers_<appele>)."""
    suffixe = f"_vers_{appele}"
    empreintes: dict[str, bytes] = {}
    if not dossier.is_dir():
        return empreintes
    for chemin in sorted(dossier.glob(f"empreinte_*{suffixe}")):
        appelant = chemin.name.removeprefix("empreinte_").removesuffix(suffixe)
        try:
            empreinte = bytes.fromhex(lire_secret(chemin))
        except ValueError as exc:
            raise SecretInvalide(f"{chemin} : empreinte illisible (hexadécimal attendu)") from exc
        if len(empreinte) != TAILLE_EMPREINTE:
            raise SecretInvalide(f"{chemin} : empreinte SHA-256 attendue ({TAILLE_EMPREINTE} octets)")
        empreintes[appelant] = empreinte
    return empreintes
