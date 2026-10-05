"""Invitation et renvoi d'invitation par un gérant (APP-USR-01, ADR 0006).

L'invitation crée le compte au statut `invite` et planifie l'e-mail ; le jeton du lien n'existe que dans le
job qui l'envoie (jamais dans le payload du job ni dans le journal).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.jobs.courriels import invalider_invitations, invalider_reinitialisations
from app.libelles import message
from app.models import APPAREIL, CODE_SECOURS, INVITATION, JOB, JOBS, JOURNAL_SVC, SESSION, UTILISATEUR
from app.services.evenements import publier
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


# --- consultation ---------------------------------------------------------------------------------------


def libelle_statut(statut: str, invitation_en_cours: bool = True) -> str:
    """Statut en mots (UX-14) ; clés écrites en entier pour le contrôle de cohérence des libellés."""
    if statut == "invite" and not invitation_en_cours:
        return message("statut.invitation_expiree")
    return {
        "invite": message("statut.invite"),
        "actif": message("statut.actif"),
        "suspendu": message("statut.suspendu"),
    }[statut]


def _invitations_en_cours(s: Session) -> set[UUID]:
    """Comptes invités dont l'invitation n'est pas expirée : lien valable, ou e-mail d'invitation encore à
    envoyer (job en attente, par exemple pendant une panne SMTP). Les autres : « Invitation expirée »."""
    liens = select(INVITATION.c.utilisateur_id).where(
        INVITATION.c.utilisee_le.is_(None),
        INVITATION.c.invalidee_le.is_(None),
        INVITATION.c.expire_le > func.now(),
    )
    envois = select(JOB.c.payload["utilisateur_id"].astext).where(
        JOB.c.type.in_(("courriel.invitation", "courriel.acces_reinitialise")),
        JOB.c.statut.in_(("planifie", "en_cours")),
    )
    return set(s.execute(liens).scalars()) | {UUID(i) for i in s.execute(envois).scalars()}


def _fiche(u: Any, en_cours: set[UUID]) -> dict[str, Any]:
    return {
        "id": str(u["id"]),
        "email": u["email"],
        "nom_affiche": u["nom_affiche"],
        "role": u["role"],
        "statut": u["statut"],
        "statut_libelle": libelle_statut(u["statut"], u["id"] in en_cours),
    }


def moi(fabrique: Fabrique, utilisateur_id: UUID) -> dict[str, Any]:
    """Le compte connecté ; un compte suspendu depuis moins de 60 s (en-têtes encore valables) est refusé."""
    with fabrique() as s:
        u = (
            s.execute(
                select(UTILISATEUR).where(UTILISATEUR.c.id == utilisateur_id, UTILISATEUR.c.statut == "actif")
            )
            .mappings()
            .first()
        )
    if u is None:
        raise HTTPException(401)
    return {"id": str(u["id"]), "email": u["email"], "nom_affiche": u["nom_affiche"], "role": u["role"]}


def lister(fabrique: Fabrique) -> list[dict[str, Any]]:
    with fabrique() as s:
        lignes = s.execute(select(UTILISATEUR)).mappings().all()
        en_cours = _invitations_en_cours(s)
    return [
        _fiche(u, en_cours) for u in sorted(lignes, key=lambda u: (u["nom_affiche"].casefold(), str(u["id"])))
    ]


# --- modification (rôle, suspension, réactivation) -----------------------------------------------------


def _verrouiller(s: Session, utilisateur_id: UUID) -> tuple[list[UUID], Any]:
    """Gérants actifs puis compte visé, verrouillés toujours dans cet ordre (gérants triés par identifiant) :
    deux gérants qui agissent l'un sur l'autre en même temps ne se bloquent pas mutuellement, et le second
    voit le résultat du premier avant de décider (APP-USR-05)."""
    gerants = list(
        s.execute(
            select(UTILISATEUR.c.id)
            .where(UTILISATEUR.c.role == "gerant", UTILISATEUR.c.statut == "actif")
            .order_by(UTILISATEUR.c.id)
            .with_for_update()
        ).scalars()
    )
    u = (
        s.execute(select(UTILISATEUR).where(UTILISATEUR.c.id == utilisateur_id).with_for_update())
        .mappings()
        .first()
    )
    if u is None:
        raise HTTPException(404)
    return gerants, u


def _dernier_gerant(gerants: list[UUID], u: Any, reste_gerant_actif: bool) -> None:
    if u["id"] in gerants and not reste_gerant_actif and len(gerants) <= 1:
        raise refuser(409, "dernier_gerant", "utilisateurs.dernier_gerant")


def _revoquer_sessions(s: Session, utilisateur_id: UUID, motif: str) -> None:
    s.execute(
        update(SESSION)
        .where(SESSION.c.utilisateur_id == utilisateur_id, SESSION.c.revoquee_le.is_(None))
        .values(revoquee_le=func.now(), motif_revocation=motif)
    )


def modifier(
    fabrique: Fabrique, par: UUID, utilisateur_id: UUID, role: str | None, statut: str | None, ip: str | None
) -> dict[str, Any]:
    with fabrique() as s, s.begin():
        maintenant = s.execute(select(func.now())).scalar_one()
        gerants, u = _verrouiller(s, utilisateur_id)
        nouveau_role = role or u["role"]
        nouveau_statut = statut or u["statut"]
        if nouveau_statut != u["statut"] and u["statut"] == "invite":
            raise refuser(409, "compte_non_active", "utilisateurs.compte_non_active")
        if nouveau_statut == "suspendu" and u["id"] == par:
            # même s'il reste d'autres gérants ; se rétrograder reste possible (confirmation à l'écran)
            raise refuser(409, "se_suspendre", "utilisateurs.se_suspendre")
        _dernier_gerant(gerants, u, nouveau_role == "gerant" and nouveau_statut == "actif")
        apres = dict(u)
        if nouveau_role != u["role"]:
            s.execute(update(UTILISATEUR).where(UTILISATEUR.c.id == u["id"]).values(role=nouveau_role))
            apres["role"] = nouveau_role
            _journaliser(s, "role_change", u["id"], par, {"role": u["role"]}, {"role": nouveau_role}, ip)
            if u["statut"] != "invite":
                # compte invité inconnu des autres services : utilisateur.cree portera son rôle
                publier(s, "role_change", apres, par, maintenant, ancien_role=u["role"])
        if nouveau_statut != u["statut"]:
            suspendre = nouveau_statut == "suspendu"
            s.execute(
                update(UTILISATEUR)
                .where(UTILISATEUR.c.id == u["id"])
                .values(statut=nouveau_statut, suspendu_le=maintenant if suspendre else None)
            )
            apres["statut"] = nouveau_statut
            if suspendre:
                _revoquer_sessions(s, u["id"], "suspension")
            fait = "suspendu" if suspendre else "reactive"
            _journaliser(s, fait, u["id"], par, {"statut": u["statut"]}, {"statut": nouveau_statut}, ip)
            publier(s, fait, apres, par, maintenant)
        return _fiche(apres, _invitations_en_cours(s))


def _journaliser(
    s: Session,
    fait: str,
    utilisateur_id: UUID,
    par: UUID | None,
    avant: dict[str, Any] | None,
    apres: dict[str, Any] | None,
    ip: str | None,
) -> None:
    JOURNAL_SVC.ecrire(
        s,
        action=f"utilisateur.{fait}",
        table_cible="utilisateur",
        enregistrement_id=utilisateur_id,
        utilisateur_id=par,
        avant=avant,
        apres=apres,
        ip=ip,
    )


# --- réinitialisation de l'accès (ADR 0006, décision 3) -------------------------------------------------


def effacer_acces(s: Session, u: Any, maintenant: datetime, par: UUID | None, ip: str | None) -> None:
    """Retour au statut invité, dans la transaction de l'appelant : mot de passe, secret TOTP et codes de
    secours effacés, sessions et appareils révoqués, liens en cours invalidés, action journalisée (`par`
    null : commande d'administration locale). Le nouveau lien est créé par l'appelant."""
    s.execute(
        update(UTILISATEUR)
        .where(UTILISATEUR.c.id == u["id"])
        .values(statut="invite", mot_de_passe_hache=None, totp_secret_chiffre=None, totp_dernier_pas=None)
    )
    s.execute(
        update(CODE_SECOURS)
        .where(
            CODE_SECOURS.c.utilisateur_id == u["id"],
            CODE_SECOURS.c.utilise_le.is_(None),
            CODE_SECOURS.c.invalide_le.is_(None),
        )
        .values(invalide_le=maintenant)
    )
    _revoquer_sessions(s, u["id"], "totp_reinitialise")
    s.execute(
        update(APPAREIL)
        .where(APPAREIL.c.utilisateur_id == u["id"], APPAREIL.c.revoque_le.is_(None))
        .values(revoque_le=maintenant)
    )
    invalider_invitations(s, u["id"])
    invalider_reinitialisations(s, u["id"])
    _journaliser(s, "acces_reinitialise", u["id"], par, {"statut": u["statut"]}, {"statut": "invite"}, ip)


def reinitialiser_acces(fabrique: Fabrique, par: UUID, utilisateur_id: UUID, ip: str | None) -> None:
    """Retour au statut invité : mot de passe, secret TOTP et codes de secours effacés, sessions et appareils
    révoqués, nouveau lien d'activation de 7 jours envoyé par le job. Jamais sur son propre accès (commande
    locale seulement) ni sur un compte suspendu (à réactiver d'abord)."""
    if utilisateur_id == par:
        raise refuser(409, "son_propre_acces", "utilisateurs.son_propre_acces")
    with fabrique() as s, s.begin():
        maintenant = s.execute(select(func.now())).scalar_one()
        gerants, u = _verrouiller(s, utilisateur_id)
        if u["statut"] == "suspendu":
            raise refuser(409, "acces_suspendu", "utilisateurs.acces_suspendu")
        _dernier_gerant(gerants, u, reste_gerant_actif=False)
        effacer_acces(s, u, maintenant, par, ip)
        JOBS.planifier(
            s,
            "courriel.acces_reinitialise",
            str(uuid7()),
            payload={"utilisateur_id": u["id"], "par_utilisateur_id": par},
        )
