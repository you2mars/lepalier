"""Section H : purges quotidiennes (TEC-DAT-02) planifiées par planifier_jour, journalisées une à une."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy import func, insert, select, update
from sqlalchemy.orm import Session, sessionmaker

from app.engines.chiffrement import pseudonymiser
from app.models import IDEMPOTENCE, JOB, JOBS, JOURNAL, OUTBOX, OUTBOX_SVC, SESSION, TENTATIVE_CONNEXION
from app.worker import GESTIONNAIRES, planifier_jour
from commun.enveloppe import Enveloppe, nouvelle_enveloppe
from commun.ids import uuid7

from .aides import CLES, MOT_DE_PASSE, client, creer_compte, lignes

pytestmark = pytest.mark.integration

JOUR = date(2026, 10, 5)
PURGES = {"purge.sessions", "purge.tentatives", "purge.idempotence", "purge.jobs", "purge.outbox"}


def _executer(fabrique: sessionmaker[Session]) -> list[str | None]:
    issues: list[str | None] = []
    while (issue := JOBS.executer_un(fabrique, GESTIONNAIRES)) is not None:
        issues.append(issue)
    return issues


def _planifier(fabrique: sessionmaker[Session], jour: date = JOUR) -> None:
    with fabrique() as s, s.begin():
        planifier_jour(s, jour)


def _vieillir(
    fabrique: sessionmaker[Session], table: object, colonne: str, age: timedelta, *conditions: object
) -> None:
    with fabrique() as s, s.begin():
        s.execute(update(table).where(*conditions).values({colonne: func.now() - age}))  # type: ignore[arg-type]


def test_purges__planifiees_chaque_jour_par_planifier_jour(fabrique: sessionmaker[Session]) -> None:
    assert PURGES <= set(GESTIONNAIRES)
    _planifier(fabrique)
    jobs = lignes(fabrique, JOB)
    assert {(j["type"], j["cle"]) for j in jobs} == {(p, "2026-10-05") for p in PURGES}


def test_purges__sessions_de_plus_de_90_jours_tentatives_de_30_jours_idempotence_expiree(
    fabrique: sessionmaker[Session],
) -> None:
    compte = creer_compte(fabrique)
    for _ in range(2):
        c = client(fabrique)
        c.post("/auth/connexion", json={"email": compte.email, "mot_de_passe": MOT_DE_PASSE})
    cle = pseudonymiser(compte.email, CLES.pseudonymisation)
    with fabrique() as s, s.begin():
        for _ in range(2):
            s.execute(
                insert(TENTATIVE_CONNEXION).values(
                    id=uuid7(), cle_compte=cle, ip="10.0.0.1", etape="mot_de_passe", reussie=False
                )
            )
        for age in (timedelta(hours=25), timedelta(hours=1)):
            s.execute(
                insert(IDEMPOTENCE).values(
                    portee="utilisateur:x",
                    cle=uuid7(),
                    route="POST /utilisateurs/inviter",
                    empreinte_requete=b"e" * 32,
                    statut="terminee",
                    statut_http=201,
                    cree_le=func.now() - age,
                    expire_le=func.now() - age + timedelta(hours=24),
                )
            )
    anciennes = [s["id"] for s in lignes(fabrique, SESSION)][:1]
    _vieillir(fabrique, SESSION, "cree_le", timedelta(days=90, seconds=1), SESSION.c.id.in_(anciennes))
    tentatives = [t["id"] for t in lignes(fabrique, TENTATIVE_CONNEXION)][:1]
    _vieillir(
        fabrique,
        TENTATIVE_CONNEXION,
        "cree_le",
        timedelta(days=30, seconds=1),
        TENTATIVE_CONNEXION.c.id.in_(tentatives),
    )

    _planifier(fabrique)
    assert _executer(fabrique) == ["termine"] * 5

    assert len(lignes(fabrique, SESSION)) == 1
    assert len(lignes(fabrique, TENTATIVE_CONNEXION)) == 1
    with fabrique() as s:
        assert s.execute(select(func.count()).select_from(IDEMPOTENCE)).scalar() == 1
    journal = {j["action"]: j for j in lignes(fabrique, JOURNAL, JOURNAL.c.action.like("purge.%"))}
    assert set(journal) == PURGES
    assert {a: j["apres"]["supprimees"] for a, j in journal.items()} == {  # type: ignore[index]
        "purge.sessions": 1,
        "purge.tentatives": 1,
        "purge.idempotence": 1,
        "purge.jobs": 0,
        "purge.outbox": 0,
    }
    assert all(j["utilisateur_id"] is None for j in journal.values())


def test_purges__rien_a_purger__une_ligne_de_journal_a_zero(fabrique: sessionmaker[Session]) -> None:
    _planifier(fabrique)
    _executer(fabrique)
    journal = lignes(fabrique, JOURNAL, JOURNAL.c.action.like("purge.%"))
    assert sorted(j["apres"]["supprimees"] for j in journal) == [0] * 5  # type: ignore[index]


def test_purges__rejouees_le_meme_jour__sans_double_effet(fabrique: sessionmaker[Session]) -> None:
    _planifier(fabrique)
    _executer(fabrique)
    _planifier(fabrique)
    assert _executer(fabrique) == []
    assert len(lignes(fabrique, JOURNAL, JOURNAL.c.action.like("purge.%"))) == 5
    _planifier(fabrique, JOUR + timedelta(days=1))
    assert _executer(fabrique) == ["termine"] * 5


def test_purges__jobs_termines_depuis_plus_de_90_jours__seulement(fabrique: sessionmaker[Session]) -> None:
    with fabrique() as s, s.begin():
        for cle in ("ancien", "recent", "en_echec", "planifie"):
            JOBS.planifier(s, "essai.purge", cle)
        s.execute(
            update(JOB)
            .where(JOB.c.cle == "ancien")
            .values(statut="termine", termine_le=func.now() - timedelta(days=90, seconds=1))
        )
        s.execute(
            update(JOB)
            .where(JOB.c.cle == "recent")
            .values(statut="termine", termine_le=func.now() - timedelta(days=89))
        )
        s.execute(
            update(JOB)
            .where(JOB.c.cle == "en_echec")
            .values(statut="echec", termine_le=func.now() - timedelta(days=200))
        )
    _planifier(fabrique)
    _executer(fabrique)
    restants = {str(j["cle"]) for j in lignes(fabrique, JOB, JOB.c.type == "essai.purge")}
    assert restants == {"recent", "en_echec", "planifie"}
    (journal,) = lignes(fabrique, JOURNAL, JOURNAL.c.action == "purge.jobs")
    assert journal["apres"]["supprimees"] == 1  # type: ignore[index]


def test_purges__outbox_relayee_depuis_plus_de_30_jours__seulement(fabrique: sessionmaker[Session]) -> None:
    def evenement() -> Enveloppe:
        return nouvelle_enveloppe(
            type="essai.cree", version=1, producer="identity", aggregate_id=uuid7(), payload={}
        )

    envs = [evenement() for _ in range(3)]
    with fabrique() as s, s.begin():
        for env in envs:
            OUTBOX_SVC.ajouter(s, env)
        s.execute(
            update(OUTBOX)
            .where(OUTBOX.c.id == envs[0].id)
            .values(relaye_le=func.now() - timedelta(days=30, seconds=1))
        )
        s.execute(
            update(OUTBOX).where(OUTBOX.c.id == envs[1].id).values(relaye_le=func.now() - timedelta(days=29))
        )
    _planifier(fabrique)
    _executer(fabrique)
    restants = {e["id"] for e in lignes(fabrique, OUTBOX)}
    assert restants == {envs[1].id, envs[2].id}
