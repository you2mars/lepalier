"""Base PostgreSQL 16 de test (Testcontainers) organisée comme en dev et en prod (TEC-DAT-03) :
un rôle propriétaire qui migre, un rôle applicatif qui n'a que les droits accordés par les migrations."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, make_url, text
from sqlalchemy.orm import Session, sessionmaker
from testcontainers.community.postgres import PostgresContainer

from app.settings import settings

RACINE = Path(__file__).resolve().parents[1]
ROLE = settings.role_applicatif
MDP_APPLICATIF = "mdp-essai-applicatif"


@dataclass(frozen=True)
class BaseEssai:
    url_proprietaire: str
    url_applicatif: str


def config_alembic(url: str) -> Config:
    config = Config(str(RACINE / "alembic.ini"))
    config.set_main_option("script_location", str(RACINE / "migrations"))
    config.attributes["url"] = url
    config.attributes["role_applicatif"] = ROLE
    return config


def creer_base(admin: Engine, nom: str, url_admin: str) -> BaseEssai:
    """Base `nom` possédée par le rôle propriétaire ; le rôle applicatif ne peut que s'y connecter."""
    with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as cnx:
        cnx.execute(text(f'CREATE DATABASE "{nom}"'))
        cnx.execute(text(f'REVOKE ALL ON DATABASE "{nom}" FROM PUBLIC'))
        cnx.execute(text(f'GRANT CONNECT ON DATABASE "{nom}" TO "{ROLE}"'))
    url = make_url(url_admin).set(database=nom)
    moteur = create_engine(url)
    with moteur.begin() as cnx:
        cnx.execute(text(f'GRANT USAGE ON SCHEMA public TO "{ROLE}"'))
    moteur.dispose()
    return BaseEssai(
        url_proprietaire=url.render_as_string(hide_password=False),
        url_applicatif=url.set(username=ROLE, password=MDP_APPLICATIF).render_as_string(hide_password=False),
    )


@pytest.fixture(scope="session")
def serveur() -> Iterator[tuple[Engine, str]]:
    with PostgresContainer(
        "postgres:16", username="proprietaire", password="mdp-essai", driver="psycopg"
    ) as pg:
        url_admin = pg.get_connection_url()
        admin = create_engine(url_admin)
        with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as cnx:
            cnx.execute(text(f"CREATE ROLE \"{ROLE}\" LOGIN PASSWORD '{MDP_APPLICATIF}'"))
        yield admin, url_admin
        admin.dispose()


@pytest.fixture(scope="session")
def base(serveur: tuple[Engine, str]) -> BaseEssai:
    admin, url_admin = serveur
    base = creer_base(admin, "service_essai", url_admin)
    command.upgrade(config_alembic(base.url_proprietaire), "head")
    return base


@pytest.fixture
def fabrique(base: BaseEssai) -> Iterator[sessionmaker[Session]]:
    proprietaire = create_engine(base.url_proprietaire)
    with proprietaire.begin() as cnx:
        cnx.execute(text("TRUNCATE outbox, inbox, journal, job, planificateur, etat_worker"))
    proprietaire.dispose()
    applicatif = create_engine(base.url_applicatif)
    yield sessionmaker(applicatif, expire_on_commit=False)
    applicatif.dispose()
