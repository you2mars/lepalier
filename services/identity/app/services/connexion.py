"""Connexion, second facteur, déconnexion et vérification de session (ADR 0006, TEC-SEC-01, TEC-SEC-02).

Chaque fonction ouvre sa propre transaction : un refus est décidé dans la transaction (tentative, compteur,
révocation écrits), puis levé après le commit, pour que ces écritures ne soient pas annulées.

Seule une connexion complète (mot de passe et code) compte comme une réussite pour le verrouillage : un mot de
passe juste ne remet pas le compteur à zéro, sans quoi les codes pourraient être essayés sans limite.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, insert, select, text, update
from sqlalchemy.orm import Session

from app.engines import codes_secours, durees, totp
from app.engines.chiffrement import dechiffrer, pseudonymiser
from app.engines.jetons import empreinte, nouveau_jeton
from app.engines.mot_de_passe import hacher, rehachage_necessaire, verifier, verifier_factice
from app.engines.verrouillage import PERIODE_ALERTE, Tentative, alerte_compte, verrou_couple
from app.models import APPAREIL, CODE_SECOURS, JOBS, JOURNAL_SVC, SESSION, TENTATIVE_CONNEXION, UTILISATEUR
from app.securite import ClesCompte
from app.services.refus import refuser
from commun.erreurs import ErreurApi
from commun.identite import entetes_signes
from commun.ids import uuid7

VALIDITE_ENTETES_SECONDES = 60
HISTORIQUE_VERROU = timedelta(hours=1)
_SAISIE_TOTP = re.compile(r"^[0-9]{6}$")

Fabrique = Callable[[], Session]


@dataclass(frozen=True)
class SessionOuverte:
    jeton_session: str
    jeton_appareil: str | None
    nom_affiche: str
    role: str


def _maintenant(s: Session) -> datetime:
    return s.execute(select(func.now())).scalar_one()


def noter_tentative(
    s: Session, cle_compte: bytes, utilisateur_id: UUID | None, ip: str, etape: str, reussie: bool
) -> None:
    s.execute(
        insert(TENTATIVE_CONNEXION).values(
            id=uuid7(),
            cle_compte=cle_compte,
            utilisateur_id=utilisateur_id,
            ip=ip,
            etape=etape,
            reussie=reussie,
        )
    )


def couple_verrouille(s: Session, cle_compte: bytes, ip: str, maintenant: datetime) -> bool:
    t = TENTATIVE_CONNEXION
    lignes = s.execute(
        select(t.c.cree_le, t.c.reussie).where(
            t.c.cle_compte == cle_compte, t.c.ip == ip, t.c.cree_le > maintenant - HISTORIQUE_VERROU
        )
    ).all()
    tentatives = [Tentative(instant=cree_le, reussie=reussie) for cree_le, reussie in lignes]
    return verrou_couple(tentatives, maintenant) is not None


# --- étape 1 : adresse e-mail et mot de passe -----------------------------------------------------------


def connecter(fabrique: Fabrique, email: str, mot_de_passe: str, ip: str, cles: ClesCompte) -> str:
    """Ouvre une pré-session (jeton du cookie lp_pre) ou lève le refus adapté."""
    refus: ErreurApi | None = None
    jeton = ""
    with fabrique() as s, s.begin():
        maintenant = _maintenant(s)
        cle_compte = pseudonymiser(email, cles.pseudonymisation)
        if couple_verrouille(s, cle_compte, ip, maintenant):
            refus = refuser(429, "trop_d_essais", "connexion.trop_d_essais")
        else:
            u = (
                s.execute(
                    select(UTILISATEUR).where(
                        func.lower(UTILISATEUR.c.email) == email.strip().lower(),
                        UTILISATEUR.c.statut != "annule",
                    )
                )
                .mappings()
                .first()
            )
            if u is None or u["statut"] == "invite" or u["mot_de_passe_hache"] is None:
                verifier_factice(mot_de_passe)
                bon = False
            else:
                bon = verifier(u["mot_de_passe_hache"], mot_de_passe)
            if not bon:
                noter_tentative(s, cle_compte, u["id"] if u else None, ip, "mot_de_passe", False)
                if u is not None:
                    JOURNAL_SVC.ecrire(
                        s,
                        action="connexion.echec",
                        table_cible="utilisateur",
                        enregistrement_id=u["id"],
                        ip=ip,
                    )
                    _alerter_echecs(s, u, cle_compte, maintenant)
                refus = refuser(
                    401, "identifiants_incorrects", "connexion.identifiants_incorrects", "mot_de_passe"
                )
            else:
                assert u is not None
                if rehachage_necessaire(u["mot_de_passe_hache"]):
                    s.execute(
                        update(UTILISATEUR)
                        .where(UTILISATEUR.c.id == u["id"])
                        .values(mot_de_passe_hache=hacher(mot_de_passe))
                    )
                jeton = nouveau_jeton()
                s.execute(
                    insert(SESSION).values(
                        id=uuid7(),
                        empreinte=empreinte(jeton),
                        utilisateur_id=u["id"],
                        etat="pre_totp",
                        cree_le=maintenant,
                        derniere_activite_le=maintenant,
                        expire_le=durees.expiration_pre_session(maintenant),
                        ip_creation=ip,
                    )
                )
    if refus is not None:
        raise refus
    return jeton


# --- étape 2 : code TOTP ou code de secours ---------------------------------------------------------


def verifier_code(
    s: Session, u: Any, saisie: str, maintenant: datetime, cles: ClesCompte
) -> tuple[str, bool]:
    """(étape, réussite) ; anti-rejeu TOTP et usage unique des codes de secours garantis par la base."""
    compacte = "".join(saisie.split()).replace("-", "")
    if _SAISIE_TOTP.fullmatch(compacte):
        secret = dechiffrer(u["totp_secret_chiffre"], cles.chiffrement, u["id"].bytes)
        pas = totp.verifier(secret, compacte, maintenant.timestamp(), u["totp_dernier_pas"])
        if pas is None:
            return "totp", False
        accepte = s.execute(
            update(UTILISATEUR)
            .where(
                UTILISATEUR.c.id == u["id"],
                (UTILISATEUR.c.totp_dernier_pas.is_(None)) | (UTILISATEUR.c.totp_dernier_pas < pas),
            )
            .values(totp_dernier_pas=pas)
            .returning(UTILISATEUR.c.id)
        ).first()
        return "totp", accepte is not None
    disponibles = s.execute(
        select(CODE_SECOURS.c.id, CODE_SECOURS.c.empreinte)
        .where(
            CODE_SECOURS.c.utilisateur_id == u["id"],
            CODE_SECOURS.c.utilise_le.is_(None),
            CODE_SECOURS.c.invalide_le.is_(None),
        )
        .with_for_update()
    ).all()
    index = codes_secours.trouver(saisie, [e for _, e in disponibles])
    if index is None:
        return "secours", False
    s.execute(
        update(CODE_SECOURS).where(CODE_SECOURS.c.id == disponibles[index][0]).values(utilise_le=maintenant)
    )
    return "secours", True


def _revoquer(s: Session, session_id: UUID, motif: str) -> None:
    s.execute(
        update(SESSION)
        .where(SESSION.c.id == session_id, SESSION.c.revoquee_le.is_(None))
        .values(revoquee_le=func.now(), motif_revocation=motif)
    )


def _appareil(
    s: Session, utilisateur_id: UUID, jeton_appareil: str | None, maintenant: datetime, prevenir: bool
) -> tuple[UUID, str | None]:
    """Appareil connu (cookie valide pour cet utilisateur), sinon nouvel appareil ; e-mail si `prevenir`."""
    if jeton_appareil:
        connu = s.execute(
            update(APPAREIL)
            .where(
                APPAREIL.c.empreinte == empreinte(jeton_appareil),
                APPAREIL.c.utilisateur_id == utilisateur_id,
                APPAREIL.c.revoque_le.is_(None),
                APPAREIL.c.expire_le > maintenant,
            )
            .values(vu_le=maintenant)
            .returning(APPAREIL.c.id)
        ).first()
        if connu is not None:
            return connu[0], None
    jeton = nouveau_jeton()
    appareil_id = uuid7()
    s.execute(
        insert(APPAREIL).values(
            id=appareil_id,
            utilisateur_id=utilisateur_id,
            empreinte=empreinte(jeton),
            cree_le=maintenant,
            vu_le=maintenant,
            expire_le=durees.expiration_appareil(maintenant),
        )
    )
    if prevenir:
        JOBS.planifier(
            s,
            "courriel.nouvel_appareil",
            str(appareil_id),
            payload={"utilisateur_id": utilisateur_id, "appareil_id": appareil_id},
        )
    return appareil_id, jeton


def ouvrir_session(
    s: Session,
    utilisateur_id: UUID,
    maintenant: datetime,
    ip: str,
    jeton_appareil: str | None,
    prevenir: bool,
) -> tuple[str, str | None]:
    """Session complète (jeton de lp_session) et, pour un appareil nouveau, jeton de lp_appareil."""
    appareil_id, nouveau_jeton_appareil = _appareil(s, utilisateur_id, jeton_appareil, maintenant, prevenir)
    jeton = nouveau_jeton()
    s.execute(
        insert(SESSION).values(
            id=uuid7(),
            empreinte=empreinte(jeton),
            utilisateur_id=utilisateur_id,
            etat="active",
            cree_le=maintenant,
            derniere_activite_le=maintenant,
            expire_le=durees.expiration_session(maintenant, maintenant),
            appareil_id=appareil_id,
            ip_creation=ip,
        )
    )
    return jeton, nouveau_jeton_appareil


def _alerter_echecs(s: Session, u: Any, cle_compte: bytes, maintenant: datetime) -> None:
    """Alerte aux gérants à 20 échecs par heure sur un compte connu, toutes IP ; une par heure au plus,
    décidée par la base pour que deux requêtes simultanées au seuil n'en envoient qu'une (ADR 0006)."""
    t = TENTATIVE_CONNEXION
    echecs = (
        s.execute(
            select(t.c.cree_le).where(
                t.c.cle_compte == cle_compte,
                t.c.reussie.is_(False),
                t.c.cree_le > maintenant - PERIODE_ALERTE,
            )
        )
        .scalars()
        .all()
    )
    if not alerte_compte(echecs, u["derniere_alerte_echecs_le"], maintenant, compte_connu=True):
        return
    alerte = s.execute(
        update(UTILISATEUR)
        .where(
            UTILISATEUR.c.id == u["id"],
            (UTILISATEUR.c.derniere_alerte_echecs_le.is_(None))
            | (UTILISATEUR.c.derniere_alerte_echecs_le <= maintenant - PERIODE_ALERTE),
        )
        .values(derniere_alerte_echecs_le=maintenant)
        .returning(UTILISATEUR.c.id)
    ).first()
    if alerte is not None:
        JOBS.planifier(
            s,
            "courriel.alerte_echecs",
            f"{u['id']}:{maintenant.isoformat()}",
            payload={"utilisateur_id": u["id"], "instant": maintenant},
        )


def _alerter_compte_suspendu(s: Session, utilisateur_id: UUID, maintenant: datetime) -> None:
    """Au plus une alerte par compte et par heure (ADR 0006), décidée par la base."""
    alerte = s.execute(
        update(UTILISATEUR)
        .where(
            UTILISATEUR.c.id == utilisateur_id,
            (UTILISATEUR.c.derniere_alerte_suspension_le.is_(None))
            | (UTILISATEUR.c.derniere_alerte_suspension_le <= maintenant - timedelta(hours=1)),
        )
        .values(derniere_alerte_suspension_le=maintenant)
        .returning(UTILISATEUR.c.id)
    ).first()
    if alerte is not None:
        JOBS.planifier(
            s,
            "courriel.alerte_compte_suspendu",
            f"{utilisateur_id}:{maintenant:%Y%m%d%H%M%S%f}",
            payload={"utilisateur_id": utilisateur_id, "instant": maintenant},
        )


def valider_code(
    fabrique: Fabrique,
    jeton_pre: str | None,
    saisie: str,
    ip: str,
    jeton_appareil: str | None,
    cles: ClesCompte,
) -> SessionOuverte:
    refus: ErreurApi | None = None
    ouverte: SessionOuverte | None = None
    with fabrique() as s, s.begin():
        maintenant = _maintenant(s)
        pre = (
            s.execute(
                select(SESSION)
                .where(SESSION.c.empreinte == empreinte(jeton_pre or ""), SESSION.c.etat == "pre_totp")
                .with_for_update()
            )
            .mappings()
            .first()
        )
        if pre is None or pre["revoquee_le"] is not None or pre["expire_le"] <= maintenant:
            refus = refuser(401, "delai_depasse", "code.delai_depasse")
        else:
            u = (
                s.execute(select(UTILISATEUR).where(UTILISATEUR.c.id == pre["utilisateur_id"]))
                .mappings()
                .one()
            )
            cle_compte = pseudonymiser(u["email"], cles.pseudonymisation)
            if couple_verrouille(s, cle_compte, ip, maintenant):
                refus = refuser(429, "trop_d_essais", "connexion.trop_d_essais")
            else:
                etape, reussi = verifier_code(s, u, saisie, maintenant, cles)
                if not reussi:
                    noter_tentative(s, cle_compte, u["id"], ip, etape, False)
                    _alerter_echecs(s, u, cle_compte, maintenant)
                    JOURNAL_SVC.ecrire(
                        s,
                        action="connexion.echec",
                        table_cible="utilisateur",
                        enregistrement_id=u["id"],
                        ip=ip,
                    )
                    essais = pre["essais_totp"] + 1
                    s.execute(update(SESSION).where(SESSION.c.id == pre["id"]).values(essais_totp=essais))
                    if durees.pre_session_epuisee(essais):
                        _revoquer(s, pre["id"], "essais_totp")
                        refus = refuser(401, "trop_de_codes", "code.trop_de_codes")
                    else:
                        refus = refuser(401, "code_incorrect", "code.incorrect")
                elif u["statut"] != "actif":
                    _revoquer(s, pre["id"], "suspension")
                    _alerter_compte_suspendu(s, u["id"], maintenant)
                    JOURNAL_SVC.ecrire(
                        s,
                        action="connexion.compte_suspendu",
                        table_cible="utilisateur",
                        enregistrement_id=u["id"],
                        ip=ip,
                    )
                    refus = refuser(403, "compte_suspendu", "connexion.compte_suspendu")
                else:
                    _revoquer(s, pre["id"], "rotation")
                    noter_tentative(s, cle_compte, u["id"], ip, etape, True)
                    jeton, jeton_appareil_neuf = ouvrir_session(
                        s, u["id"], maintenant, ip, jeton_appareil, prevenir=True
                    )
                    JOURNAL_SVC.ecrire(
                        s,
                        action="connexion.reussie",
                        table_cible="utilisateur",
                        enregistrement_id=u["id"],
                        utilisateur_id=u["id"],
                        ip=ip,
                    )
                    ouverte = SessionOuverte(jeton, jeton_appareil_neuf, u["nom_affiche"], u["role"])
    if refus is not None:
        raise refus
    assert ouverte is not None
    return ouverte


# --- déconnexion et vérification (nginx) --------------------------------------------------------------


def deconnecter(fabrique: Fabrique, jeton_session: str | None, ip: str) -> None:
    if not jeton_session:
        return
    with fabrique() as s, s.begin():
        revoquee = s.execute(
            update(SESSION)
            .where(SESSION.c.empreinte == empreinte(jeton_session), SESSION.c.revoquee_le.is_(None))
            .values(revoquee_le=func.now(), motif_revocation="deconnexion")
            .returning(SESSION.c.utilisateur_id)
        ).first()
        if revoquee is not None:
            JOURNAL_SVC.ecrire(
                s,
                action="connexion.deconnexion",
                table_cible="utilisateur",
                enregistrement_id=revoquee[0],
                utilisateur_id=revoquee[0],
                ip=ip,
            )


_VERIFIER = text(
    """
    UPDATE session s
       SET derniere_activite_le = now(),
           expire_le = least(now() + :inactivite, s.cree_le + :duree_max)
      FROM utilisateur u
     WHERE s.empreinte = :empreinte AND s.etat = 'active' AND s.revoquee_le IS NULL AND s.expire_le > now()
       AND u.id = s.utilisateur_id AND u.statut = 'actif'
    RETURNING u.id, u.role, extract(epoch FROM now())::bigint
    """
)


def verifier_session(
    fabrique: Fabrique, jeton_session: str | None, cles: ClesCompte
) -> dict[str, str] | None:
    """En-têtes signés (valables 60 s) pour nginx, ou None : lecture et prolongation en une seule requête."""
    if not jeton_session:
        return None
    with fabrique() as s, s.begin():
        ligne = s.execute(
            _VERIFIER,
            {
                "empreinte": empreinte(jeton_session),
                "inactivite": durees.INACTIVITE_MAX,
                "duree_max": durees.DUREE_MAX_SESSION,
            },
        ).first()
    if ligne is None:
        return None
    utilisateur_id, role, maintenant = ligne
    return entetes_signes(utilisateur_id, role, int(maintenant) + VALIDITE_ENTETES_SECONDES, cles.hmac[0])


# --- motif d'une session devenue invalide (front, après un 401) ------------------------------------------

_SUSPENDUE = text(
    """
    SELECT 1 FROM session s JOIN utilisateur u ON u.id = s.utilisateur_id
     WHERE s.empreinte = :empreinte AND s.motif_revocation = 'suspension' AND u.statut = 'suspendu'
    """
)


def session_suspendue(fabrique: Fabrique, jeton_session: str | None) -> bool:
    """Vrai seulement si cette session a été coupée par une suspension toujours en cours (R0-07)."""
    if not jeton_session:
        return False
    with fabrique() as s:
        return s.execute(_SUSPENDUE, {"empreinte": empreinte(jeton_session)}).first() is not None
