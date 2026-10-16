"""Jobs d'envoi des e-mails de compte : payload limité à des identifiants et un instant, jamais de jeton.

Le jeton d'un lien est créé dans le job, dans la transaction qui l'envoie : si l'envoi échoue, la transaction
est annulée et le jeton éventuellement parti ne vaut rien ; le nouvel essai en crée un autre.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Table, func, insert, select, update
from sqlalchemy.orm import Session

from app.courriels import textes
from app.courriels.envoi import Expediteur
from app.engines import durees
from app.engines.jetons import empreinte, nouveau_jeton
from app.engines.verrouillage import PERIODE_ALERTE
from app.models import APPAREIL, INVITATION, REINITIALISATION, UTILISATEUR
from commun.ids import uuid7
from commun.jobs import Gestionnaire, Job


def _utilisateur(s: Session, utilisateur_id: str) -> tuple[str, str]:
    email, nom, _ = _utilisateur_et_role(s, utilisateur_id)
    return email, nom


def _utilisateur_et_role(s: Session, utilisateur_id: str) -> tuple[str, str, str]:
    email, nom, role = s.execute(
        select(UTILISATEUR.c.email, UTILISATEUR.c.nom_affiche, UTILISATEUR.c.role).where(
            UTILISATEUR.c.id == UUID(utilisateur_id)
        )
    ).one()
    return email, nom, role


def _gerants_actifs(s: Session) -> list[tuple[str, str]]:
    return [
        (email, nom)
        for email, nom in s.execute(
            select(UTILISATEUR.c.email, UTILISATEUR.c.nom_affiche).where(
                UTILISATEUR.c.role == "gerant", UTILISATEUR.c.statut == "actif"
            )
        ).all()
    ]


def _invalider(s: Session, table: Table, utilisateur_id: UUID) -> None:
    s.execute(
        update(table)
        .where(
            table.c.utilisateur_id == utilisateur_id,
            table.c.utilisee_le.is_(None),
            table.c.invalidee_le.is_(None),
        )
        .values(invalidee_le=func.now())
    )


def invalider_invitations(s: Session, utilisateur_id: UUID) -> None:
    """Un seul lien actif par utilisateur : un renvoi invalide le précédent."""
    _invalider(s, INVITATION, utilisateur_id)


def invalider_reinitialisations(s: Session, utilisateur_id: UUID) -> None:
    """Une nouvelle demande, ou un mot de passe changé, invalide le lien en cours."""
    _invalider(s, REINITIALISATION, utilisateur_id)


def _utilisateur_verrouille(s: Session, job: Job) -> Any:
    return (
        s.execute(
            select(UTILISATEUR)
            .where(UTILISATEUR.c.id == UUID(job.payload["utilisateur_id"]))
            .with_for_update()
        )
        .mappings()
        .one()
    )


def gestionnaires(expediteur: Expediteur, url_publique: str) -> dict[str, Gestionnaire]:
    def _lien_d_activation(s: Session, job: Job) -> tuple[Any, str, datetime] | None:
        """Nouveau lien d'activation de 7 jours (utilisateur, lien, fin du lien), ou None si le compte n'est
        plus invité. L'auteur est le gérant qui a agi (`par_utilisateur_id`), à défaut celui qui a invité."""
        u = _utilisateur_verrouille(s, job)
        if u["statut"] != "invite":
            return None  # activé ou suspendu entre-temps : plus rien à envoyer
        par = (
            UUID(job.payload["par_utilisateur_id"])
            if "par_utilisateur_id" in job.payload
            else u["invite_par"]
        )
        invalider_invitations(s, u["id"])
        jeton = nouveau_jeton()
        maintenant = s.execute(select(func.now())).scalar_one()
        expire_le = durees.expiration_invitation(maintenant)
        s.execute(
            insert(INVITATION).values(
                id=uuid7(),
                utilisateur_id=u["id"],
                empreinte=empreinte(jeton),
                cree_le=maintenant,
                expire_le=expire_le,
                par_utilisateur_id=par,
            )
        )
        return u, f"{url_publique.rstrip('/')}/activation#{jeton}", expire_le

    def invitation(s: Session, job: Job) -> None:
        cree = _lien_d_activation(s, job)
        if cree is not None:
            u, lien, expire_le = cree
            nom_gerant = s.execute(
                select(UTILISATEUR.c.nom_affiche).where(UTILISATEUR.c.id == u["invite_par"])
            ).scalar_one()
            expediteur.envoyer(
                u["email"], textes.invitation(u["nom_affiche"], nom_gerant, u["role"], lien, expire_le)
            )

    def acces_reinitialise(s: Session, job: Job) -> None:
        cree = _lien_d_activation(s, job)
        if cree is not None:
            u, lien, expire_le = cree
            expediteur.envoyer(u["email"], textes.acces_reinitialise(u["nom_affiche"], lien, expire_le))

    def reinitialisation(s: Session, job: Job) -> None:
        u = _utilisateur_verrouille(s, job)
        if u["statut"] != "actif":
            return  # suspendu entre-temps : aucun lien
        invalider_reinitialisations(s, u["id"])
        jeton = nouveau_jeton()
        maintenant = s.execute(select(func.now())).scalar_one()
        expire_le = durees.expiration_reinitialisation(maintenant)
        s.execute(
            insert(REINITIALISATION).values(
                id=uuid7(),
                utilisateur_id=u["id"],
                empreinte=empreinte(jeton),
                cree_le=maintenant,
                expire_le=expire_le,
            )
        )
        lien = f"{url_publique.rstrip('/')}/reinitialisation#{jeton}"
        expediteur.envoyer(u["email"], textes.reinitialisation(u["nom_affiche"], lien, expire_le))

    def mot_de_passe_change(s: Session, job: Job) -> None:
        email, nom = _utilisateur(s, job.payload["utilisateur_id"])
        expediteur.envoyer(
            email, textes.mot_de_passe_change(nom, datetime.fromisoformat(job.payload["instant"]))
        )

    def nouvel_appareil(s: Session, job: Job) -> None:
        email, nom, role = _utilisateur_et_role(s, job.payload["utilisateur_id"])
        cree_le = s.execute(
            select(APPAREIL.c.cree_le).where(APPAREIL.c.id == UUID(job.payload["appareil_id"]))
        ).scalar_one()
        expediteur.envoyer(email, textes.nouvel_appareil(nom, cree_le, role))

    def alerte_echecs(s: Session, job: Job) -> None:
        _, nom = _utilisateur(s, job.payload["utilisateur_id"])
        instant = datetime.fromisoformat(job.payload["instant"])
        # job planifié avant l'ajout de « debut » : début de la fenêtre d'une heure
        debut = (
            datetime.fromisoformat(job.payload["debut"])
            if "debut" in job.payload
            else instant - PERIODE_ALERTE
        )
        for email_gerant, nom_gerant in _gerants_actifs(s):
            expediteur.envoyer(email_gerant, textes.alerte_echecs(nom_gerant, nom, debut, instant))

    def alerte_compte_suspendu(s: Session, job: Job) -> None:
        _, nom = _utilisateur(s, job.payload["utilisateur_id"])
        instant = datetime.fromisoformat(job.payload["instant"])
        for email_gerant, nom_gerant in _gerants_actifs(s):
            expediteur.envoyer(email_gerant, textes.alerte_compte_suspendu(nom_gerant, nom, instant))

    return {
        "courriel.invitation": invitation,
        "courriel.acces_reinitialise": acces_reinitialise,
        "courriel.reinitialisation": reinitialisation,
        "courriel.mot_de_passe_change": mot_de_passe_change,
        "courriel.nouvel_appareil": nouvel_appareil,
        "courriel.alerte_echecs": alerte_echecs,
        "courriel.alerte_compte_suspendu": alerte_compte_suspendu,
    }
