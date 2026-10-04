"""deploy/postgres/init-databases.sh (TEC-DAT-03), exécuté par une vraie image postgres:16. Docker requis."""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import Engine, create_engine, make_url, text
from sqlalchemy.exc import OperationalError, ProgrammingError
from testcontainers.community.postgres import PostgresContainer

pytestmark = pytest.mark.skipif(shutil.which("docker") is None, reason="Docker requis")

SCRIPT = Path(__file__).resolve().parents[2] / "deploy" / "postgres" / "init-databases.sh"
BASES = [
    "identity",
    "referentiel",
    "facturation",
    "charges_eau",
    "documents",
    "envois",
    "veille",
    "reporting",
]


@pytest.fixture(scope="module")
def url_admin() -> Iterator[str]:
    conteneur = PostgresContainer(
        "postgres:16", username="admin", password="mdp-admin-essai", driver="psycopg"
    )
    conteneur.with_volume_mapping(str(SCRIPT), "/docker-entrypoint-initdb.d/10-init-databases.sh", "ro")
    with conteneur as pg:
        yield pg.get_connection_url()


def _moteur(url_admin: str, base: str, role: str | None = None) -> Engine:
    url = make_url(url_admin).set(database=base)
    if role is not None:
        url = url.set(username=role, password="changeme")
    return create_engine(url)


def test_init__chaque_base_appartient_au_role_d_administration(url_admin: str) -> None:
    with _moteur(url_admin, "postgres").connect() as cnx:
        proprietaires = dict(
            cnx.execute(
                text("SELECT datname, pg_get_userbyid(datdba) FROM pg_database WHERE datname = ANY(:bases)"),
                {"bases": BASES},
            ).all()
        )
    assert proprietaires == {base: "admin" for base in BASES}


@pytest.mark.parametrize("base", BASES)
def test_init__role_applicatif_se_connecte_a_sa_base_sans_pouvoir_creer_de_table(
    url_admin: str, base: str
) -> None:
    with _moteur(url_admin, base, f"svc_{base}").connect() as cnx:
        assert cnx.execute(text("SELECT current_user")).scalar_one() == f"svc_{base}"
        with pytest.raises(ProgrammingError, match="permission denied"):
            cnx.execute(text("CREATE TABLE intruse (id int)"))


def test_init__role_applicatif_sans_acces_a_la_base_d_un_autre_service(url_admin: str) -> None:
    with pytest.raises(OperationalError, match="permission denied"):
        _moteur(url_admin, "referentiel", "svc_identity").connect()
