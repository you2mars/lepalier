"""Activation d'un compte invité depuis le lien reçu par e-mail (APP-USR-01, ADR 0006).

Début : le secret TOTP est créé au premier appel et chiffré ; tant que le lien est valable, chaque appel
renvoie le même secret (rechargement de la page). Fin : mot de passe, code du nouveau secret et, si besoin,
nouveau nom affiché ; tout est écrit dans une seule transaction (compte actif, codes de secours, lien utilisé,
événement `utilisateur.cree` à la première activation, journal, session complète) ou rien ne l'est.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from functools import cache
from pathlib import Path
from typing import Any

from sqlalchemy import func, insert, select, update
from sqlalchemy.orm import Session

from app.engines import codes_secours, totp
from app.engines.chiffrement import chiffrer, dechiffrer
from app.engines.jetons import empreinte
from app.engines.mot_de_passe import hacher, lire_courants, motif_refus
from app.libelles import message_mot_de_passe
from app.models import CODE_SECOURS, INVITATION, JOURNAL_SVC, OUTBOX_SVC, UTILISATEUR
from app.securite import ClesCompte
from app.services.connexion import ouvrir_session
from app.services.refus import refuser, refuser_texte
from commun.enveloppe import Enveloppe
from commun.ids import uuid7
from commun.trace import trace_id_courant

Fabrique = Callable[[], Session]
COURANTS = Path(__file__).resolve().parents[1] / "engines" / "donnees" / "mots_de_passe_courants.txt"


@cache
def mots_de_passe_courants() -> frozenset[str]:
    return lire_courants(COURANTS.read_text())


@dataclass(frozen=True)
class Activation:
    jeton_session: str
    jeton_appareil: str | None
    codes_secours: list[str]
    nom_affiche: str
    role: str


def _lien(s: Session, jeton: str, maintenant: datetime) -> tuple[Any, Any]:
    """(lien, utilisateur) verrouillés, ou refus 410 : lien inconnu, expiré, utilisé ou remplacé."""
    lien = (
        s.execute(
            select(INVITATION)
            .where(
                INVITATION.c.empreinte == empreinte(jeton),
                INVITATION.c.utilisee_le.is_(None),
                INVITATION.c.invalidee_le.is_(None),
                INVITATION.c.expire_le > maintenant,
            )
            .with_for_update()
        )
        .mappings()
        .first()
    )
    u = None
    if lien is not None:
        u = (
            s.execute(select(UTILISATEUR).where(UTILISATEUR.c.id == lien["utilisateur_id"]).with_for_update())
            .mappings()
            .one()
        )
    if lien is None or u is None or u["statut"] != "invite":
        raise refuser(410, "lien_invalide", "invitation.lien_invalide")
    return lien, u


def _maintenant(s: Session) -> datetime:
    return s.execute(select(func.now())).scalar_one()


def debut(fabrique: Fabrique, jeton: str, cles: ClesCompte) -> dict[str, str]:
    with fabrique() as s, s.begin():
        _, u = _lien(s, jeton, _maintenant(s))
        if u["totp_secret_chiffre"] is None:
            secret = totp.nouveau_secret()
            s.execute(
                update(UTILISATEUR)
                .where(UTILISATEUR.c.id == u["id"])
                .values(
                    totp_secret_chiffre=chiffrer(secret, cles.chiffrement, u["id"].bytes),
                    totp_dernier_pas=None,
                )
            )
        else:
            secret = dechiffrer(u["totp_secret_chiffre"], cles.chiffrement, u["id"].bytes)
        return {
            "uri_otpauth": totp.uri_provisionnement(secret, u["nom_affiche"]),
            "nom_affiche": u["nom_affiche"],
        }


def fin(
    fabrique: Fabrique,
    jeton: str,
    mot_de_passe: str,
    code: str,
    nom_affiche: str | None,
    ip: str,
    jeton_appareil: str | None,
    cles: ClesCompte,
) -> Activation:
    with fabrique() as s, s.begin():
        maintenant = _maintenant(s)
        lien, u = _lien(s, jeton, maintenant)
        motif = motif_refus(mot_de_passe, u["email"], mots_de_passe_courants())
        if motif is not None:
            raise refuser_texte(422, "mot_de_passe_refuse", message_mot_de_passe(motif), "mot_de_passe")
        pas = None
        if u["totp_secret_chiffre"] is not None:
            secret = dechiffrer(u["totp_secret_chiffre"], cles.chiffrement, u["id"].bytes)
            pas = totp.verifier(secret, code, maintenant.timestamp(), u["totp_dernier_pas"])
        if pas is None:
            raise refuser(400, "code_incorrect", "activation.code_incorrect", "code")

        nom = nom_affiche or u["nom_affiche"]
        premiere = u["active_le"] is None
        s.execute(
            update(UTILISATEUR)
            .where(UTILISATEUR.c.id == u["id"])
            .values(
                mot_de_passe_hache=hacher(mot_de_passe),
                mot_de_passe_change_le=maintenant,
                nom_affiche=nom,
                statut="actif",
                active_le=func.coalesce(UTILISATEUR.c.active_le, maintenant),
                totp_dernier_pas=pas,
            )
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
        codes = codes_secours.generer()
        s.execute(
            insert(CODE_SECOURS),
            [
                {
                    "id": uuid7(),
                    "utilisateur_id": u["id"],
                    "empreinte": codes_secours.hacher(c),
                    "genere_le": maintenant,
                }
                for c in codes
            ],
        )
        s.execute(update(INVITATION).where(INVITATION.c.id == lien["id"]).values(utilisee_le=maintenant))
        if premiere:
            # une nouvelle activation après réinitialisation de l'accès ne publie rien (ADR 0006)
            OUTBOX_SVC.ajouter(
                s,
                Enveloppe(
                    id=uuid7(),
                    type="utilisateur.cree",
                    version=1,
                    occurred_at=maintenant,
                    producer="identity",
                    aggregate_id=u["id"],
                    trace_id=trace_id_courant(),
                    payload={
                        "utilisateur_id": u["id"],
                        "role": u["role"],
                        "associe_id": u["associe_id"],
                        "nom_affiche": nom,
                        "par_utilisateur_id": lien["par_utilisateur_id"],
                    },
                ),
            )
        JOURNAL_SVC.ecrire(
            s,
            action="utilisateur.active",
            table_cible="utilisateur",
            enregistrement_id=u["id"],
            utilisateur_id=u["id"],
            apres={"statut": "actif"},
            ip=ip,
        )
        jeton_session, jeton_appareil_neuf = ouvrir_session(
            s, u["id"], maintenant, ip, jeton_appareil, prevenir=False
        )
        return Activation(jeton_session, jeton_appareil_neuf, codes, nom, u["role"])
