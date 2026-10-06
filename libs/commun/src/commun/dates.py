"""Dates en toutes lettres et heures à l'heure de Paris (UX-6, UX-13) : e-mails, PDF, commandes en terminal.

Un seul endroit pour les noms de jours et de mois ; les horodatages sont en UTC en base, affichés à Paris.
"""

from __future__ import annotations

from datetime import date, datetime
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


def date_en_toutes_lettres(jour: date) -> str:
    """« jeudi 1er octobre 2026 »."""
    numero = "1er" if jour.day == 1 else str(jour.day)
    return f"{JOURS[jour.weekday()]} {numero} {MOIS[jour.month - 1]} {jour.year}"


def _a_paris(instant: datetime) -> datetime:
    if instant.tzinfo is None:
        raise ValueError("instant sans fuseau horaire : impossible de le situer à l'heure de Paris")
    return instant.astimezone(PARIS)


def heure_paris(instant: datetime) -> str:
    """« 1 h 30 », à l'heure de Paris."""
    local = _a_paris(instant)
    return f"{local.hour} h {local.minute:02d}"


def date_heure_paris(instant: datetime) -> tuple[str, str]:
    """(« mercredi 15 juillet 2026 », « 1 h 30 ») pour un instant donné, à l'heure de Paris."""
    return date_en_toutes_lettres(_a_paris(instant).date()), heure_paris(instant)
