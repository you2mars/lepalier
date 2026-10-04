from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import Column, Engine, MetaData, Table, Text, create_engine, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Session, sessionmaker
from testcontainers.community.postgres import PostgresContainer

from commun.inbox import table_inbox
from commun.jobs import table_job, table_planificateur
from commun.journal import table_journal
from commun.outbox import table_outbox

METADATA = MetaData()
OUTBOX = table_outbox(METADATA)
INBOX = table_inbox(METADATA)
JOURNAL = table_journal(METADATA)
JOB = table_job(METADATA)
PLANIFICATEUR = table_planificateur(METADATA)
EFFET = Table("effet", METADATA, Column("id", UUID(as_uuid=True), primary_key=True), Column("valeur", Text))


@pytest.fixture(scope="session")
def moteur() -> Iterator[Engine]:
    with PostgresContainer("postgres:16", driver="psycopg") as pg:
        engine = create_engine(pg.get_connection_url())
        METADATA.create_all(engine)
        yield engine
        engine.dispose()


@pytest.fixture
def fabrique(moteur: Engine) -> sessionmaker[Session]:
    with moteur.begin() as cnx:
        cnx.execute(text("TRUNCATE outbox, inbox, effet, journal, job, planificateur"))
    return sessionmaker(moteur)
