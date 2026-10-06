"""Planificateur quotidien déclenché à la main (make tick, recette) : python -m app.scheduler tick [--jour …].

`tick` fait ce que le worker fait chaque jour à 04:00 (Europe/Paris) : planifier les jobs quotidiens de chaque
jour écoulé depuis le dernier passage (TEC-JOB-06) ; le worker les exécute ensuite. `--jour AAAA-MM-JJ`
planifie un jour donné, même déjà passé (clés d'idempotence : aucun doublon) ; refusé en production.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from datetime import date
from typing import TextIO

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import JOB, JOBS, PLANIFICATEUR
from app.settings import Settings
from app.worker import planifier_jour
from commun.dates import date_en_toutes_lettres

Fabrique = Callable[[], Session]
REFUS_PRODUCTION = "L'option --jour sert au développement et à la recette : elle est refusée en production."


def _compter_jobs(s: Session) -> int:
    return s.execute(select(func.count()).select_from(JOB)).scalar_one()


def planifier_un_jour(fabrique: Fabrique, jour: date) -> str:
    with fabrique() as s, s.begin():
        avant = _compter_jobs(s)
        planifier_jour(s, jour)
        crees = _compter_jobs(s) - avant
    if crees == 0:
        detail = "aucun nouveau job (jour déjà planifié)"
    else:
        detail = f"{crees} job{'s' if crees > 1 else ''} créé{'s' if crees > 1 else ''}"
    return f"Jour du {date_en_toutes_lettres(jour)} : {detail}.\n"


def tick(fabrique: Fabrique, nom: str) -> str:
    jours = JOBS.tick(fabrique, nom, planifier_jour)
    if not jours:
        # jour du planificateur (avant 4 h, c'est encore la veille) : celui du dernier passage
        with fabrique() as s:
            dernier = s.execute(
                select(PLANIFICATEUR.c.dernier_tick).where(PLANIFICATEUR.c.nom == nom)
            ).scalar_one()
        return (
            f"Rien à planifier : les jobs quotidiens du {date_en_toutes_lettres(dernier)} le sont déjà. "
            "Pour un autre jour : --jour AAAA-MM-JJ.\n"
        )
    return "".join(f"Jobs quotidiens planifiés pour le {date_en_toutes_lettres(j)}.\n" for j in jours)


def _analyseur() -> argparse.ArgumentParser:
    analyseur = argparse.ArgumentParser(prog="python -m app.scheduler", description="Planificateur quotidien")
    commandes = analyseur.add_subparsers(dest="commande", required=True)
    commande = commandes.add_parser("tick", help="planifier les jobs quotidiens (comme le worker à 04:00)")
    commande.add_argument("--jour", type=date.fromisoformat, help="AAAA-MM-JJ (développement et recette)")
    return analyseur


def main(
    arguments: Sequence[str] | None = None,
    *,
    fabrique: Fabrique | None = None,
    reglages: Settings | None = None,
    sortie: TextIO = sys.stdout,
    erreur: TextIO = sys.stderr,
) -> int:
    try:
        lus = _analyseur().parse_args(arguments)
    except SystemExit as exc:
        return int(exc.code or 0)
    if reglages is None:  # pragma: no cover - valeurs réelles dans le conteneur
        from app.settings import settings

        reglages = settings
    if lus.jour is not None and reglages.env == "prod":
        erreur.write(f"{REFUS_PRODUCTION}\n")
        return 2
    if fabrique is None:  # pragma: no cover - valeurs réelles dans le conteneur
        from app.db import fabrique as fabrique_reelle

        fabrique = fabrique_reelle()
    texte = planifier_un_jour(fabrique, lus.jour) if lus.jour else tick(fabrique, reglages.service_name)
    sortie.write(texte)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
