"""Jobs du service et planificateur quotidien (TEC-JOB-01, 02, 06, 07).

Prise par `SKIP LOCKED` avec verrou de 15 min (un job dont le verrou a expiré est repris) ; le traitement
et le passage à `termine` partagent la transaction. Trois tentatives espacées de 1, 10 et 60 min, puis
`echec` ; une `ErreurReseau` reporte le job sans compter de tentative. Le planificateur rattrape les jours
manqués, en date civile Europe/Paris calculée depuis l'horloge de la base. Fonctions synchrones : le worker
les appelle par `asyncio.to_thread`.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    Index,
    Integer,
    MetaData,
    Table,
    Text,
    UniqueConstraint,
    and_,
    func,
    or_,
    select,
    text,
    update,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, insert
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Session

from commun.enveloppe import normaliser_json
from commun.ids import uuid7

log = logging.getLogger("commun.jobs")

STATUTS = ("planifie", "en_cours", "termine", "echec")
DUREE_VERROU = timedelta(minutes=15)
DELAIS_NOUVELLE_TENTATIVE = (timedelta(minutes=1), timedelta(minutes=10), timedelta(minutes=60))
MAX_TENTATIVES = 3
DELAI_ERREUR_RESEAU = timedelta(minutes=1)
FUSEAU = "Europe/Paris"
HEURE_TICK = 4

Issue = Literal["termine", "reessai", "reporte", "echec"]


class ErreurReseau(Exception):
    """Panne passagère d'une dépendance (SMTP, NATS, service interne) : ne compte pas comme tentative."""


@dataclass(frozen=True)
class Job:
    id: UUID
    type: str
    cle: str
    tentatives: int
    payload: dict[str, Any] = field(default_factory=dict)


Gestionnaire = Callable[[Session, Job], None]


def table_job(metadata: MetaData) -> Table:
    table = Table(
        "job",
        metadata,
        Column("id", PG_UUID(as_uuid=True), primary_key=True),
        Column("type", Text, nullable=False),
        Column("cle", Text, nullable=False),
        Column("statut", Text, nullable=False, server_default="planifie"),
        Column("planifie_pour", TIMESTAMP(timezone=True), nullable=False, server_default=func.now()),
        Column("tentatives", Integer, nullable=False, server_default="0"),
        Column("verrouille_jusqu", TIMESTAMP(timezone=True)),
        Column("derniere_erreur", Text),
        Column("payload", JSONB, nullable=False, server_default=text("'{}'::jsonb")),
        Column("cree_le", TIMESTAMP(timezone=True), nullable=False, server_default=func.now()),
        Column("termine_le", TIMESTAMP(timezone=True)),
        UniqueConstraint("type", "cle", name="uq_job_type_cle"),
        CheckConstraint("statut IN ('planifie', 'en_cours', 'termine', 'echec')", name="ck_job_statut"),
    )
    # TEC-DAT-08
    Index("ix_job_statut_planifie_pour", table.c.statut, table.c.planifie_pour)
    return table


def table_planificateur(metadata: MetaData) -> Table:
    return Table(
        "planificateur",
        metadata,
        Column("nom", Text, primary_key=True),
        Column("dernier_tick", Date, nullable=False),
    )


