"""Nom affiché (ADR 0006) : 1 à 60 caractères, sans « @ » ni caractère de contrôle, pas seulement des espaces.

Même règle que le contrat `utilisateur.*` et la contrainte de la base (migration 0005) : un retour à la ligne
pourrait injecter des lignes dans les e-mails envoyés aux gérants.
"""

from __future__ import annotations

import re

LONGUEUR_MAX = 60
# contrôles C0 et C1, séparateurs de ligne et de paragraphe, marques de sens d'écriture
_CONTROLE = re.compile(r"[\x00-\x1f\x7f-\x9f\u2028-\u202e\u2066-\u2069]")


def nettoyer(nom: str) -> str:
    """Espaces de début et de fin retirés ; l'intérieur est conservé tel que saisi."""
    return nom.strip(" ")


def nom_affiche_valide(nom: str) -> bool:
    nettoye = nettoyer(nom)
    return (
        1 <= len(nettoye) <= LONGUEUR_MAX
        and "@" not in nettoye
        and _CONTROLE.search(nettoye) is None
        and nettoye.strip() != ""
    )
