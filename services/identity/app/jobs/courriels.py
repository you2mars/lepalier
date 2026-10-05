"""Jobs d'envoi des e-mails de compte : payload limité à des identifiants et un instant, jamais de jeton.

Le jeton d'un lien est créé dans le job, dans la transaction qui l'envoie : si l'envoi échoue, la transaction
est annulée et le jeton éventuellement parti ne vaut rien ; le nouvel essai en crée un autre.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, insert, select, update
from sqlalchemy.orm import Session

from app.courriels import textes
from app.courriels.envoi import Expediteur
from app.engines import durees
from app.engines.jetons import empreinte, nouveau_jeton
from app.models import APPAREIL, INVITATION, UTILISATEUR
from commun.ids import uuid7
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


def invalider_invitations(s: Session, utilisateur_id: UUID) -> None:
    """Un seul lien actif par utilisateur : un renvoi invalide le précédent."""
    s.execute(
        update(INVITATION)
        .where(
            INVITATION.c.utilisateur_id == utilisateur_id,
            INVITATION.c.utilisee_le.is_(None),
            INVITATION.c.invalidee_le.is_(None),
        )
        .values(invalidee_le=func.now())
    )


def gestionnaires(expediteur: Expediteur, url_publique: str) -> dict[str, Gestionnaire]:
    def invitation(s: Session, job: Job) -> None:
        u = (
            s.execute(
                select(UTILISATEUR)
                .where(UTILISATEUR.c.id == UUID(job.payload["utilisateur_id"]))
                .with_for_update()
            )
            .mappings()
            .one()
        )
        if u["statut"] != "invite":
            return  # activé entre-temps : plus rien à envoyer
        nom_gerant = s.execute(
            select(UTILISATEUR.c.nom_affiche).where(UTILISATEUR.c.id == u["invite_par"])
        ).scalar_one()
        invalider_invitations(s, u["id"])
        jeton = nouveau_jeton()
        maintenant = s.execute(select(func.now())).scalar_one()
        s.execute(
            insert(INVITATION).values(
                id=uuid7(),
                utilisateur_id=u["id"],
                empreinte=empreinte(jeton),
                cree_le=maintenant,
                expire_le=durees.expiration_invitation(maintenant),
                par_utilisateur_id=u["invite_par"],
            )
        )
        lien = f"{url_publique.rstrip('/')}/activation#{jeton}"
        expediteur.envoyer(u["email"], textes.invitation(u["nom_affiche"], nom_gerant, lien))

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
        "courriel.invitation": invitation,
        "courriel.nouvel_appareil": nouvel_appareil,
        "courriel.alerte_echecs": alerte_echecs,
        "courriel.alerte_compte_suspendu": alerte_compte_suspendu,
    }
