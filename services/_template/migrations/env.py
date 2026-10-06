"""Environnement Alembic : migrations exécutées avec le rôle propriétaire des tables (TEC-DAT-03).

URL : attribut `url` (tests) sinon APP_MIGRATION_DATABASE_URL ; jamais le rôle applicatif. Le rôle applicatif
(APP_ROLE_APPLICATIF) reçoit ses droits table par table dans chaque migration.
"""

from __future__ import annotations

from alembic import context
from sqlalchemy import create_engine, pool

from app.models import METADATA
from app.settings import settings

config = context.config
url = config.attributes.get("url") or settings.migration_database_url
if not url:
    raise SystemExit(
        "APP_MIGRATION_DATABASE_URL est requis : les migrations s'exécutent avec le rôle propriétaire "
        "des tables, jamais avec le rôle applicatif (TEC-DAT-03)."
    )
URL_MIGRATION: str = url
config.attributes.setdefault("role_applicatif", settings.role_applicatif)


def executer_hors_ligne() -> None:
    context.configure(url=URL_MIGRATION, target_metadata=METADATA, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def executer_en_ligne() -> None:
    moteur = create_engine(URL_MIGRATION, poolclass=pool.NullPool)
    with moteur.connect() as connexion:
        context.configure(connection=connexion, target_metadata=METADATA)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    executer_hors_ligne()
else:
    executer_en_ligne()
