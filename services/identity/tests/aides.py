"""Aides des tests des parcours de compte : application d'essai, comptes, codes TOTP du moment."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import insert, select
from sqlalchemy.orm import Session, sessionmaker

from app.engines import codes_secours, mot_de_passe, totp
from app.engines.chiffrement import Cle, chiffrer
from app.main import creer_app
from app.models import CODE_SECOURS, UTILISATEUR
from app.securite import ClesCompte
from app.settings import Settings
from commun.ids import uuid7

ORIGINE = "https://lepalier.essai"
CLE_HMAC = b"h" * 32
CLES = ClesCompte(
    hmac=[CLE_HMAC],
    chiffrement=[Cle(version=1, valeur=b"c" * 32)],
    pseudonymisation=b"p" * 32,
)
REGLAGES = Settings(
    service_name="identity",
    origines_autorisees=[ORIGINE],
    prefixes_publics=["/internal/", "/auth/"],
)
MOT_DE_PASSE = "mon chat dort sur le toit"
IP = "192.168.1.20"


def application(fabrique: sessionmaker[Session]) -> FastAPI:
    return creer_app(
        cles_hmac=CLES.hmac, empreintes={}, fabrique_session=fabrique, reglages=REGLAGES, cles=CLES
    )


def client(fabrique: sessionmaker[Session], ip: str = IP) -> TestClient:
    """Client HTTPS (les cookies Secure ne circulent qu'en HTTPS), adresse IP posée comme par nginx."""
    return TestClient(application(fabrique), base_url="https://testserver", headers={"X-Real-IP": ip})


@dataclass
class Compte:
    id: uuid.UUID
    email: str
    secret: bytes
    codes: list[str] = field(default_factory=list)

    def code_totp(self, decalage_secondes: int = 0) -> str:
        return totp.code(self.secret, totp.pas_a(time.time() + decalage_secondes))


def creer_compte(
    fabrique: sessionmaker[Session],
    *,
    email: str | None = None,
    role: str = "associe",
    statut: str = "actif",
    nom_affiche: str = "Mme Durand",
    mot_de_passe_hache: str | None = None,
) -> Compte:
    uid = uuid7()
    secret = totp.nouveau_secret()
    codes = codes_secours.generer()
    adresse = email or f"{uid.hex[:12]}@essai.local"
    with fabrique() as s, s.begin():
        s.execute(
            insert(UTILISATEUR).values(
                id=uid,
                email=adresse,
                nom_affiche=nom_affiche,
                role=role,
                statut=statut,
                origine="commande_locale",
                mot_de_passe_hache=mot_de_passe_hache or mot_de_passe.hacher(MOT_DE_PASSE),
                totp_secret_chiffre=chiffrer(secret, CLES.chiffrement, uid.bytes),
            )
        )
        for code in codes[:3]:
            s.execute(
                insert(CODE_SECOURS).values(
                    id=uuid7(), utilisateur_id=uid, empreinte=codes_secours.hacher(code)
                )
            )
    return Compte(id=uid, email=adresse, secret=secret, codes=codes[:3])


def valeur(fabrique: sessionmaker[Session], requete: object) -> object:
    with fabrique() as s:
        return s.execute(requete).scalar()  # type: ignore[call-overload]


def lignes(fabrique: sessionmaker[Session], table: object, *conditions: object) -> list[dict[str, object]]:
    with fabrique() as s:
        return [dict(r) for r in s.execute(select(table).where(*conditions)).mappings()]  # type: ignore[call-overload,arg-type]
