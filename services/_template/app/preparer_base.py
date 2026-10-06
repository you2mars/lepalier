"""Préparation de la base avant le démarrage du service : python -m app.preparer_base (conteneur à usage
unique `<service>-migrations` de compose.dev.yml, terminé avant que le service démarre).

1. Aligne le mot de passe du rôle applicatif sur le secret monté `mdp_base` (ADR 0007), à chaque démarrage :
   après `make dev-secrets FORCE=1`, le rôle suit le nouveau secret sans recréer la base.
2. Applique les migrations avec le rôle propriétaire (APP_MIGRATION_DATABASE_URL, TEC-DAT-03).
Le processus du service, lui, ne reçoit jamais l'URL du rôle propriétaire. Aucun mot de passe n'est affiché.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TextIO

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from psycopg import sql
from sqlalchemy import create_engine, make_url

from app.settings import Settings
from commun.secrets import SecretInvalide, lire_secret

RACINE = Path(__file__).resolve().parents[1]


class Refus(Exception):
    """Message affiché tel quel ; rien n'a été modifié en base."""


def _config(url: str, role: str) -> Config:
    config = Config(str(RACINE / "alembic.ini"))
    config.set_main_option("script_location", str(RACINE / "migrations"))
    config.attributes["url"] = url
    config.attributes["role_applicatif"] = role
    return config


def preparer(reglages: Settings) -> str:
    if not reglages.migration_database_url:
        raise Refus(
            "APP_MIGRATION_DATABASE_URL manque : URL du rôle propriétaire de la base, pour les migrations."
        )
    try:
        mot_de_passe = lire_secret(reglages.secrets_dir / "mdp_base")
    except SecretInvalide as exc:
        raise Refus(f"Secret mdp_base illisible : {exc}") from exc
    url = make_url(reglages.migration_database_url).render_as_string(hide_password=False)
    role = reglages.role_applicatif
    moteur = create_engine(url)
    try:
        with moteur.connect().execution_options(isolation_level="AUTOCOMMIT") as cnx:
            # ALTER ROLE n'accepte pas de paramètre lié : identifiant et littéral échappés par psycopg
            requete = sql.SQL("ALTER ROLE {} PASSWORD {}").format(
                sql.Identifier(role), sql.Literal(mot_de_passe)
            )
            cnx.connection.driver_connection.execute(requete)  # type: ignore[union-attr]
        command.upgrade(_config(url, role), "head")
        with moteur.connect() as cnx:
            revision = MigrationContext.configure(cnx).get_current_revision()
    finally:
        moteur.dispose()
    return f"Mot de passe du rôle {role} aligné sur le secret mdp_base.\nBase à jour : révision {revision}.\n"


def main(
    *, reglages: Settings | None = None, sortie: TextIO = sys.stdout, erreur: TextIO = sys.stderr
) -> int:
    if reglages is None:  # pragma: no cover - valeurs réelles dans le conteneur
        from app.settings import settings

        reglages = settings
    try:
        sortie.write(preparer(reglages))
    except Refus as exc:
        erreur.write(f"{exc}\n")
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
