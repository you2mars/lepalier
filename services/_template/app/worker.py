"""Worker du service : relais outbox, jobs dus, planificateur quotidien, battement lu par /internal/healthz.

Les accès base passent par `asyncio.to_thread` (fonctions synchrones de `commun`). Les consommateurs NATS du
service s'ajoutent ici avec `commun.inbox.consommer_message`.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import signal
from collections.abc import Callable, Mapping
from datetime import date
from typing import cast

import nats
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db import fabrique
from app.models import ETAT_WORKER, JOBS, OUTBOX_SVC
from app.settings import settings
from commun.enveloppe import Producteur
from commun.jobs import HEURE_TICK, Gestionnaire
from commun.outbox import Publieur, PublieurJetStream, assurer_flux

log = logging.getLogger("worker")

MAX_JOBS_PAR_TOUR = 20

# Type de job → gestionnaire (SPEC_TECHNIQUE § 6.1) ; à compléter par le service.
GESTIONNAIRES: dict[str, Gestionnaire] = {}


def planifier_jour(session: Session, jour: date) -> None:
    """Jobs quotidiens du service pour `jour` (JOBS.planifier avec clé d'idempotence) ; à compléter."""


class Worker:
    def __init__(
        self,
        *,
        nom: str,
        fabrique_session: Callable[[], Session],
        publieur: Publieur,
        gestionnaires: Mapping[str, Gestionnaire] = GESTIONNAIRES,
        planificateur: Callable[[Session, date], None] = planifier_jour,
        heure_tick: int = HEURE_TICK,
    ) -> None:
        self.nom = nom
        self.fabrique = fabrique_session
        self.publieur = publieur
        self.gestionnaires = gestionnaires
        self.planificateur = planificateur
        self.heure_tick = heure_tick

    async def un_tour(self) -> dict[str, int]:
        relayes = await OUTBOX_SVC.relayer(self.fabrique, self.publieur)
        jobs = 0
        while jobs < MAX_JOBS_PAR_TOUR:
            issue = await asyncio.to_thread(JOBS.executer_un, self.fabrique, self.gestionnaires)
            if issue is None:
                break
            jobs += 1
        jours = await asyncio.to_thread(
            JOBS.tick, self.fabrique, self.nom, self.planificateur, self.heure_tick
        )
        await asyncio.to_thread(self._battement)
        return {"relayes": relayes, "jobs": jobs, "jours_planifies": len(jours)}

    def _battement(self) -> None:
        with self.fabrique() as session, session.begin():
            session.execute(
                insert(ETAT_WORKER)
                .values(nom=self.nom, vu_le=func.now())
                .on_conflict_do_update(index_elements=[ETAT_WORKER.c.nom], set_={"vu_le": func.now()})
            )

    async def tourner(self, intervalle: float, arret: asyncio.Event) -> None:
        """Enchaîne les tours jusqu'à l'arrêt ; un tour en erreur est journalisé sans arrêter le worker."""
        while not arret.is_set():
            try:
                await self.un_tour()
            except Exception:
                log.exception("tour du worker en erreur")
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(arret.wait(), timeout=intervalle)


async def main() -> None:  # pragma: no cover - lancé par supervisord, couvert par les tests de chorégraphie
    client = await nats.connect(settings.nats_url)
    js = client.jetstream()
    await assurer_flux(js, cast(Producteur, settings.service_name))
    worker = Worker(nom=settings.service_name, fabrique_session=fabrique(), publieur=PublieurJetStream(js))
    arret = asyncio.Event()
    boucle = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        boucle.add_signal_handler(sig, arret.set)
    log.info("worker %s démarré (env=%s)", settings.service_name, settings.env)
    try:
        await worker.tourner(settings.intervalle_worker_secondes, arret)
    finally:
        await client.drain()


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(
        level=logging.INFO, format='{"t":"%(asctime)s","lvl":"%(levelname)s","msg":"%(message)s"}'
    )
    asyncio.run(main())
