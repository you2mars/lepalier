from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import func, insert, select, text, update
from sqlalchemy.orm import Session, sessionmaker

from commun.ids import uuid7
from commun.jobs import DUREE_VERROU, ErreurReseau, Job, Jobs

from .conftest import EFFET, JOB, PLANIFICATEUR

pytestmark = pytest.mark.integration

JOBS = Jobs(JOB, PLANIFICATEUR)


def _maintenant(fabrique: sessionmaker[Session]) -> datetime:
    with fabrique() as s:
        maintenant = s.scalar(select(func.now()))
    assert isinstance(maintenant, datetime)
    return maintenant


def _ligne(fabrique: sessionmaker[Session], cle: str) -> dict[str, object]:
    with fabrique() as s:
        return dict(s.execute(select(JOB).where(JOB.c.cle == cle)).mappings().one())


def _rendre_du(fabrique: sessionmaker[Session], cle: str) -> None:
    with fabrique() as s, s.begin():
        s.execute(update(JOB).where(JOB.c.cle == cle).values(planifie_pour=func.now() - timedelta(seconds=1)))


def _planifier(fabrique: sessionmaker[Session], cle: str, dans: timedelta = timedelta(0)) -> None:
    with fabrique() as s, s.begin():
        JOBS.planifier(
            s, "essai.effet", cle, planifie_pour=_maintenant(fabrique) + dans, payload={"cle": cle}
        )


def _effet(session: Session, job: Job) -> None:
    session.execute(insert(EFFET).values(id=uuid7(), valeur=job.cle))


# --- planification et prise (TEC-JOB-01) -----------------------------------------------------------


def test_planifier__idempotent_par_type_et_cle(fabrique: sessionmaker[Session]) -> None:
    with fabrique() as s, s.begin():
        assert JOBS.planifier(s, "essai.effet", "lot-12:2026-11") is True
        assert JOBS.planifier(s, "essai.effet", "lot-12:2026-11") is False
        assert JOBS.planifier(s, "autre.type", "lot-12:2026-11") is True
    with fabrique() as s:
        assert s.scalar(select(func.count()).select_from(JOB)) == 2


def test_prendre__seulement_les_jobs_dus_dans_l_ordre(fabrique: sessionmaker[Session]) -> None:
    _planifier(fabrique, "futur", dans=timedelta(hours=1))
    _planifier(fabrique, "second", dans=timedelta(seconds=-1))
    _planifier(fabrique, "premier", dans=timedelta(seconds=-5))
    with fabrique() as s, s.begin():
        job = JOBS.prendre(s)
    assert job is not None
    assert job.cle == "premier"
    assert job.payload == {"cle": "premier"}
    ligne = _ligne(fabrique, "premier")
    assert ligne["statut"] == "en_cours"
    verrou = ligne["verrouille_jusqu"]
    assert isinstance(verrou, datetime)
    assert abs(verrou - (_maintenant(fabrique) + DUREE_VERROU)) < timedelta(seconds=30)


def test_prendre__deux_preneurs_simultanes__jamais_le_meme_job(fabrique: sessionmaker[Session]) -> None:
    _planifier(fabrique, "a", dans=timedelta(seconds=-2))
    _planifier(fabrique, "b", dans=timedelta(seconds=-1))
    with fabrique() as s1, s1.begin(), fabrique() as s2, s2.begin():
        j1, j2 = JOBS.prendre(s1), JOBS.prendre(s2)
        assert j1 is not None and j2 is not None
        assert {j1.cle, j2.cle} == {"a", "b"}
        assert JOBS.prendre(s2) is None


def test_prendre__verrou_expire__job_repris_sinon_non(fabrique: sessionmaker[Session]) -> None:
    _planifier(fabrique, "bloque", dans=timedelta(seconds=-1))
    with fabrique() as s, s.begin():
        assert JOBS.prendre(s) is not None
    with fabrique() as s, s.begin():
        assert JOBS.prendre(s) is None
    with fabrique() as s, s.begin():
        s.execute(update(JOB).values(verrouille_jusqu=func.now() - timedelta(seconds=1)))
    with fabrique() as s, s.begin():
        repris = JOBS.prendre(s)
    assert repris is not None and repris.cle == "bloque"


# --- exécution (TEC-JOB-02) ------------------------------------------------------------------------


def test_executer_un__aucun_job_du__none(fabrique: sessionmaker[Session]) -> None:
    _planifier(fabrique, "plus-tard", dans=timedelta(hours=1))
    assert JOBS.executer_un(fabrique, {"essai.effet": _effet}) is None


def test_executer_un__succes__effet_et_statut_termine_ensemble(fabrique: sessionmaker[Session]) -> None:
    _planifier(fabrique, "ok", dans=timedelta(seconds=-1))
    assert JOBS.executer_un(fabrique, {"essai.effet": _effet}) == "termine"
    ligne = _ligne(fabrique, "ok")
    assert ligne["statut"] == "termine"
    assert ligne["termine_le"] is not None
    assert ligne["verrouille_jusqu"] is None
    with fabrique() as s:
        assert s.scalar(select(EFFET.c.valeur)) == "ok"


