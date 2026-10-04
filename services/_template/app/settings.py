from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration du service (variables d'environnement, jamais de secret en dur)."""

    model_config = SettingsConfigDict(env_prefix="APP_", extra="ignore")

    service_name: str = "__SERVICE__"
    env: str = "dev"  # dev | preprod | prod
    database_url: str = "postgresql+psycopg://svc___SERVICE__:changeme@postgres:5432/__SERVICE__"
    nats_url: str = "nats://nats:4222"
    tz: str = "Europe/Paris"


settings = Settings()