class Jobs:
    def __init__(self, table_job: Table, table_planificateur: Table) -> None:
        self.job = table_job
        self.planificateur = table_planificateur

    def planifier(
        self,
        session: Session,
        type: str,
        cle: str,
        planifie_pour: Any = None,
        payload: dict[str, Any] | None = None,
    ) -> bool:
        """Crée le job s'il n'existe pas déjà pour (type, clé d'idempotence) ; True s'il a été créé."""
        valeurs: dict[str, Any] = {
            "id": uuid7(),
            "type": type,
            "cle": cle,
            "payload": normaliser_json(payload or {}, "payload"),
        }
        if planifie_pour is not None:
            valeurs["planifie_pour"] = planifie_pour
        cree = session.execute(
            insert(self.job)
            .values(**valeurs)
            .on_conflict_do_nothing(constraint="uq_job_type_cle")
            .returning(self.job.c.id)
        ).first()
        return cree is not None

    def prendre(self, session: Session) -> Job | None:
        """TEC-JOB-01 : prend le job dû le plus ancien (ou au verrou expiré) et le verrouille 15 min."""
        j = self.job
        candidat = (
            select(j.c.id)
            .where(
                or_(
                    and_(j.c.statut == "planifie", j.c.planifie_pour <= func.now()),
                    and_(j.c.statut == "en_cours", j.c.verrouille_jusqu < func.now()),
                )
            )
            .order_by(j.c.planifie_pour)
            .limit(1)
            .with_for_update(skip_locked=True)
            .scalar_subquery()
        )
        ligne = (
            session.execute(
                update(j)
                .where(j.c.id == candidat)
                .values(statut="en_cours", verrouille_jusqu=func.now() + DUREE_VERROU)
                .returning(j.c.id, j.c.type, j.c.cle, j.c.tentatives, j.c.payload)
            )
            .mappings()
            .first()
        )
        if ligne is None:
            return None
        return Job(
            id=ligne["id"],
            type=ligne["type"],
            cle=ligne["cle"],
            tentatives=ligne["tentatives"],
            payload=ligne["payload"],
        )

    def executer_un(
        self, fabrique: Callable[[], Session], gestionnaires: Mapping[str, Gestionnaire]
    ) -> Issue | None:
        """Prend et exécute un job dû ; None s'il n'y en a aucun."""
        with fabrique() as session, session.begin():
            job = self.prendre(session)
        if job is None:
            return None
        gestionnaire = gestionnaires.get(job.type)
        if gestionnaire is None:
            return self._echouer(fabrique, job, f"aucun gestionnaire pour le type {job.type}", definitif=True)
        try:
            with fabrique() as session, session.begin():
                gestionnaire(session, job)
                session.execute(
                    update(self.job)
                    .where(self.job.c.id == job.id)
                    .values(
                        statut="termine", termine_le=func.now(), verrouille_jusqu=None, derniere_erreur=None
                    )
                )
        except ErreurReseau as exc:
            log.warning("job reporté (erreur réseau)", extra={"job_id": str(job.id), "type": job.type})
            with fabrique() as session, session.begin():
                session.execute(
                    update(self.job)
                    .where(self.job.c.id == job.id)
                    .values(
                        statut="planifie",
                        planifie_pour=func.now() + DELAI_ERREUR_RESEAU,
                        verrouille_jusqu=None,
                        derniere_erreur=_resume(exc),
                    )
                )
            return "reporte"
        except Exception as exc:
            return self._echouer(fabrique, job, _resume(exc), definitif=False)
        return "termine"

    def _echouer(self, fabrique: Callable[[], Session], job: Job, erreur: str, definitif: bool) -> Issue:
        tentatives = MAX_TENTATIVES if definitif else job.tentatives + 1
        valeurs: dict[str, Any] = {
            "tentatives": tentatives,
            "verrouille_jusqu": None,
            "derniere_erreur": erreur,
        }
        if tentatives >= MAX_TENTATIVES:
            valeurs["statut"] = "echec"
            issue: Issue = "echec"
            log.error("job en échec définitif", extra={"job_id": str(job.id), "type": job.type})
        else:
            valeurs["statut"] = "planifie"
            valeurs["planifie_pour"] = func.now() + DELAIS_NOUVELLE_TENTATIVE[tentatives - 1]
            issue = "reessai"
            log.warning(
                "job en échec, nouvelle tentative prévue", extra={"job_id": str(job.id), "type": job.type}
            )
        with fabrique() as session, session.begin():
            session.execute(update(self.job).where(self.job.c.id == job.id).values(**valeurs))
        return issue

    def compter_en_echec(self, session: Session) -> int:
        return int(
            session.scalar(select(func.count()).select_from(self.job).where(self.job.c.statut == "echec"))
            or 0
        )

    def tick(
        self,
        fabrique: Callable[[], Session],
        nom: str,
        planifier_jour: Callable[[Session, date], None],
        heure_tick: int = HEURE_TICK,
    ) -> list[date]:
        """TEC-JOB-06 : planifie une fois chaque jour écoulé depuis le dernier passage.

        Un jour n'est planifié qu'à partir de `heure_tick` heures (Europe/Paris) : avant 04:00, le jour civil
        courant est encore celui de la veille pour le planificateur.
        """
        p = self.planificateur
        heure_locale = func.timezone(FUSEAU, func.now()) - timedelta(hours=heure_tick)
        with fabrique() as session, session.begin():
            aujourd_hui: date = session.scalar(select(func.date(heure_locale)))  # type: ignore[assignment]
            dernier = session.scalar(select(p.c.dernier_tick).where(p.c.nom == nom).with_for_update())
            debut = aujourd_hui if dernier is None else dernier + timedelta(days=1)
            jours = [debut + timedelta(days=n) for n in range((aujourd_hui - debut).days + 1)]
            for jour in jours:
                planifier_jour(session, jour)
            session.execute(
                insert(p)
                .values(nom=nom, dernier_tick=aujourd_hui)
                .on_conflict_do_update(index_elements=[p.c.nom], set_={"dernier_tick": aujourd_hui})
            )
        return jours


def _resume(exc: BaseException) -> str:
    return f"{type(exc).__name__} : {exc}"[:500]
