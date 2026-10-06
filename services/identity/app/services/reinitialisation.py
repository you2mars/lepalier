"""Réinitialisation du mot de passe par lien e-mail (ADR 0006, TEC-SEC-01).

Demande : même réponse quel que soit le compte (existant, inconnu, invité, suspendu) et même travail en
base, pour que ni le message ni le temps de réponse ne révèlent qui a un compte ; 3 demandes par heure et par
compte, les suivantes sont ignorées en silence. Fin : lien valable 1 h, verrou par couple (compte, IP)
consulté avant le code, code TOTP ou de secours exigé, 5 codes faux invalident le lien ; un mot de passe
changé ferme toutes les sessions et révoque tous les appareils. Un refus (verrou, mot de passe) ne consomme
aucun code.
"""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.engines import durees
from app.engines.chiffrement import pseudonymiser
from app.engines.jetons import empreinte
from app.engines.mot_de_passe import hacher, motif_refus
from app.engines.verrouillage import PERIODE_REINITIALISATION, reinitialisation_autorisee
from app.jobs.courriels import invalider_invitations, invalider_reinitialisations
from app.libelles import message_mot_de_passe
from app.models import APPAREIL, JOB, JOBS, JOURNAL_SVC, REINITIALISATION, SESSION, UTILISATEUR
from app.securite import ClesCompte
from app.services.activation import mots_de_passe_courants
from app.services.connexion import couple_verrouille, noter_tentative, verifier_code
from app.services.refus import refuser, refuser_texte
from commun.erreurs import ErreurApi
from commun.ids import uuid7

Fabrique = Callable[[], Session]
# identifiant d'aucun compte : la requête de décompte est faite aussi pour une adresse inconnue
_PERSONNE = UUID(int=0)


def demander(fabrique: Fabrique, email: str, ip: str) -> None:
    with fabrique() as s, s.begin():
        maintenant = s.execute(select(func.now())).scalar_one()
        u = (
            s.execute(
                select(UTILISATEUR.c.id, UTILISATEUR.c.statut)
                .where(func.lower(UTILISATEUR.c.email) == email.strip().lower())
                .with_for_update()
            )
            .mappings()
            .first()
        )
        demandes = (
            s.execute(
                select(JOB.c.cree_le).where(
                    JOB.c.type == "courriel.reinitialisation",
                    JOB.c.payload["utilisateur_id"].astext == str(u["id"] if u else _PERSONNE),
                    JOB.c.cree_le > maintenant - PERIODE_REINITIALISATION,
                )
            )
            .scalars()
            .all()
        )
        if u is None or u["statut"] != "actif" or not reinitialisation_autorisee(demandes, maintenant):
            return
        invalider_reinitialisations(s, u["id"])
        JOBS.planifier(s, "courriel.reinitialisation", str(uuid7()), payload={"utilisateur_id": u["id"]})
        JOURNAL_SVC.ecrire(
            s,
            action="utilisateur.reinitialisation_demandee",
            table_cible="utilisateur",
            enregistrement_id=u["id"],
            ip=ip,
        )


def terminer(fabrique: Fabrique, jeton: str, mot_de_passe: str, code: str, ip: str, cles: ClesCompte) -> None:
    """Un code faux est inscrit (tentative, compteur du lien) ; le refus est levé après le commit."""
    refus: ErreurApi | None = None
    with fabrique() as s, s.begin():
        maintenant = s.execute(select(func.now())).scalar_one()
        lien = (
            s.execute(
                select(REINITIALISATION)
                .where(
                    REINITIALISATION.c.empreinte == empreinte(jeton),
                    REINITIALISATION.c.utilisee_le.is_(None),
                    REINITIALISATION.c.invalidee_le.is_(None),
                    REINITIALISATION.c.expire_le > maintenant,
                )
                .with_for_update()
            )
            .mappings()
            .first()
        )
        u = None
        if lien is not None:
            u = (
                s.execute(
                    select(UTILISATEUR).where(UTILISATEUR.c.id == lien["utilisateur_id"]).with_for_update()
                )
                .mappings()
                .one()
            )
        if lien is None or u is None or u["statut"] != "actif":
            raise refuser(410, "lien_invalide", "reinitialisation.lien_invalide")
        cle_compte = pseudonymiser(u["email"], cles.pseudonymisation)
        if couple_verrouille(s, cle_compte, ip, maintenant):
            raise refuser(429, "trop_d_essais", "connexion.trop_d_essais")
        motif = motif_refus(mot_de_passe, u["email"], mots_de_passe_courants())
        if motif is not None:
            raise refuser_texte(422, "mot_de_passe_refuse", message_mot_de_passe(motif), "mot_de_passe")
        etape, reussi = verifier_code(s, u, code, maintenant, cles)
        if not reussi:
            noter_tentative(s, cle_compte, u["id"], ip, etape, False)
            essais = lien["essais_code"] + 1
            valeurs: dict[str, object] = {"essais_code": essais}
            if essais >= durees.ESSAIS_CODE_REINITIALISATION:
                valeurs["invalidee_le"] = maintenant
                refus = refuser(400, "trop_de_codes", "reinitialisation.trop_de_codes", "code")
            else:
                refus = refuser(400, "code_incorrect", "code.incorrect", "code")
            s.execute(update(REINITIALISATION).where(REINITIALISATION.c.id == lien["id"]).values(**valeurs))
        else:
            s.execute(
                update(UTILISATEUR)
                .where(UTILISATEUR.c.id == u["id"])
                .values(mot_de_passe_hache=hacher(mot_de_passe), mot_de_passe_change_le=maintenant)
            )
            s.execute(
                update(REINITIALISATION)
                .where(REINITIALISATION.c.id == lien["id"])
                .values(utilisee_le=maintenant)
            )
            invalider_reinitialisations(s, u["id"])
            invalider_invitations(s, u["id"])
            s.execute(
                update(SESSION)
                .where(SESSION.c.utilisateur_id == u["id"], SESSION.c.revoquee_le.is_(None))
                .values(revoquee_le=maintenant, motif_revocation="reinitialisation")
            )
            s.execute(
                update(APPAREIL)
                .where(APPAREIL.c.utilisateur_id == u["id"], APPAREIL.c.revoque_le.is_(None))
                .values(revoque_le=maintenant)
            )
            JOBS.planifier(
                s,
                "courriel.mot_de_passe_change",
                f"{u['id']}:{maintenant:%Y%m%d%H%M%S%f}",
                payload={"utilisateur_id": u["id"], "instant": maintenant},
            )
            JOURNAL_SVC.ecrire(
                s,
                action="utilisateur.mot_de_passe_reinitialise",
                table_cible="utilisateur",
                enregistrement_id=u["id"],
                utilisateur_id=u["id"],
                ip=ip,
            )
    if refus is not None:
        raise refus
