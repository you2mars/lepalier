"""Contrôles de saisie communs aux routes : nom affiché et adresse e-mail, avec les messages des libellés."""

from __future__ import annotations

import re

from app.engines.nom_affiche import nettoyer, nom_affiche_valide
from app.libelles import message

EMAIL_LONGUEUR_MAX = 254
# caractères ASCII imprimables seulement (U+0021 à U+007E, hors « @ ») : ni contrôle, ni marque de sens
# d'écriture, ni lettre d'un autre alphabet qui imiterait une adresse connue
_EMAIL = re.compile(r"^[!-?A-~]+@[!-?A-~]+\.[!-?A-~]+$")


def nom_affiche_saisi(nom: str) -> str:
    if not nom_affiche_valide(nom):
        raise ValueError(message("nom_affiche.invalide"))
    return nettoyer(nom)


def email_saisi(email: str) -> str:
    """Espaces ordinaires autour retirés (pas les retours à la ligne) ; casse conservée."""
    nettoye = email.strip(" ")
    if len(nettoye) > EMAIL_LONGUEUR_MAX or not _EMAIL.fullmatch(nettoye):
        raise ValueError(message("utilisateurs.email_invalide"))
    return nettoye
