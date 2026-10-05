"""Purges quotidiennes (TEC-DAT-02) : suppression physique autorisée pour les sessions de plus de 90 jours,
les tentatives de connexion de plus de 30 jours, les clés d'idempotence expirées, les jobs terminés depuis
plus de 90 jours et les événements de l'outbox relayés depuis plus de 30 jours ; une ligne de journal par
purge, avec le nombre de lignes supprimées. Planifiées chaque jour par `planifier_jour`, clé = le jour."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import Table, delete, func
from sqlalchemy.orm import Session

from app.models import IDEMPOTENCE, JOB, JOBS, JOURNAL_SVC, OUTBOX, SESSION, TENTATIVE_CONNEXION
from commun.jobs import Gestionnaire, Job

CONSERVATION_SESSIONS = timedelta(days=90)
CONSERVATION_TENTATIVES = timedelta(days=30)
CONSERVATION_JOBS_TERMINES = timedelta(days=90)
CONSERVATION_OUTBOX_RELAYEE = timedelta(days=30)


def _journaliser(s: Session, job: Job, table: Table, supprimees: int) -> None:
    JOURNAL_SVC.ecrire(
        s,
        action=job.type,
        table_cible=table.name,
        enregistrement_id=job.id,
        apres={"supprimees": supprimees, "jour": job.cle},
    )


def purger_sessions(s: Session, job: Job) -> None:
    resultat = s.execute(delete(SESSION).where(SESSION.c.cree_le < func.now() - CONSERVATION_SESSIONS))
    _journaliser(s, job, SESSION, resultat.rowcount)  # type: ignore[attr-defined]


def purger_tentatives(s: Session, job: Job) -> None:
    t = TENTATIVE_CONNEXION
    resultat = s.execute(delete(t).where(t.c.cree_le < func.now() - CONSERVATION_TENTATIVES))
    _journaliser(s, job, t, resultat.rowcount)  # type: ignore[attr-defined]


def purger_idempotence(s: Session, job: Job) -> None:
    resultat = s.execute(delete(IDEMPOTENCE).where(IDEMPOTENCE.c.expire_le <= func.now()))
    _journaliser(s, job, IDEMPOTENCE, resultat.rowcount)  # type: ignore[attr-defined]


def purger_jobs(s: Session, job: Job) -> None:
    """Jobs terminés seulement : un job en échec reste visible (TEC-JOB-02)."""
    resultat = s.execute(
        delete(JOB).where(
            JOB.c.statut == "termine", JOB.c.termine_le < func.now() - CONSERVATION_JOBS_TERMINES
        )
    )
    _journaliser(s, job, JOB, resultat.rowcount)  # type: ignore[attr-defined]


def purger_outbox(s: Session, job: Job) -> None:
    """Événements déjà relayés seulement : ils restent dans le flux JetStream (rétention illimitée)."""
    resultat = s.execute(delete(OUTBOX).where(OUTBOX.c.relaye_le < func.now() - CONSERVATION_OUTBOX_RELAYEE))
    _journaliser(s, job, OUTBOX, resultat.rowcount)  # type: ignore[attr-defined]


GESTIONNAIRES: dict[str, Gestionnaire] = {
    "purge.sessions": purger_sessions,
    "purge.tentatives": purger_tentatives,
    "purge.idempotence": purger_idempotence,
    "purge.jobs": purger_jobs,
    "purge.outbox": purger_outbox,
}


def planifier(s: Session, jour: date) -> None:
    for type_ in GESTIONNAIRES:
        JOBS.planifier(s, type_, jour.isoformat())
