from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import date

import pytest
from sqlalchemy import func, insert, select
from sqlalchemy.orm import Session, sessionmaker

from app.models import ETAT_WORKER, JOB, JOBS, OUTBOX, OUTBOX_SVC
from app.worker import GESTIONNAIRES, Worker, planifier_jour
from commun.enveloppe import Enveloppe, nouvelle_enveloppe
from commun.ids import uuid7
from commun.jobs import Job

pytestmark = pytest.mark.integration


@dataclass
class PublieurFactice:
    publies: list[str] = field(default_factory=list)

    async def publier(self, sujet: str, donnees: bytes, id_message: str) -> None:
        self.publies.append(id_message)


def _env() -> Enveloppe:
    return nouvelle_enveloppe(
        type="essai.cree", version=1, producer="identity", aggregate_id=uuid7(), payload={}
    )


def test_gabarit__aucun_job_ni_planification_metier_par_defaut(fabrique: sessionmaker[Session]) -> None:
    assert GESTIONNAIRES == {}
    with fabrique() as s, s.begin():
        planifier_jour(s, date(2026, 10, 4))
    with fabrique() as s:
        assert s.scalar(select(func.count()).select_from(JOB)) == 0


async def test_un_tour__relaie_execute_planifie_et_signale_sa_presence(
    fabrique: sessionmaker[Session],
) -> None:
    env = _env()
    with fabrique() as s, s.begin():
        OUTBOX_SVC.ajouter(s, env)
        JOBS.planifier(s, "essai.effet", "1", planifie_pour=func.now())
    executes: list[str] = []
    jours: list[date] = []

    def gestionnaire(session: Session, job: Job) -> None:
        executes.append(job.cle)

    def planifier(session: Session, jour: date) -> None:
        jours.append(jour)

    publieur = PublieurFactice()
    worker = Worker(
        nom="essai",
        fabrique_session=fabrique,
        publieur=publieur,
        gestionnaires={"essai.effet": gestionnaire},
        planificateur=planifier,
        heure_tick=0,
    )
    assert await worker.un_tour() == {"relayes": 1, "jobs": 1, "jours_planifies": 1}
    assert publieur.publies == [str(env.id)]
    assert executes == ["1"]
    assert len(jours) == 1
    with fabrique() as s:
        assert s.scalar(select(ETAT_WORKER.c.vu_le).where(ETAT_WORKER.c.nom == "essai")) is not None
        assert s.scalar(select(func.count()).select_from(OUTBOX).where(OUTBOX.c.relaye_le.is_(None))) == 0
    assert await worker.un_tour() == {"relayes": 0, "jobs": 0, "jours_planifies": 0}


async def test_tourner__erreur_d_un_tour_journalisee_puis_arret_sur_demande(
    fabrique: sessionmaker[Session],
) -> None:
    tours = 0

    class WorkerFragile(Worker):
        async def un_tour(self) -> dict[str, int]:
            nonlocal tours
            tours += 1
            if tours == 1:
                raise RuntimeError("panne passagère")
            arret.set()
            return {}

    arret = asyncio.Event()
    worker = WorkerFragile(nom="essai", fabrique_session=fabrique, publieur=PublieurFactice())
    await asyncio.wait_for(worker.tourner(0.01, arret), timeout=5)
    assert tours == 2


async def test_battement__mis_a_jour_a_chaque_tour(fabrique: sessionmaker[Session]) -> None:
    with fabrique() as s, s.begin():
        s.execute(
            insert(ETAT_WORKER).values(nom="essai", vu_le=func.now() - func.make_interval(0, 0, 0, 0, 1))
        )
    worker = Worker(nom="essai", fabrique_session=fabrique, publieur=PublieurFactice(), heure_tick=0)
    await worker.un_tour()
    with fabrique() as s:
        maintenant, vu_le = s.execute(
            select(func.now(), ETAT_WORKER.c.vu_le).where(ETAT_WORKER.c.nom == "essai")
        ).one()
    assert (maintenant - vu_le).total_seconds() < 5
