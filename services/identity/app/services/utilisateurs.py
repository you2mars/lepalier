"""Invitation et renvoi d'invitation par un gérant (APP-USR-01, ADR 0006).

L'invitation crée le compte au statut `invite` et planifie l'e-mail ; le jeton du lien n'existe que dans le
job qui l'envoie (jamais dans le payload du job ni dans le journal).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.jobs.courriels import invalider_invitations
from app.models import JOBS, JOURNAL_SVC, UTILISATEUR
from app.services.refus import refuser
from commun.ids import uuid7

Fabrique = Callable[[], Session]


@dataclass(frozen=True)
class Invite:
    id: UUID
    email: str
    nom_affiche: str
    role: str
    statut: str = "invite"


def _planifier_invitation(s: Session, utilisateur_id: UUID) -> None:
    JOBS.planifier(s, "courriel.invitation", str(uuid7()), payload={"utilisateur_id": utilisateur_id})


def inviter(fabrique: Fabrique, par: UUID, email: str, nom_affiche: str, role: str, ip: str | None) -> Invite:
    deja_utilise = refuser(409, "email_deja_utilise", "utilisateurs.email_deja_utilise", "email")
    uid = uuid7()
    try:
        with fabrique() as s, s.begin():
            existe = s.execute(
                select(UTILISATEUR.c.id).where(func.lower(UTILISATEUR.c.email) == email.lower())
            ).first()
            if existe is not None:
                raise deja_utilise
            s.execute(
                insert(UTILISATEUR).values(
                    id=uid,
                    email=email,
                    nom_affiche=nom_affiche,
                    role=role,
                    statut="invite",
                    origine="invitation",
                    invite_par=par,
                )
            )
            JOURNAL_SVC.ecrire(
                s,
                action="utilisateur.invite",
                table_cible="utilisateur",
                enregistrement_id=uid,
                utilisateur_id=par,
                apres={"role": role, "statut": "invite"},
                ip=ip,
            )
            _planifier_invitation(s, uid)
    except IntegrityError as exc:
        # deux invitations simultanées pour la même adresse : l'index unique tranche
        raise deja_utilise from exc
    return Invite(id=uid, email=email, nom_affiche=nom_affiche, role=role)


def renvoyer_invitation(fabrique: Fabrique, par: UUID, utilisateur_id: UUID, ip: str | None) -> None:
    """Invalide tout de suite le lien en cours, puis planifie un nouvel e-mail avec un nouveau lien."""
    with fabrique() as s, s.begin():
        statut = s.execute(
            select(UTILISATEUR.c.statut).where(UTILISATEUR.c.id == utilisateur_id).with_for_update()
        ).scalar()
        if statut is None:
            raise HTTPException(404)
        if statut != "invite":
            raise refuser(409, "deja_activee", "invitation.deja_activee")
        invalider_invitations(s, utilisateur_id)
        JOURNAL_SVC.ecrire(
            s,
            action="utilisateur.invitation_renvoyee",
            table_cible="utilisateur",
            enregistrement_id=utilisateur_id,
            utilisateur_id=par,
            ip=ip,
        )
        _planifier_invitation(s, utilisateur_id)
