"""Verrouillage, alerte au gérant et limite des demandes de réinitialisation (TEC-SEC-01, ADR 0006).

Couple (compte, IP) : 5 échecs dans une fenêtre de 15 min, comptés depuis la dernière réussite du couple,
verrouillent le couple 15 min à partir du 5e échec. Les essais faits pendant un verrou ne sont ni vérifiés ni
enregistrés par le service : le décompte reprend à zéro à la fin du verrou.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

FENETRE = timedelta(minutes=15)
DUREE_VERROU = timedelta(minutes=15)
SEUIL_COUPLE = 5
SEUIL_ALERTE = 20
PERIODE_ALERTE = timedelta(hours=1)
MAX_DEMANDES_REINITIALISATION = 3
PERIODE_REINITIALISATION = timedelta(hours=1)


@dataclass(frozen=True)
class Tentative:
    instant: datetime
    reussie: bool


def verrou_couple(tentatives: Sequence[Tentative], maintenant: datetime) -> datetime | None:
    """Fin du verrou en cours pour le couple (compte, IP), ou None s'il n'est pas verrouillé."""
    ordonnees = sorted(tentatives, key=lambda t: t.instant)
    reussites = [t.instant for t in ordonnees if t.reussie]
    depuis = reussites[-1] if reussites else None
    fenetre: list[datetime] = []
    fin_verrou: datetime | None = None
    for tentative in ordonnees:
        if tentative.reussie or (depuis is not None and tentative.instant <= depuis):
            continue
        if fin_verrou is not None and tentative.instant < fin_verrou:
            continue
        fenetre = [instant for instant in fenetre if instant > tentative.instant - FENETRE]
        fenetre.append(tentative.instant)
        if len(fenetre) >= SEUIL_COUPLE:
            fin_verrou = tentative.instant + DUREE_VERROU
            fenetre = []
    return fin_verrou if fin_verrou is not None and fin_verrou > maintenant else None


def alerte_compte(
    echecs: Sequence[datetime], derniere_alerte: datetime | None, maintenant: datetime, compte_connu: bool
) -> bool:
    """Vrai s'il faut alerter le gérant : 20 échecs ou plus en une heure, toutes IP ; une alerte par heure.

    Un compte inconnu ne déclenche jamais d'alerte (il n'y a personne à protéger ni à prévenir).
    """
    if not compte_connu:
        return False
    recents = sum(1 for instant in echecs if instant > maintenant - PERIODE_ALERTE)
    return recents >= SEUIL_ALERTE and (
        derniere_alerte is None or derniere_alerte <= maintenant - PERIODE_ALERTE
    )


def reinitialisation_autorisee(demandes: Sequence[datetime], maintenant: datetime) -> bool:
    recentes = sum(1 for instant in demandes if instant > maintenant - PERIODE_REINITIALISATION)
    return recentes < MAX_DEMANDES_REINITIALISATION
