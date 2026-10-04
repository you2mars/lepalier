from __future__ import annotations

import asyncio
import logging

from app.settings import settings

log = logging.getLogger("worker")


async def main() -> None:
    """Boucle du worker : relais outbox, consommateurs NATS, jobs (TEC-JOB-01…08). Squelette à compléter."""
    log.info("worker %s démarré (env=%s)", settings.service_name, settings.env)
    while True:
        await asyncio.sleep(2)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='{"t":"%(asctime)s","lvl":"%(levelname)s","msg":"%(message)s"}')
    asyncio.run(main())
