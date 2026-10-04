from __future__ import annotations

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Engine, create_engine, inspect, text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session, sessionmaker

from app.models import JOURNAL, METADATA, OUTBOX
from commun.ids import uuid7

from .conftest import BaseEssai, config_alembic, creer_base

pytestmark = pytest.mark.integration

TABLES_SOCLE = {"outbox", "inbox", "journal", "job", "planificateur", "etat_worker"}


def test_migrations__base_vide__montee_descente_remontee(serveur: tuple[Engine, str]) -> None:
    admin, url_admin = serveur
    base = creer_base(admin, "essai_migrations", url_admin)
    config = config_alembic(base.url_proprietaire)
    moteur = create_engine(base.url_proprietaire)

    command.upgrade(config, "head")
    assert TABLES_SOCLE <= set(inspect(moteur).get_table_names())
    command.downgrade(config, "base")
    assert not TABLES_SOCLE & set(inspect(moteur).get_table_names())
    command.upgrade(config, "head")
    assert TABLES_SOCLE <= set(inspect(moteur).get_table_names())
    moteur.dispose()


def test_migrations__schema_identique_aux_tables_declarees(base: BaseEssai) -> None:
    moteur = create_engine(base.url_proprietaire)
    with moteur.connect() as cnx:
        ecarts = compare_metadata(MigrationContext.configure(cnx), METADATA)
    moteur.dispose()
    assert ecarts == []


def _executer(fabrique: sessionmaker[Session], sql: str) -> None:
    with fabrique() as s, s.begin():
        s.execute(text(sql))


def test_droits__role_applicatif__journal_en_ajout_seul(fabrique: sessionmaker[Session]) -> None:
    with fabrique() as s, s.begin():
        s.execute(
            JOURNAL.insert().values(
                id=uuid7(), action="essai.cree", table_cible="essai", enregistrement_id=uuid7(), trace_id="t"
            )
        )
    for sql in ("UPDATE journal SET action = 'falsifie'", "DELETE FROM journal", "TRUNCATE journal"):
        with pytest.raises(ProgrammingError, match="permission denied"):
            _executer(fabrique, sql)


def test_droits__role_applicatif__ni_creation_ni_suppression_de_table(
    fabrique: sessionmaker[Session],
) -> None:
    for sql in ("CREATE TABLE intruse (id int)", "DROP TABLE journal", "ALTER TABLE outbox ADD COLUMN x int"):
        with pytest.raises(ProgrammingError, match=r"permission denied|must be owner"):
            _executer(fabrique, sql)


def test_droits__role_applicatif__lecture_ecriture_sur_les_autres_tables_du_socle(
    fabrique: sessionmaker[Session],
) -> None:
    with fabrique() as s, s.begin():
        for table in ("outbox", "inbox", "job", "planificateur", "etat_worker"):
            s.execute(text(f"SELECT 1 FROM {table} LIMIT 1"))
            s.execute(text(f"DELETE FROM {table}"))
        s.execute(OUTBOX.update().values(relaye_le=None))
