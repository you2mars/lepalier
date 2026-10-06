"""python -m app.scheduler tick [--jour AAAA-MM-JJ] : planificateur quotidien lancé à la main (make tick)."""

from __future__ import annotations

import io
import re

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app import scheduler
from app.settings import Settings

pytestmark = pytest.mark.integration


def _lancer(fabrique: sessionmaker[Session], *arguments: str, env: str = "dev") -> tuple[int, str, str]:
    sortie, erreur = io.StringIO(), io.StringIO()
    reglages = Settings(service_name="identity", env=env)
    code = scheduler.main(list(arguments), fabrique=fabrique, reglages=reglages, sortie=sortie, erreur=erreur)
    return code, sortie.getvalue(), erreur.getvalue()


def test_tick__premier_passage__jour_courant_planifie_une_seule_fois(fabrique: sessionmaker[Session]) -> None:
    code, sortie, erreur = _lancer(fabrique, "tick")
    assert (code, erreur) == (0, "")
    assert re.fullmatch(r"Jobs quotidiens planifiés pour le \w+ (1er|\d{1,2}) \w+ \d{4}\.\n", sortie)
    jour = re.search(r"pour le (.+)\.\n", sortie).group(1)  # type: ignore[union-attr]
    assert _lancer(fabrique, "tick") == (
        0,
        f"Rien à planifier : les jobs quotidiens du {jour} le sont déjà. "
        "Pour un autre jour : --jour AAAA-MM-JJ.\n",
        "",
    )


def test_tick__jour_donne__planifie_ce_jour(fabrique: sessionmaker[Session]) -> None:
    code, sortie, _ = _lancer(fabrique, "tick", "--jour", "2026-10-01")
    assert code == 0
    assert sortie.startswith("Jour du jeudi 1er octobre 2026 : ")


@pytest.mark.parametrize("jour", ["2026-13-01", "demain", "01/10/2026"])
def test_tick__jour_mal_forme__code_2(fabrique: sessionmaker[Session], jour: str) -> None:
    assert _lancer(fabrique, "tick", "--jour", jour)[0] == 2


def test_tick__jour_donne_en_production__refuse(fabrique: sessionmaker[Session]) -> None:
    assert _lancer(fabrique, "tick", "--jour", "2026-10-01", env="prod") == (
        2,
        "",
        "L'option --jour sert au développement et à la recette : elle est refusée en production.\n",
    )


def test_tick__en_production_sans_jour__autorise(fabrique: sessionmaker[Session]) -> None:
    assert _lancer(fabrique, "tick", env="prod")[0] == 0


def test_scheduler__commande_inconnue__code_2(fabrique: sessionmaker[Session]) -> None:
    assert _lancer(fabrique, "purger")[0] == 2


def test_tick__jour_donne__purges_d_identity_creees_puis_aucune(fabrique: sessionmaker[Session]) -> None:
    from app.models import JOB
    from tests.aides import lignes

    assert _lancer(fabrique, "tick", "--jour", "2026-10-05") == (
        0,
        "Jour du lundi 5 octobre 2026 : 5 jobs créés.\n",
        "",
    )
    assert len(lignes(fabrique, JOB, JOB.c.type.like("purge.%"))) == 5
    assert _lancer(fabrique, "tick", "--jour", "2026-10-05")[1] == (
        "Jour du lundi 5 octobre 2026 : aucun nouveau job (jour déjà planifié).\n"
    )
