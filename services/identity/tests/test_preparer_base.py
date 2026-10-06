"""python -m app.preparer_base : conteneur à usage unique lancé avant le service (compose.dev.yml).

Aligne le mot de passe du rôle applicatif sur le secret `mdp_base` (ADR 0007), puis applique les migrations
avec le rôle propriétaire (TEC-DAT-03). Rôle d'essai à part : celui des autres tests n'est pas touché.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, create_engine, make_url, text
from sqlalchemy.exc import OperationalError

from app import preparer_base
from app.settings import Settings

from .conftest import RACINE, config_alembic

pytestmark = pytest.mark.integration

ROLE_ESSAI = "svc_preparation"
SECRET = "mdp-tire-du-secret-mdp-base"


@pytest.fixture
def base_neuve(serveur: tuple[Engine, str]) -> str:
    """Base vide possédée par le rôle propriétaire ; rôle applicatif d'essai créé sans mot de passe."""
    admin, url_admin = serveur
    nom = "essai_preparation"
    with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as cnx:
        cnx.execute(text(f'DROP DATABASE IF EXISTS "{nom}"'))
        cnx.execute(text(f'DROP ROLE IF EXISTS "{ROLE_ESSAI}"'))
        cnx.execute(text(f'CREATE ROLE "{ROLE_ESSAI}" LOGIN'))
        cnx.execute(text(f'CREATE DATABASE "{nom}"'))
        cnx.execute(text(f'GRANT CONNECT ON DATABASE "{nom}" TO "{ROLE_ESSAI}"'))
    url = make_url(url_admin).set(database=nom)
    moteur = create_engine(url)
    with moteur.begin() as cnx:
        cnx.execute(text(f'GRANT USAGE ON SCHEMA public TO "{ROLE_ESSAI}"'))
    moteur.dispose()
    return url.render_as_string(hide_password=False)


def _reglages(url_proprietaire: str | None, secrets: Path) -> Settings:
    return Settings(
        migration_database_url=url_proprietaire,
        database_url=make_url(url_proprietaire or "postgresql+psycopg://x@h/b")
        .set(username=ROLE_ESSAI, password=None)
        .render_as_string(hide_password=False),
        role_applicatif=ROLE_ESSAI,
        secrets_dir=secrets,
    )


def _secret(dossier: Path, valeur: str = SECRET) -> Path:
    dossier.mkdir(exist_ok=True)
    (dossier / "mdp_base").write_text(valeur + "\n")
    (dossier / "mdp_base").chmod(0o400)
    return dossier


def _lancer(reglages: Settings) -> tuple[int, str, str]:
    sortie, erreur = io.StringIO(), io.StringIO()
    code = preparer_base.main(reglages=reglages, sortie=sortie, erreur=erreur)
    return code, sortie.getvalue(), erreur.getvalue()


def _connexion(url_proprietaire: str, mot_de_passe: str) -> str:
    url = make_url(url_proprietaire).set(username=ROLE_ESSAI, password=mot_de_passe)
    moteur = create_engine(url)
    try:
        with moteur.connect() as cnx:
            return str(cnx.execute(text("SELECT current_user")).scalar_one())
    finally:
        moteur.dispose()


def _revision(url_proprietaire: str) -> str | None:
    moteur = create_engine(url_proprietaire)
    with moteur.connect() as cnx:
        revision = cnx.execute(text("SELECT version_num FROM alembic_version")).scalar()
    moteur.dispose()
    return revision


def test_preparer__mot_de_passe_du_role_aligne_sur_mdp_base(base_neuve: str, tmp_path: Path) -> None:
    code, sortie, erreur = _lancer(_reglages(base_neuve, _secret(tmp_path / "s")))
    assert (code, erreur) == (0, "")
    assert _connexion(base_neuve, SECRET) == ROLE_ESSAI
    with pytest.raises(OperationalError):
        _connexion(base_neuve, "changeme")
    assert SECRET not in sortie


def test_preparer__secret_change__mot_de_passe_suit(base_neuve: str, tmp_path: Path) -> None:
    _lancer(_reglages(base_neuve, _secret(tmp_path / "a")))
    _lancer(_reglages(base_neuve, _secret(tmp_path / "b", "nouveau-secret-apres-force")))
    assert _connexion(base_neuve, "nouveau-secret-apres-force") == ROLE_ESSAI
    with pytest.raises(OperationalError):
        _connexion(base_neuve, SECRET)


def test_preparer__migrations_jusqu_a_la_derniere_revision_puis_rien(base_neuve: str, tmp_path: Path) -> None:
    derniere = ScriptDirectory.from_config(config_alembic(base_neuve)).get_current_head()
    reglages = _reglages(base_neuve, _secret(tmp_path / "s"))
    assert _lancer(reglages)[0] == 0
    assert _revision(base_neuve) == derniere
    code, sortie, _ = _lancer(reglages)
    assert (code, _revision(base_neuve)) == (0, derniere)
    assert f"révision {derniere}" in sortie


def test_preparer__secret_mdp_base_absent__refus_sans_rien_changer(base_neuve: str, tmp_path: Path) -> None:
    (tmp_path / "vide").mkdir()
    code, sortie, erreur = _lancer(_reglages(base_neuve, tmp_path / "vide"))
    assert (code, sortie) == (1, "")
    assert "mdp_base" in erreur
    assert _revision_ou_rien(base_neuve) is None


def test_preparer__sans_url_du_role_proprietaire__refus(tmp_path: Path) -> None:
    code, _, erreur = _lancer(_reglages(None, _secret(tmp_path / "s")))
    assert code == 1
    assert "APP_MIGRATION_DATABASE_URL" in erreur


def _revision_ou_rien(url_proprietaire: str) -> str | None:
    moteur = create_engine(url_proprietaire)
    with moteur.connect() as cnx:
        existe = cnx.execute(text("SELECT to_regclass('alembic_version')")).scalar()
    moteur.dispose()
    return None if existe is None else _revision(url_proprietaire)


def test_preparer__alembic_ini_du_service() -> None:
    assert (RACINE / "alembic.ini").exists()
