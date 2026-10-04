from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration du service (variables APP_*) ; les secrets sont des fichiers montés (ADR 0007)."""

    model_config = SettingsConfigDict(env_prefix="APP_", extra="ignore")

    service_name: str = "__SERVICE__"
    env: str = "dev"  # dev | preprod | prod
    # rôle applicatif : lecture et écriture, INSERT seul sur journal (TEC-DAT-03)
    database_url: str = "postgresql+psycopg://svc___SERVICE__@postgres:5432/__SERVICE__"
    role_applicatif: str = "svc___SERVICE__"
    # rôle propriétaire des tables, utilisé seulement par les migrations (make migrate)
    migration_database_url: str | None = None
    nats_url: str = "nats://nats:4222"
    tz: str = "Europe/Paris"
    secrets_dir: Path = Path("/run/secrets")
    # écritures acceptées depuis ces origines (TEC-SEC-07), ex. ["https://lepalier.exemple.fr"]
    origines_autorisees: list[str] = []
    # chemins sans identité utilisateur ; identity y ajoute "/auth/"
    prefixes_publics: list[str] = ["/internal/"]
    intervalle_worker_secondes: float = 2.0


settings = Settings()