def test_executer_un__trois_echecs__delais_1_10_60_min_puis_echec_sans_effet(
    fabrique: sessionmaker[Session],
) -> None:
    def echoue(session: Session, job: Job) -> None:
        _effet(session, job)
        raise ValueError("donnée incohérente")

    _planifier(fabrique, "ko", dans=timedelta(seconds=-1))
    for tentative, delai in [(1, timedelta(minutes=1)), (2, timedelta(minutes=10))]:
        assert JOBS.executer_un(fabrique, {"essai.effet": echoue}) == "reessai"
        ligne = _ligne(fabrique, "ko")
        assert (ligne["statut"], ligne["tentatives"]) == ("planifie", tentative)
        prochain = ligne["planifie_pour"]
        assert isinstance(prochain, datetime)
        assert abs(prochain - (_maintenant(fabrique) + delai)) < timedelta(seconds=30)
        _rendre_du(fabrique, "ko")
    assert JOBS.executer_un(fabrique, {"essai.effet": echoue}) == "echec"
    ligne = _ligne(fabrique, "ko")
    assert (ligne["statut"], ligne["tentatives"]) == ("echec", 3)
    assert "donnée incohérente" in str(ligne["derniere_erreur"])
    with fabrique() as s:
        assert s.execute(select(EFFET)).first() is None
    _rendre_du(fabrique, "ko")
    assert JOBS.executer_un(fabrique, {"essai.effet": echoue}) is None


def test_executer_un__erreur_reseau__reporte_sans_compter_de_tentative(
    fabrique: sessionmaker[Session],
) -> None:
    def injoignable(session: Session, job: Job) -> None:
        raise ErreurReseau("SMTP injoignable")

    _planifier(fabrique, "reseau", dans=timedelta(seconds=-1))
    assert JOBS.executer_un(fabrique, {"essai.effet": injoignable}) == "reporte"
    ligne = _ligne(fabrique, "reseau")
    assert (ligne["statut"], ligne["tentatives"]) == ("planifie", 0)
    assert ligne["planifie_pour"] > _maintenant(fabrique)  # type: ignore[operator]


def test_executer_un__type_sans_gestionnaire__echec_immediat(fabrique: sessionmaker[Session]) -> None:
    _planifier(fabrique, "orphelin", dans=timedelta(seconds=-1))
    assert JOBS.executer_un(fabrique, {}) == "echec"
    ligne = _ligne(fabrique, "orphelin")
    assert ligne["statut"] == "echec"
    assert "aucun gestionnaire" in str(ligne["derniere_erreur"])


def test_compter_en_echec(fabrique: sessionmaker[Session]) -> None:
    _planifier(fabrique, "orphelin", dans=timedelta(seconds=-1))
    JOBS.executer_un(fabrique, {})
    with fabrique() as s:
        assert JOBS.compter_en_echec(s) == 1


# --- planificateur quotidien (TEC-JOB-06, TEC-JOB-07) ----------------------------------------------


def _aujourd_hui_paris(fabrique: sessionmaker[Session]) -> date:
    with fabrique() as s:
        return s.scalar(text("SELECT (now() AT TIME ZONE 'Europe/Paris')::date"))  # type: ignore[no-any-return]


def test_tick__premier_passage__jour_courant_en_heure_de_paris(fabrique: sessionmaker[Session]) -> None:
    jours: list[date] = []
    assert JOBS.tick(fabrique, "essai", lambda s, j: jours.append(j), heure_tick=0) == [
        _aujourd_hui_paris(fabrique)
    ]
    assert jours == [_aujourd_hui_paris(fabrique)]


def test_tick__avant_l_heure_du_tick__jour_courant_pas_encore_planifie(
    fabrique: sessionmaker[Session],
) -> None:
    hier = _aujourd_hui_paris(fabrique) - timedelta(days=1)
    assert JOBS.tick(fabrique, "essai", lambda s, j: None, heure_tick=24) == [hier]


def test_tick__meme_jour__rien_a_faire(fabrique: sessionmaker[Session]) -> None:
    JOBS.tick(fabrique, "essai", lambda s, j: None, heure_tick=0)
    assert JOBS.tick(fabrique, "essai", lambda s, j: None, heure_tick=0) == []


def test_tick__jours_manques__rattrapes_dans_l_ordre_et_jobs_planifies(
    fabrique: sessionmaker[Session],
) -> None:
    aujourd_hui = _aujourd_hui_paris(fabrique)
    with fabrique() as s, s.begin():
        s.execute(insert(PLANIFICATEUR).values(nom="essai", dernier_tick=aujourd_hui - timedelta(days=3)))

    def planifier_jour(session: Session, jour: date) -> None:
        JOBS.planifier(session, "essai.quotidien", jour.isoformat())

    jours = JOBS.tick(fabrique, "essai", planifier_jour, heure_tick=0)
    assert jours == [aujourd_hui - timedelta(days=2), aujourd_hui - timedelta(days=1), aujourd_hui]
    with fabrique() as s:
        assert (
            s.scalar(select(PLANIFICATEUR.c.dernier_tick).where(PLANIFICATEUR.c.nom == "essai"))
            == aujourd_hui
        )
        assert s.scalar(select(func.count()).select_from(JOB)) == 3


def test_tick__echec_de_planification__dernier_tick_inchange(fabrique: sessionmaker[Session]) -> None:
    def echoue(session: Session, jour: date) -> None:
        raise RuntimeError("panne")

    with pytest.raises(RuntimeError):
        JOBS.tick(fabrique, "essai", echoue, heure_tick=0)
    with fabrique() as s:
        assert s.execute(select(PLANIFICATEUR)).first() is None
