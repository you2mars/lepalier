from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration du service (variables APP_*) ; les secrets sont des fichiers montés (ADR 0007)."""

    model_config = SettingsConfigDict(env_prefix="APP_", extra="ignore")

    service_name: str = "identity"
    env: str = "dev"  # dev | preprod | prod
    # rôle applicatif : lecture et écriture, INSERT seul sur journal (TEC-DAT-03)
    database_url: str = "postgresql+psycopg://svc_identity@postgres:5432/identity"
    role_applicatif: str = "svc_identity"
    # rôle propriétaire des tables, utilisé seulement par les migrations (make migrate)
    migration_database_url: str | None = None
    nats_url: str = "nats://nats:4222"
    tz: str = "Europe/Paris"
    secrets_dir: Path = Path("/run/secrets")
    # écritures acceptées depuis ces origines (TEC-SEC-07), ex. ["https://lepalier.exemple.fr"]
    origines_autorisees: list[str] = []
    # chemins sans identité utilisateur : /auth/* (connexion, code, liens) en plus des routes internes
    prefixes_publics: list[str] = ["/internal/", "/auth/"]
    intervalle_worker_secondes: float = 2.0
    # e-mails de compte (ADR 0006) : Mailpit en dev, serveur SMTP de la SCI en production
    smtp_hote: str = "mailpit"
    smtp_port: int = 1025
    courriel_expediteur: str = "LePalier <lepalier@localhost>"
    # textes affichés, écrits une seule fois et partagés avec le front (docs/LEXIQUE.md)
    libelles_dir: Path = Path(__file__).resolve().parents[3] / "contracts" / "libelles"


settings = Settings()
