from __future__ import annotations

from functools import cache

from sqlalchemy import URL, Engine, create_engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from app.settings import Settings, settings
from commun.secrets import lire_secret


def url_base(reglages: Settings = settings) -> URL:
    """URL du rôle applicatif ; le mot de passe vient du secret `mdp_base` s'il est monté (ADR 0007)."""
    url = make_url(reglages.database_url)
    secret = reglages.secrets_dir / "mdp_base"
    if secret.exists():
        url = url.set(password=lire_secret(secret))
    return url


@cache
def moteur() -> Engine:
    return create_engine(url_base(), pool_pre_ping=True)


@cache
def fabrique() -> sessionmaker[Session]:
    return sessionmaker(moteur(), expire_on_commit=False)
