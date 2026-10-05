"""Durées de vie des sessions, pré-sessions, liens et appareils (TEC-SEC-02, ADR 0006)."""

from __future__ import annotations

from datetime import datetime, timedelta

DUREE_PRE_SESSION = timedelta(minutes=5)
ESSAIS_TOTP_MAX = 5
INACTIVITE_MAX = timedelta(hours=12)
DUREE_MAX_SESSION = timedelta(days=30)
DUREE_INVITATION = timedelta(days=7)
DUREE_REINITIALISATION = timedelta(hours=1)
DUREE_APPAREIL = timedelta(days=365)
# 5 codes faux (TOTP ou secours) invalident un lien de réinitialisation (ADR 0006)
ESSAIS_CODE_REINITIALISATION = 5


def expiration_pre_session(cree_le: datetime) -> datetime:
    return cree_le + DUREE_PRE_SESSION


def pre_session_epuisee(essais_totp: int) -> bool:
    """Après 5 codes faux (TOTP ou secours), la pré-session est révoquée."""
    return essais_totp >= ESSAIS_TOTP_MAX


def expiration_session(cree_le: datetime, derniere_activite: datetime) -> datetime:
    """12 h glissantes, plafonnées à 30 jours après la création."""
    return min(derniere_activite + INACTIVITE_MAX, cree_le + DUREE_MAX_SESSION)


def session_valide(cree_le: datetime, derniere_activite: datetime, maintenant: datetime) -> bool:
    return maintenant < expiration_session(cree_le, derniere_activite)


def expiration_invitation(cree_le: datetime) -> datetime:
    return cree_le + DUREE_INVITATION


def expiration_reinitialisation(cree_le: datetime) -> datetime:
    return cree_le + DUREE_REINITIALISATION


def expiration_appareil(cree_le: datetime) -> datetime:
    return cree_le + DUREE_APPAREIL
