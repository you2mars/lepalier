"""Robustesse et hachage des mots de passe (APP-USR-01, TEC-SEC-01, ADR 0006).

Règle NIST : 12 à 128 caractères, aucune règle de composition. Refus, dans cet ordre : trop court, trop
long, suite ou répétition, nom de l'application, adresse e-mail (complète, ou partie locale d'au moins 4
caractères), mot de passe courant. Normalisation à la création comme à la vérification : NFKC, espaces de
début et de fin retirés, espaces intérieurs consécutifs ramenés à un seul (ADR 0006). La suppression de tous
les espaces et le passage en minuscules ne servent qu'aux comparaisons. Messages : contracts/libelles.
"""

from __future__ import annotations

import unicodedata
from enum import StrEnum
from itertools import pairwise

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from argon2.low_level import Type

LONGUEUR_MIN = 12
LONGUEUR_MAX = 128
LONGUEUR_MIN_PARTIE_LOCALE = 4
MOTIF_REPETE_MAX = 4
NOMS_APPLICATION = ("palier",)  # couvre « lepalier »
# séquences lues dans un sens ou dans l'autre ; les chiffres bouclent (…8901…)
SEQUENCES: tuple[tuple[str, bool], ...] = (
    ("0123456789", True),
    ("abcdefghijklmnopqrstuvwxyz", False),
    ("azertyuiopqsdfghjklmwxcvbn", False),
    ("qwertyuiopasdfghjklzxcvbnm", False),
)

_HACHEUR = PasswordHasher(
    time_cost=2, memory_cost=19456, parallelism=1, hash_len=32, salt_len=16, type=Type.ID
)


class Motif(StrEnum):
    TROP_COURT = "trop_court"
    TROP_LONG = "trop_long"
    SUITE_OU_REPETITION = "suite_ou_repetition"
    NOM_APPLICATION = "nom_application"
    ADRESSE_EMAIL = "adresse_email"
    COURANT = "courant"


def _nfkc(texte: str) -> str:
    return unicodedata.normalize("NFKC", texte)


def normaliser(mot_de_passe: str) -> str:
    """Forme hachée et mesurée : NFKC, sans espaces autour, espaces intérieurs consécutifs réduits à un."""
    return " ".join(_nfkc(mot_de_passe).split())


def _comparable(texte: str) -> str:
    return "".join(_nfkc(texte).lower().split())


def lire_courants(texte: str) -> frozenset[str]:
    """Liste locale : en-tête, ligne « --- », puis un mot de passe par ligne."""
    corps = texte.split("\n---\n", 1)[-1]
    return frozenset(_comparable(ligne) for ligne in corps.splitlines() if ligne.strip())


def _repetition(compacte: str) -> bool:
    return any(
        compacte == (compacte[:k] * (len(compacte) // k + 1))[: len(compacte)]
        for k in range(1, MOTIF_REPETE_MAX + 1)
        if len(compacte) > k
    )


def _suit(compacte: str, sequence: str, boucle: bool, pas: int) -> bool:
    n = len(sequence)
    for a, b in pairwise(compacte):
        if a not in sequence or b not in sequence:
            return False
        suivant = sequence.index(a) + pas
        if boucle:
            suivant %= n
        if not 0 <= suivant < n or sequence[suivant] != b:
            return False
    return True


def _suite(compacte: str) -> bool:
    return any(_suit(compacte, seq, boucle, pas) for seq, boucle in SEQUENCES for pas in (1, -1))


def motif_refus(mot_de_passe: str, email: str, courants: frozenset[str]) -> Motif | None:
    """Premier motif de refus rencontré, ou None si le mot de passe est accepté."""
    longueur = len(normaliser(mot_de_passe))
    if longueur < LONGUEUR_MIN:
        return Motif.TROP_COURT
    if longueur > LONGUEUR_MAX:
        return Motif.TROP_LONG
    compacte = _comparable(mot_de_passe)
    if _repetition(compacte) or _suite(compacte):
        return Motif.SUITE_OU_REPETITION
    if any(nom in compacte for nom in NOMS_APPLICATION):
        return Motif.NOM_APPLICATION
    adresse = _comparable(email)
    partie_locale = adresse.split("@", 1)[0]
    if adresse and (
        adresse in compacte
        or (len(partie_locale) >= LONGUEUR_MIN_PARTIE_LOCALE and partie_locale in compacte)
    ):
        return Motif.ADRESSE_EMAIL
    if compacte in courants:
        return Motif.COURANT
    return None


def hacher(mot_de_passe: str) -> str:
    return _HACHEUR.hash(normaliser(mot_de_passe))


def verifier(hache: str, mot_de_passe: str) -> bool:
    try:
        return _HACHEUR.verify(hache, normaliser(mot_de_passe))
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def rehachage_necessaire(hache: str) -> bool:
    try:
        return _HACHEUR.check_needs_rehash(hache)
    except (InvalidHashError, ValueError):
        return True


# Pour un compte inconnu : même coût de vérification qu'un vrai compte, réponse toujours négative (ADR 0006).
HACHAGE_FACTICE = hacher("compte inconnu : vérification factice de même coût")


def verifier_factice(mot_de_passe: str) -> bool:
    verifier(HACHAGE_FACTICE, mot_de_passe + "\x00")
    return False
