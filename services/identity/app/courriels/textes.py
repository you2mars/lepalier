"""Textes des e-mails de compte, validés le 4 octobre 2026 (ADR 0006, UX-13, UX-16).

Objet « [LePalier] … », 5 lignes au plus, aucun mot de passe ni code ; dates en toutes lettres, heure de
Paris.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

PARIS = ZoneInfo("Europe/Paris")
JOURS = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")
MOIS = (
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
)


@dataclass(frozen=True)
class Courriel:
    objet: str
    corps: str


def date_heure_paris(instant: datetime) -> tuple[str, str]:
    """(« mercredi 15 juillet 2026 », « 1 h 30 ») pour un instant donné, à l'heure de Paris."""
    local = instant.astimezone(PARIS)
    jour = "1er" if local.day == 1 else str(local.day)
    return (
        f"{JOURS[local.weekday()]} {jour} {MOIS[local.month - 1]} {local.year}",
        f"{local.hour} h {local.minute:02d}",
    )


def nouvel_appareil(nom_affiche: str, instant: datetime) -> Courriel:
    date, heure = date_heure_paris(instant)
    return Courriel(
        objet="[LePalier] Nouvelle connexion à votre compte",
        corps=(
            f"Bonjour {nom_affiche},\n"
            f"Votre compte LePalier a été utilisé le {date} à {heure} depuis un appareil ou un navigateur "
            "utilisé pour la première fois.\n"
            "Si c'est vous, il n'y a rien à faire. Sinon, contactez tout de suite le gérant de la SCI."
        ),
    )


def alerte_echecs(nom_gerant: str, nom_affiche: str, instant: datetime) -> Courriel:
    date, _ = date_heure_paris(instant)
    return Courriel(
        objet="[LePalier] Nombreux essais de connexion sur un compte",
        corps=(
            f"Bonjour {nom_gerant},\n"
            "Au moins 20 essais de connexion ont échoué en une heure sur le compte de "
            f"{nom_affiche}, le {date}.\n"
            f"Ces essais viennent peut-être d'une autre personne. Vérifiez avec {nom_affiche} et, si besoin, "
            "suspendez son accès dans Administration, Utilisateurs."
        ),
    )


def alerte_compte_suspendu(nom_gerant: str, nom_affiche: str, instant: datetime) -> Courriel:
    date, heure = date_heure_paris(instant)
    return Courriel(
        objet="[LePalier] Connexion d'un compte suspendu",
        corps=(
            f"Bonjour {nom_gerant},\n"
            f"{nom_affiche} a essayé de se connecter le {date} à {heure}, avec le bon mot de passe et le "
            "bon code, alors que son accès est suspendu.\n"
            "Si cet accès doit être rétabli, réactivez-le dans Administration, Utilisateurs."
        ),
    )


def invitation(nom_affiche: str, nom_gerant: str, lien: str) -> Courriel:
    return Courriel(
        objet="[LePalier] Votre invitation",
        corps=(
            f"Bonjour {nom_affiche},\n"
            f"{nom_gerant} vous invite à utiliser LePalier, "
            "l'application de gestion de l'immeuble de la SCI.\n"
            "Pour créer votre accès, ouvrez ce lien et suivez les étapes à l'écran. Prévoyez 5 minutes et "
            f"gardez votre téléphone à portée de main : {lien}\n"
            "Ce lien est valable 7 jours. Si vous n'attendiez pas cette invitation, ignorez ce message."
        ),
    )
