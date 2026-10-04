"""Jobs d'envoi des e-mails de compte : payload limité à des identifiants et un instant, jamais de jeton."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.courriels import textes
from app.courriels.envoi import Expediteur
from app.models import APPAREIL, UTILISATEUR
from commun.jobs import Gestionnaire, Job


def _utilisateur(s: Session, utilisateur_id: str) -> tuple[str, str]:
    email, nom = s.execute(
        select(UTILISATEUR.c.email, UTILISATEUR.c.nom_affiche).where(UTILISATEUR.c.id == UUID(utilisateur_id))
    ).one()
    return email, nom


def _gerants_actifs(s: Session) -> list[tuple[str, str]]:
    return [
        (email, nom)
        for email, nom in s.execute(
            select(UTILISATEUR.c.email, UTILISATEUR.c.nom_affiche).where(
                UTILISATEUR.c.role == "gerant", UTILISATEUR.c.statut == "actif"
            )
        ).all()
    ]


def gestionnaires(expediteur: Expediteur) -> dict[str, Gestionnaire]:
    def nouvel_appareil(s: Session, job: Job) -> None:
        email, nom = _utilisateur(s, job.payload["utilisateur_id"])
        cree_le = s.execute(
            select(APPAREIL.c.cree_le).where(APPAREIL.c.id == UUID(job.payload["appareil_id"]))
        ).scalar_one()
        expediteur.envoyer(email, textes.nouvel_appareil(nom, cree_le))

    def alerte_echecs(s: Session, job: Job) -> None:
        _, nom = _utilisateur(s, job.payload["utilisateur_id"])
        instant = datetime.fromisoformat(job.payload["instant"])
        for email_gerant, nom_gerant in _gerants_actifs(s):
            expediteur.envoyer(email_gerant, textes.alerte_echecs(nom_gerant, nom, instant))

    def alerte_compte_suspendu(s: Session, job: Job) -> None:
        _, nom = _utilisateur(s, job.payload["utilisateur_id"])
        instant = datetime.fromisoformat(job.payload["instant"])
        for email_gerant, nom_gerant in _gerants_actifs(s):
            expediteur.envoyer(email_gerant, textes.alerte_compte_suspendu(nom_gerant, nom, instant))

    return {
        "courriel.nouvel_appareil": nouvel_appareil,
        "courriel.alerte_echecs": alerte_echecs,
        "courriel.alerte_compte_suspendu": alerte_compte_suspendu,
    }
