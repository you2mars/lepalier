"""Plateforme de développement (étape 5) : images, Compose et nginx, essayés pour de vrai avec Docker.

Lancés seulement par `make test-plateforme` (LEPALIER_PLATEFORME=1), qui construit d'abord les images
locales ; `make test` les ignore. Job CI « plateforme », filtré par chemins.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import shlex
import socket
import ssl
import struct
import subprocess
import time
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("LEPALIER_PLATEFORME") != "1", reason="make test-plateforme (images construites, Docker)"
)

IMAGE_IDENTITY = "ghcr.io/you2mars/identity:dev"
# navigateurs et bibliothèques système de Playwright, même version que @playwright/test (front/package.json)
IMAGE_PLAYWRIGHT = (
    "mcr.microsoft.com/playwright:v1.63.0-noble"
    "@sha256:eff16c30e6f3f4af0a03fa4b706120d5e9b0891c344a27d64559aff5900a4a27"
)
RACINE = Path(__file__).resolve().parents[2]


def _dans_l_image(image: str, *commande: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", "run", "--rm", "--network", "none", "--entrypoint", commande[0], image, *commande[1:]],
        capture_output=True,
        text=True,
        check=False,
    )


# --- bloc A : images ------------------------------------------------------------------------------------


def test_image__identity_construite_depuis_l_app_base_locale() -> None:
    """P1 : l'image d'identity repose sur ghcr.io/you2mars/app-base, construite en local par make images."""
    base = subprocess.run(
        ["docker", "image", "inspect", "--format", "{{.Id}}", "ghcr.io/you2mars/app-base:latest"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    couches_base = subprocess.run(
        ["docker", "image", "inspect", "--format", "{{json .RootFS.Layers}}", base],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    couches_identity = subprocess.run(
        ["docker", "image", "inspect", "--format", "{{json .RootFS.Layers}}", IMAGE_IDENTITY],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert couches_identity.startswith(couches_base.rstrip("]"))


def test_image__utilisateur_10001_et_python_de_l_image() -> None:
    """P2 : processus sous l'uid 10001 ; environnement construit dans l'image, pas copié depuis l'hôte."""
    r = _dans_l_image(IMAGE_IDENTITY, "sh", "-c", "id -u && readlink -f .venv/bin/python && pwd")
    assert r.returncode == 0, r.stderr
    uid, python, dossier = r.stdout.split()
    assert (uid, dossier) == ("10001", "/srv/services/identity")
    assert python.startswith("/usr/local/bin/python3.12")


def test_image__libelles_lus_depuis_contracts() -> None:
    """P2 : contracts/libelles/ est dans l'image, au chemin par défaut d'APP_LIBELLES_DIR."""
    r = _dans_l_image(
        IMAGE_IDENTITY,
        ".venv/bin/python",
        "-c",
        "from app.libelles import message; print(message('connexion.trop_d_essais'))",
    )
    assert (r.returncode, r.stdout) == (0, "Trop d'essais. Réessayez dans 15 minutes.\n"), r.stderr


def test_image__dependances_du_verrou_sans_outils_de_test() -> None:
    """P2 : versions installées = versions de uv.lock ; pytest absent ; ni secret ni cache local copiés."""
    # installation à blanc du contenu exporté de uv.lock (conditions de plateforme évaluées par uv)
    verrou = _dans_l_image(
        IMAGE_IDENTITY,
        "sh",
        "-c",
        "uv export --frozen --no-dev --no-hashes --no-emit-project --no-emit-package commun --offline "
        "> /tmp/verrou.txt "
        "&& uv pip install --dry-run --offline --no-deps -r /tmp/verrou.txt",
    )
    assert verrou.returncode == 0, verrou.stderr
    assert "Would make no changes" in verrou.stderr, verrou.stderr
    assert _dans_l_image(IMAGE_IDENTITY, ".venv/bin/python", "-c", "import pytest").returncode != 0
    copies = _dans_l_image(
        IMAGE_IDENTITY,
        "sh",
        "-c",
        "find / -xdev \\( -name .pytest_cache -o -name .mypy_cache -o -name secrets -o -name '.env*' \\) "
        "-not -path '/proc/*' -not -path '/usr/*' 2>/dev/null",
    )
    assert copies.stdout == ""


def test_image__lance_l_api_et_le_worker_sans_uv_run() -> None:
    r = _dans_l_image(IMAGE_IDENTITY, "cat", "supervisord.conf")
    assert "uv run" not in r.stdout
    assert ".venv/bin/uvicorn" in r.stdout
    assert ".venv/bin/python -m app.worker" in r.stdout


def test_image__commande_tick_presente() -> None:
    r = _dans_l_image(IMAGE_IDENTITY, ".venv/bin/python", "-m", "app.scheduler", "--help")
    assert r.returncode == 0
    assert "tick" in r.stdout


# --- bloc B : identity dans Compose ----------------------------------------------------------------------

PROJET = "lepalier-essai"
ESSAI = RACINE / "scripts" / "tests" / "plateforme" / "compose.essai.yml"


def _port_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@dataclass
class Plateforme:
    env: dict[str, str]
    secrets: Path
    certificat: Path
    fichier_env: Path
    # ligne écrite par make dev-certs, avant que l'essai n'y mette l'adresse qu'il sert vraiment
    ligne_dev_certs: str = ""

    @property
    def https(self) -> str:
        return f"https://127.0.0.1:{self.env['LEPALIER_PORT_HTTPS']}"

    def compose(
        self, *arguments: str, verifier: bool = True, faux_front: bool = True
    ) -> subprocess.CompletedProcess[str]:
        """docker compose sur le projet d'essai ; faux_front=False : le vrai front, sans fichier d'essai."""
        fichiers = ["-f", str(RACINE / "compose.dev.yml"), *(["-f", str(ESSAI)] if faux_front else [])]
        r = subprocess.run(
            [
                "docker",
                "compose",
                *fichiers,
                # .env écrit par make dev-certs, comme sur la VM ; jamais le .env du dépôt
                "--env-file",
                str(self.fichier_env),
                "-p",
                PROJET,
                *arguments,
            ],
            cwd=RACINE,
            env=self.env,
            capture_output=True,
            text=True,
            check=False,
        )
        if verifier:
            assert r.returncode == 0, r.stdout + r.stderr
        return r

    def python(self, code: str, verifier: bool = True) -> subprocess.CompletedProcess[str]:
        return self.compose("exec", "-T", "identity", "python", "-c", code, verifier=verifier)

    def conteneur(self, service: str) -> str:
        return self.compose("ps", "-a", "-q", service).stdout.strip()


def _demarrer(plateforme: Plateforme) -> None:
    plateforme.compose(
        "up", "-d", "--no-build", "--wait", "--wait-timeout", "240", "identity", "nginx", "front"
    )


@pytest.fixture(scope="module")
def plateforme(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Plateforme]:
    dossier = tmp_path_factory.mktemp("plateforme")
    secrets = dossier / "secrets"
    certificats = dossier / "certs"
    fichier_env = dossier / ".env"
    subprocess.run(
        ["make", "dev-certs", f"DEV_CERTS={certificats}", f"ENV_FICHIER={fichier_env}", "IP=192.0.2.10"],
        cwd=RACINE,
        check=True,
        capture_output=True,
    )
    env = {
        **{nom: valeur for nom, valeur in os.environ.items() if nom != "LEPALIER_URL_PUBLIQUE"},
        "SECRETS_DIR": str(secrets),
        "LEPALIER_SECRETS": str(secrets),
        "LEPALIER_PORT_POSTGRES": str(_port_libre()),
        "LEPALIER_PORT_NATS": str(_port_libre()),
        "LEPALIER_PORT_NATS_SUIVI": str(_port_libre()),
        "LEPALIER_PORT_MAILPIT": str(_port_libre()),
        "LEPALIER_PORT_SMTP": str(_port_libre()),
        "LEPALIER_CERTS": str(certificats),
        "LEPALIER_ADRESSE_HTTPS": "127.0.0.1",
        "LEPALIER_PORT_HTTPS": str(_port_libre()),
    }
    subprocess.run(["bash", "scripts/dev-secrets.sh"], cwd=RACINE, env=env, check=True, capture_output=True)
    essai = Plateforme(
        env=env,
        secrets=secrets,
        certificat=certificats / "dev.crt",
        fichier_env=fichier_env,
        ligne_dev_certs=fichier_env.read_text(),
    )
    # l'essai sert le site sur 127.0.0.1 et un port libre : l'adresse publique (liens des e-mails, origine
    # autorisée des écritures) doit être celle-là, comme sur la VM l'adresse écrite par make dev-certs
    fichier_env.write_text(f"LEPALIER_URL_PUBLIQUE={essai.https}\n")
    assert PROJET == "lepalier-essai"  # down -v ne vise jamais la plateforme de dev (lepalier-dev)
    try:
        _demarrer(essai)
        yield essai
    finally:
        essai.compose("down", "-v", "--remove-orphans", verifier=False)


def _reseaux(plateforme: Plateforme, service: str) -> set[str]:
    sortie = subprocess.run(
        [
            "docker",
            "inspect",
            "--format",
            "{{json .NetworkSettings.Networks}}",
            plateforme.conteneur(service),
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return {nom.removeprefix(f"{PROJET}_") for nom in json.loads(sortie)}


def test_compose__commandes_sans_variable_dans_l_environnement(plateforme: Plateforme) -> None:
    """R0-28 : l'adresse de la VM vient du .env écrit par make dev-certs ; docker compose ps, logs, exec et
    make tick fonctionnent sans que la variable soit fournie par make dev-up."""
    assert "LEPALIER_URL_PUBLIQUE" not in plateforme.env
    assert plateforme.ligne_dev_certs == "LEPALIER_URL_PUBLIQUE=https://192.0.2.10\n"
    assert plateforme.fichier_env.read_text() == f"LEPALIER_URL_PUBLIQUE={plateforme.https}\n"
    assert "identity" in plateforme.compose("ps", "--services", "--status", "running").stdout.split()
    assert plateforme.compose("exec", "-T", "identity", "true").returncode == 0
    assert plateforme.compose("logs", "--tail", "1", "identity").returncode == 0


def test_compose__reseaux_de_chaque_conteneur(plateforme: Plateforme) -> None:
    """P3 (TEC-SEC-06) : identity sur backend et egress-mail seulement ; backend interne."""
    assert _reseaux(plateforme, "identity") == {"backend", "egress-mail"}
    assert _reseaux(plateforme, "identity-migrations") == {"backend"}
    assert _reseaux(plateforme, "postgres") == {"backend", "outils-dev"}
    assert _reseaux(plateforme, "nats") == {"backend", "outils-dev"}
    assert _reseaux(plateforme, "mailpit") == {"egress-mail"}
    assert _reseaux(plateforme, "nginx") == {"edge", "backend"}
    # nginx joint identity ; le front (réseau edge seul) ne joint ni PostgreSQL ni NATS
    assert plateforme.compose(
        "exec", "-T", "nginx", "wget", "-qO-", "http://identity:8000/internal/healthz"
    ).stdout
    sonde = (
        "import socket, sys\n"
        "for hote, port in (('postgres', 5432), ('nats', 4222), ('identity', 8000)):\n"
        "    try:\n"
        "        socket.create_connection((hote, port), timeout=2).close()\n"
        "        sys.exit(f'{hote} joignable depuis edge')\n"
        "    except OSError:\n"
        "        pass\n"
    )
    assert plateforme.compose("exec", "-T", "front", "python", "-c", sonde, verifier=False).returncode == 0
    interne = subprocess.run(
        ["docker", "network", "inspect", "--format", "{{.Internal}}", f"{PROJET}_backend"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert interne == "true"


def test_compose__secrets_montes_0400_au_nom_de_10001(plateforme: Plateforme) -> None:
    """P4 (ADR 0007)."""
    r = plateforme.compose("exec", "-T", "identity", "sh", "-c", "stat -c '%n %u %a' /run/secrets/*")
    lignes = {
        ligne.split()[0].removeprefix("/run/secrets/"): ligne.split()[1:] for ligne in r.stdout.splitlines()
    }
    assert set(lignes) == {
        "cle_hmac_identite",
        "cle_chiffrement_identity",
        "cle_pseudonymisation_identity",
        "mdp_base",
    }
    assert all(valeurs == ["10001", "400"] for valeurs in lignes.values())


def _revision_en_base(plateforme: Plateforme) -> str:
    return plateforme.compose(
        "exec",
        "-T",
        "postgres",
        "psql",
        "-U",
        "admin",
        "-d",
        "identity",
        "-tAc",
        "SELECT version_num FROM alembic_version",
    ).stdout.strip()


def test_compose__migrations_a_la_derniere_revision_puis_rien_au_redemarrage(plateforme: Plateforme) -> None:
    """P5 : identity-migrations s'est terminé avec le code 0 avant qu'identity démarre."""
    etat = subprocess.run(
        ["docker", "inspect", "--format", "{{.State.ExitCode}}", plateforme.conteneur("identity-migrations")],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert etat == "0"
    derniere = plateforme.python(
        "from alembic.config import Config; from alembic.script import ScriptDirectory;"
        "c = Config('alembic.ini'); c.set_main_option('script_location', 'migrations');"
        "print(ScriptDirectory.from_config(c).get_current_head())"
    ).stdout.strip()
    assert _revision_en_base(plateforme) == derniere
    relance = plateforme.compose("run", "--rm", "--no-deps", "identity-migrations")
    assert f"révision {derniere}" in relance.stdout
    assert _revision_en_base(plateforme) == derniere


CONNEXION = (
    "from sqlalchemy import create_engine, text; from app.db import url_base;"
    "u = url_base(){};"
    "print(create_engine(u).connect().execute(text('SELECT current_user')).scalar_one())"
)


def test_compose__svc_identity_se_connecte_avec_mdp_base_jamais_avec_changeme(plateforme: Plateforme) -> None:
    """P6 : mot de passe du rôle aligné sur le secret ; aucun mot de passe par défaut."""
    assert plateforme.python(CONNEXION.format("")).stdout.strip() == "svc_identity"
    refus = plateforme.python(CONNEXION.format(".set(password='changeme')"), verifier=False)
    assert refus.returncode != 0
    assert "password authentication failed" in refus.stderr


def test_compose__secrets_regeneres_force__le_role_suit_au_redemarrage(plateforme: Plateforme) -> None:
    """P6 : make dev-secrets FORCE=1, puis redémarrage : la connexion fonctionne avec le nouveau secret."""
    subprocess.run(
        ["bash", "scripts/dev-secrets.sh"],
        cwd=RACINE,
        env={**plateforme.env, "FORCE": "1"},
        check=True,
        capture_output=True,
    )
    plateforme.compose(
        "up", "-d", "--no-build", "--force-recreate", "--wait", "--wait-timeout", "240", "identity"
    )
    assert plateforme.python(CONNEXION.format("")).stdout.strip() == "svc_identity"


def test_compose__lien_d_invitation_recu_dans_mailpit_sur_l_adresse_de_la_vm(plateforme: Plateforme) -> None:
    """P7 : APP_URL_PUBLIQUE vient de l'adresse de la VM (R0-04)."""
    plateforme.compose(
        "exec",
        "-T",
        "identity",
        "python",
        "-m",
        "app.admin",
        "creer-gerant",
        "--email",
        "gerant@essai.local",
        "--nom",
        "M. Martin",
    )
    plateforme.python(
        "from sqlalchemy import select; from app.db import fabrique; from app.models import UTILISATEUR;"
        "from app.services.utilisateurs import inviter; f = fabrique();"
        "s = f(); g = s.execute(select(UTILISATEUR.c.id)"
        ".where(UTILISATEUR.c.email == 'gerant@essai.local')).scalar_one();"
        "s.close(); inviter(f, g, 'associe@essai.local', 'Mme Durand', 'associe', None)"
    )
    api = f"http://127.0.0.1:{plateforme.env['LEPALIER_PORT_MAILPIT']}/api/v1"
    limite = time.monotonic() + 60
    messages: list[dict[str, object]] = []
    while time.monotonic() < limite and not messages:
        messages = httpx.get(f"{api}/messages").json()["messages"]
        time.sleep(1)
    (resume,) = messages
    texte = httpx.get(f"{api}/message/{resume['ID']}").json()["Text"]
    assert re.search(rf"{re.escape(plateforme.https)}/activation#[A-Za-z0-9_-]{{43}}", texte)


def test_compose__identity_en_bonne_sante_worker_present(plateforme: Plateforme) -> None:
    """P8 : vérification de santé de Compose sur /internal/healthz."""
    sante = subprocess.run(
        ["docker", "inspect", "--format", "{{.State.Health.Status}}", plateforme.conteneur("identity")],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert sante == "healthy"
    corps = plateforme.compose(
        "exec", "-T", "identity", "curl", "-fsS", "http://localhost:8000/internal/healthz"
    )
    assert json.loads(corps.stdout)["worker"] == "ok"


def test_compose__make_tick_planifie_les_purges_du_jour_dans_le_conteneur(plateforme: Plateforme) -> None:
    """R0-29 : même commande que make tick, sans uv."""
    r = plateforme.compose(
        "exec", "-T", "identity", "python", "-m", "app.scheduler", "tick", "--jour", "2026-10-05"
    )
    assert r.stdout == "Jour du lundi 5 octobre 2026 : 5 jobs créés.\n"


# --- bloc C : nginx ----------------------------------------------------------------------------------

MOT_DE_PASSE = "les tilleuls fleurissent en juin"
CREER_COMPTE = """
from sqlalchemy import insert
from app.db import fabrique
from app.engines import mot_de_passe, totp
from app.engines.chiffrement import chiffrer
from app.models import UTILISATEUR
from app.securite import charger_cles
from app.settings import settings
from commun.ids import uuid7
cles = charger_cles(settings.secrets_dir)
uid, secret = uuid7(), totp.nouveau_secret()
with fabrique()() as s, s.begin():
    s.execute(insert(UTILISATEUR).values(
        id=uid, email="{email}", nom_affiche="{nom}", role="{role}", statut="actif",
        origine="commande_locale", mot_de_passe_hache=mot_de_passe.hacher("{mdp}"),
        totp_secret_chiffre=chiffrer(secret, cles.chiffrement, uid.bytes),
    ))
print(uid, secret.hex())
"""


# 2 codes de secours pour un compte : affichés en clair une seule fois, comme à l'activation
AJOUTER_CODES_SECOURS = """
from sqlalchemy import insert
from app.db import fabrique
from app.engines import codes_secours
from app.models import CODE_SECOURS
from commun.ids import uuid7
codes = codes_secours.generer()[:2]
with fabrique()() as s, s.begin():
    for code in codes:
        s.execute(insert(CODE_SECOURS).values(
            id=uuid7(), utilisateur_id="{uid}", empreinte=codes_secours.hacher(code)
        ))
print(*codes)
"""
# invitation par la commande locale (app.admin) : jeton du lien d'activation, sans e-mail
INVITER = """
from app.admin import creer_gerant
from app.db import fabrique
print(creer_gerant(fabrique(), "{email}", "{nom}", "https://essai.invalide").rsplit("#", 1)[1].strip())
"""
# lien de réinitialisation du mot de passe, écrit comme le fait l'envoi de l'e-mail (jobs/courriels.py)
REINITIALISER = """
from sqlalchemy import func, insert, select
from app.db import fabrique
from app.engines import durees
from app.engines.jetons import empreinte, nouveau_jeton
from app.models import REINITIALISATION, UTILISATEUR
from commun.ids import uuid7
jeton = nouveau_jeton()
with fabrique()() as s, s.begin():
    maintenant = s.execute(select(func.now())).scalar_one()
    uid = s.execute(select(UTILISATEUR.c.id).where(UTILISATEUR.c.email == "{email}")).scalar_one()
    s.execute(insert(REINITIALISATION).values(
        id=uuid7(), utilisateur_id=uid, empreinte=empreinte(jeton), cree_le=maintenant,
        expire_le=durees.expiration_reinitialisation(maintenant),
    ))
print(jeton)
"""
# un compte par projet Playwright (front/playwright.config.ts) : l'anti-rejeu refuse deux fois un même code
PROJETS_PLAYWRIGHT = ("ordinateur", "mobile-360")


def _creer_compte(
    plateforme: Plateforme, email: str, role: str = "gerant", nom: str = "M. Essai"
) -> tuple[str, str]:
    """Compte actif (mot de passe MOT_DE_PASSE) : (identifiant, clé TOTP en hexadécimal)."""
    code = CREER_COMPTE.format(email=email, mdp=MOT_DE_PASSE, role=role, nom=nom)
    uid, secret = plateforme.python(code).stdout.split()
    return uid, secret


def _code_totp(secret: bytes) -> str:
    """RFC 6238 (SHA-1, 6 chiffres, 30 s), comme les applications d'authentification."""
    empreinte = hmac.new(secret, struct.pack(">Q", int(time.time() // 30)), hashlib.sha1).digest()
    decalage = empreinte[-1] & 0x0F
    return str((struct.unpack(">I", empreinte[decalage : decalage + 4])[0] & 0x7FFFFFFF) % 1_000_000).zfill(6)


def _client(plateforme: Plateforme) -> httpx.Client:
    return httpx.Client(base_url=plateforme.https, verify=False, timeout=10)  # noqa: S501 - certificat d'essai


@dataclass
class Session:
    client: httpx.Client
    utilisateur_id: str


@pytest.fixture(scope="module")
def session(plateforme: Plateforme) -> Iterator[Session]:
    """Gérant connecté à travers nginx (cookie lp_session)."""
    connectee = _connecter(plateforme, "essai@essai.local")
    yield connectee
    connectee.client.close()


def _connecter(plateforme: Plateforme, email: str) -> Session:
    """Nouveau gérant, connecté à travers nginx (adresse, mot de passe puis code)."""
    uid, secret = _creer_compte(plateforme, email)
    client = _client(plateforme)
    connexion = {"email": email, "mot_de_passe": MOT_DE_PASSE}
    assert client.post("/api/identity/auth/connexion", json=connexion).status_code == 200
    code = {"code": _code_totp(bytes.fromhex(secret))}
    assert client.post("/api/identity/auth/code", json=code).status_code == 200
    return Session(client, uid)


FORGES = {"X-User-Id": "0192f3a4-5b6c-7d8e-9f01-234567890c99", "X-Role": "gerant", "X-Auth-Exp": "9999999999"}
FORGES_SIGNES = {**FORGES, "X-Auth-Sig": "0" * 64}


def _verify_dans_les_journaux(plateforme: Plateforme, depuis: str) -> int:
    journaux = subprocess.run(
        ["docker", "logs", "--since", depuis, plateforme.conteneur("identity")],
        capture_output=True,
        text=True,
        check=True,
    )
    return (journaux.stdout + journaux.stderr).count("GET /auth/verify")


def test_nginx__configuration_valide_et_demarre_sans_les_services_absents(
    plateforme: Plateforme, session: Session
) -> None:
    """N1 : résolveur Docker et adresses en variables ; un service absent donne 502, pas un arrêt de nginx."""
    assert plateforme.compose("exec", "-T", "nginx", "nginx", "-t").returncode == 0
    assert session.client.get("/api/referentiel/lots").status_code == 502
    assert session.client.get("/api/identity/moi").status_code == 200


@pytest.mark.parametrize(
    "chemin", ["/api/identity/auth/verify", "/internal/healthz", "/api/identity/internal/healthz"]
)
def test_nginx__verify_et_routes_internes_fermes_au_public(
    plateforme: Plateforme, session: Session, chemin: str
) -> None:
    """N2, N3 (R0-13) : 404 depuis l'extérieur, même avec une session valide."""
    for client in (_client(plateforme), session.client):
        r = client.get(chemin)
        assert r.status_code == 404, chemin
        assert "x-auth-sig" not in r.headers


def test_nginx__entetes_forges_sans_cookie__401_json_comme_commun(plateforme: Plateforme) -> None:
    """N4 (R0-11, R0-12)."""
    r = _client(plateforme).get("/api/identity/moi", headers=FORGES_SIGNES)
    assert r.status_code == 401
    corps = r.json()
    assert (corps["code"], corps["message"], corps["details"]) == (
        "unauthenticated",
        "Votre session a expiré ou n'est pas reconnue. Reconnectez-vous.",
        {},
    )
    assert re.fullmatch(r"[0-9a-f]{32}", corps["trace_id"])


def test_nginx__session_valide_et_entetes_forges__identite_reelle(session: Session) -> None:
    """N5 (R0-12) : seule la réponse d'auth_request remplit les en-têtes d'identité."""
    r = session.client.get("/api/identity/moi", headers={**FORGES_SIGNES, "X-Role": "operateur"})
    assert (r.status_code, r.json()["id"], r.json()["role"]) == (200, session.utilisateur_id, "gerant")


def test_nginx__entetes_d_identite_vides_vers_le_front(plateforme: Plateforme) -> None:
    """N6 : le front ne reçoit jamais d'en-tête d'identité forgé ; X-Real-IP est l'adresse réelle."""
    recus = _client(plateforme).get("/", headers={**FORGES_SIGNES, "X-Real-IP": "1.2.3.4"}).json()
    for nom in ("x-user-id", "x-role", "x-auth-exp", "x-auth-sig"):
        assert recus.get(nom, "") == "", nom
    assert recus["x-real-ip"] != "1.2.3.4"


def test_nginx__x_nonce_du_client_toujours_ecrase(plateforme: Plateforme) -> None:
    """Le nonce de la politique de sécurité vient toujours de nginx ($request_id), jamais du client."""
    recus = _client(plateforme).get("/", headers={"X-Nonce": "nonce-forge"}).json()
    assert recus["x-nonce"] != "nonce-forge"
    assert re.fullmatch(r"[0-9a-f]{32}", recus["x-nonce"])


# --- écoute interne 8081 : lectures du BFF (front côté serveur), jamais depuis l'hôte -------------------


def _depuis_le_front(plateforme: Plateforme, methode: str, chemin: str, *entetes: str) -> tuple[int, str]:
    """(statut, corps) d'une requête faite depuis le conteneur du front vers http://nginx:8081."""
    options = [arg for entete in entetes for arg in ("-H", entete)]
    # HEAD : -I (avec -X HEAD, curl attendrait un corps qui ne vient jamais)
    verbe = ["-I"] if methode == "HEAD" else ["-X", methode]
    r = plateforme.compose(
        "exec",
        "-T",
        "front",
        "curl",
        "-s",
        "-w",
        "\n%{http_code}",
        *verbe,
        *options,
        f"http://nginx:8081{chemin}",
    )
    corps, _, statut = r.stdout.rpartition("\n")
    return int(statut), corps


def _cookie(session: Session) -> str:
    return f"Cookie: lp_session={session.client.cookies['lp_session']}"


def test_ecoute_interne__lecture_avec_session__meme_identite_que_le_port_public(
    plateforme: Plateforme, session: Session
) -> None:
    statut, corps = _depuis_le_front(plateforme, "GET", "/api/identity/moi", _cookie(session))
    assert statut == 200
    assert json.loads(corps)["id"] == session.utilisateur_id
    # HEAD n'est pas refusé par l'écoute : la réponse vient du service (JSON), pas du refus de nginx (HTML) ;
    # FastAPI ne répond pas à HEAD sur une route GET, d'où son propre 405
    _, entetes = _depuis_le_front(plateforme, "HEAD", "/api/identity/moi", _cookie(session))
    assert "content-type: application/json" in entetes.lower()


@pytest.mark.parametrize("methode", ["POST", "PUT", "PATCH", "DELETE"])
def test_ecoute_interne__ecriture_refusee_405(plateforme: Plateforme, session: Session, methode: str) -> None:
    """Refus de nginx lui-même (HTML), avant toute vérification d'identité ou appel au service."""
    statut, corps = _depuis_le_front(
        plateforme, methode, "/api/identity/utilisateurs/inviter", _cookie(session)
    )
    assert statut == 405
    assert "nginx" in corps


@pytest.mark.parametrize(
    "chemin",
    [
        "/api/identity/auth/verify",
        "/api/identity/auth/connexion",
        "/api/identity/auth/code",
        "/api/identity/auth/etat-session/",
        "/api/identity/auth/etat-sessionx",
        "/internal/healthz",
        "/api/identity/internal/healthz",
        "/",
    ],
)
def test_ecoute_interne__auth_internal_et_front_fermes_404(
    plateforme: Plateforme, session: Session, chemin: str
) -> None:
    assert _depuis_le_front(plateforme, "GET", chemin, _cookie(session))[0] == 404


def test_ecoute_interne__etat_session__seule_exception_dans_auth_en_lecture(
    plateforme: Plateforme, session: Session
) -> None:
    """Exception bornée (ADR 0006) : après un 401, le BFF demande à identity si la session a été coupée par
    une suspension ; lecture seule, cookie du navigateur relayé ; écritures toujours refusées par nginx."""
    statut, corps = _depuis_le_front(plateforme, "GET", "/api/identity/auth/etat-session", _cookie(session))
    assert (statut, json.loads(corps)["code"]) == (200, "session_expiree")
    statut, corps = _depuis_le_front(plateforme, "POST", "/api/identity/auth/etat-session", _cookie(session))
    assert statut == 405
    assert "nginx" in corps


def test_ecoute_interne__entetes_forges_sans_cookie__401(plateforme: Plateforme) -> None:
    entetes = [f"{nom}: {valeur}" for nom, valeur in FORGES_SIGNES.items()]
    statut, corps = _depuis_le_front(plateforme, "GET", "/api/identity/moi", *entetes)
    assert statut == 401
    assert json.loads(corps)["code"] == "unauthenticated"


def test_ecoute_interne__session_valide_et_entetes_forges__identite_reelle(
    plateforme: Plateforme, session: Session
) -> None:
    entetes = [f"{nom}: {valeur}" for nom, valeur in {**FORGES_SIGNES, "X-Role": "operateur"}.items()]
    statut, corps = _depuis_le_front(plateforme, "GET", "/api/identity/moi", _cookie(session), *entetes)
    assert (statut, json.loads(corps)["id"], json.loads(corps)["role"]) == (
        200,
        session.utilisateur_id,
        "gerant",
    )


def test_ecoute_interne__injoignable_depuis_l_hote(plateforme: Plateforme) -> None:
    publie = plateforme.compose("port", "nginx", "8081", verifier=False)
    assert publie.returncode != 0 or publie.stdout.strip() in ("", ":0")
    with socket.socket() as s:
        s.settimeout(2)
        assert s.connect_ex(("127.0.0.1", 8081)) != 0


def test_nginx__cache_auth_request_10_secondes(plateforme: Plateforme, session: Session) -> None:
    """N7 : 5 requêtes en moins de 10 s → un seul /auth/verify ; après 11 s, un nouveau."""
    time.sleep(11)
    depuis = datetime.now(UTC).isoformat()
    for _ in range(5):
        assert session.client.get("/api/identity/utilisateurs").status_code == 200
    time.sleep(1)
    assert _verify_dans_les_journaux(plateforme, depuis) == 1
    time.sleep(11)
    assert session.client.get("/api/identity/utilisateurs").status_code == 200
    time.sleep(1)
    assert _verify_dans_les_journaux(plateforme, depuis) == 2


def test_nginx__ops_reserve_a_wireguard(plateforme: Plateforme) -> None:
    """N9 (R0-09, reportée au lot 2 pour l'accès réel)."""
    assert _client(plateforme).get("/ops/").status_code == 403


def test_nginx__x_real_ip_forge_ignore(plateforme: Plateforme) -> None:
    """N10 (R0-15) : la tentative est inscrite avec l'adresse réelle, jamais celle de l'en-tête."""
    _client(plateforme).post(
        "/api/identity/auth/connexion",
        json={"email": "forge@essai.local", "mot_de_passe": "un autre mot de passe"},
        headers={"X-Real-IP": "1.2.3.4"},
    )
    ip = plateforme.compose(
        "exec",
        "-T",
        "postgres",
        "psql",
        "-U",
        "admin",
        "-d",
        "identity",
        "-tAc",
        "SELECT host(ip) FROM tentative_connexion ORDER BY cree_le DESC LIMIT 1",
    ).stdout.strip()
    assert ip and ip != "1.2.3.4"


def test_nginx__certificat_de_make_dev_certs_et_en_tetes_de_securite(plateforme: Plateforme) -> None:
    """N11 (R0-25)."""
    servi = ssl.PEM_cert_to_DER_cert(
        ssl.get_server_certificate(("127.0.0.1", int(plateforme.env["LEPALIER_PORT_HTTPS"])))
    )
    attendu = ssl.PEM_cert_to_DER_cert(plateforme.certificat.read_text())
    assert hashlib.sha256(servi).hexdigest() == hashlib.sha256(attendu).hexdigest()
    r = _client(plateforme).get("/")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["referrer-policy"] == "no-referrer"
    assert "server" not in r.headers or "/" not in r.headers["server"]


def test_nginx__front_absent__page_de_maintenance(plateforme: Plateforme) -> None:
    """N12 : tant que le front ne répond pas, page de maintenance en 503, jamais une erreur brute."""
    plateforme.compose("stop", "front")
    try:
        r = _client(plateforme).get("/")
        assert r.status_code == 503
        assert "<title>Maintenance en cours</title>" in r.text
    finally:
        plateforme.compose("start", "front")


def test_nginx__compte_suspendu_refuse_au_plus_10_secondes_apres(
    plateforme: Plateforme, session: Session
) -> None:
    """N8 (R0-07) : le cache d'auth_request garde au plus 10 s une session devenue invalide."""
    assert session.client.get("/api/identity/utilisateurs").status_code == 200
    plateforme.compose(
        "exec",
        "-T",
        "postgres",
        "psql",
        "-U",
        "admin",
        "-d",
        "identity",
        "-c",
        f"UPDATE utilisateur SET statut = 'suspendu' WHERE id = '{session.utilisateur_id}'",
    )
    debut = time.monotonic()
    while session.client.get("/api/identity/utilisateurs").status_code == 200:
        assert time.monotonic() - debut < 11, "toujours accepté plus de 10 s après la suspension"
        time.sleep(0.5)
    assert session.client.get("/api/identity/utilisateurs").status_code == 401


def test_e2e__playwright_sur_le_vrai_front(plateforme: Plateforme) -> None:
    """Front réel à la place du faux : essais de bout en bout Playwright (accessibilité axe-core, politique de
    sécurité sans violation, clavier, 360 px, zoom 200 %). Avant N13, qui vide le compteur de connexions."""
    assert (RACINE / "front" / "node_modules" / "@playwright" / "test").is_dir(), (
        "Dépendances du front absentes : lancez « cd front && npm ci » avant make test-plateforme."
    )
    _creer_compte(plateforme, "e2e@essai.local")
    comptes_code = {}
    for projet in PROJETS_PLAYWRIGHT:
        email = f"e2e-code-{projet}@essai.local"
        uid, secret = _creer_compte(plateforme, email)
        secours = plateforme.python(AJOUTER_CODES_SECOURS.format(uid=uid)).stdout.split()
        comptes_code[projet] = {"email": email, "secret": secret, "secours": secours}
    # un gérant par projet pour l'accueil (connexion complète, puis déconnexion)
    comptes_accueil = {}
    for projet in PROJETS_PLAYWRIGHT:
        email = f"e2e-accueil-{projet}@essai.local"
        _, secret = _creer_compte(plateforme, email)
        comptes_accueil[projet] = {"email": email, "secret": secret, "secours": []}
    # administration : un gérant et un associé par projet
    comptes_admin = {}
    for projet in PROJETS_PLAYWRIGHT:
        # noms distincts d'un projet à l'autre : tous les comptes apparaissent dans la même liste
        for role, nom in [("gerant", f"M. Gérant {projet}"), ("associe", f"Mme Associée {projet}")]:
            email = f"e2e-admin-{role}-{projet}@essai.local"
            _, secret = _creer_compte(plateforme, email, role=role, nom=nom)
            comptes_admin[f"{role}-{projet}"] = {"email": email, "secret": secret, "secours": [], "nom": nom}
        # comptes visés par les actions de la fiche « Gérer l'accès » (6.3) : un associé actif, une invitation
        cible = f"Mme Cible {projet}"
        _creer_compte(plateforme, f"e2e-cible-{projet}@essai.local", role="associe", nom=cible)
        comptes_admin[f"cible-{projet}"] = {
            "email": f"e2e-cible-{projet}@essai.local",
            "secret": "",
            "secours": [],
            "nom": cible,
        }
        # écran 6.4 : un associé dont le gérant change le rôle, un second gérant qui quitte lui-même ce rôle
        nom_role = f"Mme Rôle {projet}"
        _creer_compte(plateforme, f"e2e-role-{projet}@essai.local", role="associe", nom=nom_role)
        comptes_admin[f"role-{projet}"] = {
            "email": f"e2e-role-{projet}@essai.local",
            "secret": "",
            "secours": [],
            "nom": nom_role,
        }
        nom_quitte = f"M. Quitte {projet}"
        _, secret_quitte = _creer_compte(plateforme, f"e2e-quitte-{projet}@essai.local", nom=nom_quitte)
        comptes_admin[f"quitte-{projet}"] = {
            "email": f"e2e-quitte-{projet}@essai.local",
            "secret": secret_quitte,
            "secours": [],
            "nom": nom_quitte,
        }
        invitee = f"M. Invité {projet}"
        plateforme.python(INVITER.format(email=f"e2e-invite-{projet}@essai.local", nom=invitee))
        comptes_admin[f"invite-{projet}"] = {
            "email": f"e2e-invite-{projet}@essai.local",
            "secret": "",
            "secours": [],
            "nom": invitee,
        }
    # écran 9 : un compte et un lien de réinitialisation par projet (le changement réussi consomme le lien)
    reinitialisations = {}
    for projet in PROJETS_PLAYWRIGHT:
        email = f"e2e-reinit-{projet}@essai.local"
        _, secret = _creer_compte(plateforme, email)
        jeton = plateforme.python(REINITIALISER.format(email=email)).stdout.strip()
        reinitialisations[projet] = {"email": email, "secret": secret, "jeton": jeton}
    # captures de la revue UX (si LEPALIER_E2E_CAPTURES) : un compte, une invitation et un lien par projet
    captures = {}
    for projet in PROJETS_PLAYWRIGHT:
        email = f"e2e-captures-{projet}@essai.local"
        _, secret = _creer_compte(plateforme, email, nom=f"M. Captures {projet}")
        invitation = plateforme.python(
            INVITER.format(email=f"e2e-captures-invite-{projet}@essai.local", nom="Mme Durand")
        ).stdout.strip()
        lien = plateforme.python(REINITIALISER.format(email=email)).stdout.strip()
        captures[projet] = {
            "email": email,
            "secret": secret,
            "invitation": invitation,
            "reinitialisation": lien,
        }
    # une invitation par projet : l'activation la consomme
    invitations = {
        projet: plateforme.python(
            INVITER.format(email=f"e2e-activation-{projet}@essai.local", nom="M. Essai")
        ).stdout.strip()
        for projet in PROJETS_PLAYWRIGHT
    }
    plateforme.compose(
        "up",
        "-d",
        "--no-build",
        "--force-recreate",
        "--wait",
        "--wait-timeout",
        "240",
        "front",
        faux_front=False,
    )
    # Playwright dans son image : dépôt en lecture seule, uid de l'utilisateur, réseau de l'hôte,
    # résultats dans le /tmp du conteneur : rien n'est écrit dans le dépôt
    variables = {
        "LEPALIER_E2E_URL": plateforme.https,
        "LEPALIER_E2E_EMAIL": "e2e@essai.local",
        "LEPALIER_E2E_MOT_DE_PASSE": MOT_DE_PASSE,
        "LEPALIER_E2E_COMPTES_CODE": json.dumps(comptes_code),
        "LEPALIER_E2E_INVITATIONS": json.dumps(invitations),
        "LEPALIER_E2E_COMPTES_ACCUEIL": json.dumps(comptes_accueil),
        "LEPALIER_E2E_COMPTES_ADMIN": json.dumps(comptes_admin),
        "LEPALIER_E2E_REINITIALISATIONS": json.dumps(reinitialisations),
        "LEPALIER_E2E_COMPTES_CAPTURES": json.dumps(captures),
        # captures de la revue UX, écrites dans le dossier de l'hôte monté (LEPALIER_E2E_RESULTATS_HOTE)
        "LEPALIER_E2E_CAPTURES": os.environ.get("LEPALIER_E2E_CAPTURES", ""),
        # essai de charge (diagnostic : processeur ralenti, écritures suivies d'un changement de page)
        "LEPALIER_E2E_CHARGE": os.environ.get("LEPALIER_E2E_CHARGE", ""),
        # dossiers du conteneur Playwright, pas de l'hôte
        # dossier parent monté si les résultats sont gardés sur l'hôte : Playwright vide et recrée le sien
        "LEPALIER_E2E_SORTIE": "/tmp/hote/resultats"  # noqa: S108
        if "LEPALIER_E2E_RESULTATS_HOTE" in os.environ
        else "/tmp/resultats",  # noqa: S108
        "HOME": "/tmp",  # noqa: S108
    }
    r = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--network",
            "host",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            *[arg for nom, valeur in variables.items() for arg in ("-e", f"{nom}={valeur}")],
            "-v",
            f"{RACINE}:/srv/depot:ro",
            # résultats (traces, captures) gardés sur l'hôte pour un diagnostic, seulement si demandé
            *(
                ["-v", f"{os.environ['LEPALIER_E2E_RESULTATS_HOTE']}:/tmp/hote"]
                if "LEPALIER_E2E_RESULTATS_HOTE" in os.environ
                else []
            ),
            "-w",
            "/srv/depot/front",
            IMAGE_PLAYWRIGHT,
            "npx",
            "--no-install",
            "playwright",
            "test",
            # arguments de diagnostic seulement (par exemple --grep … --repeat-each 10) ; vide d'ordinaire
            *os.environ.get("LEPALIER_E2E_ARGS", "").split(),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    # sortie complète de Playwright, affichée par pytest en cas d'échec : le premier échec n'est jamais coupé
    print(r.stdout)
    print(r.stderr)
    assert r.returncode == 0, "essais Playwright en échec : voir la sortie complète ci-dessus"


def test_identity_arrete__accueil_indisponible_sans_deconnexion_puis_retour(plateforme: Plateforme) -> None:
    """R0-36 (UX-30) : identity arrêté, une session valide n'est jamais traitée comme expirée ; nginx répond
    par une erreur 5xx (jamais 401) ; l'accueil dit « Information momentanément indisponible »."""
    plateforme.compose("up", "-d", "--no-build", "--wait", "--wait-timeout", "240", "front", faux_front=False)
    # session propre à l'essai : celle du module a pu être coupée par un essai précédent (suspension)
    session = _connecter(plateforme, "indisponible@essai.local")
    jeton = session.client.cookies["lp_session"]
    plateforme.compose("stop", "identity")
    try:
        # vérification d'identité de nginx (auth_request) en échec : erreur du serveur, jamais 401
        api = session.client.get("/api/identity/moi")
        assert api.status_code >= 500, api.status_code
        accueil = session.client.get("/", follow_redirects=False)
        assert accueil.status_code == 200, (accueil.status_code, accueil.headers.get("location"))
        assert "Information momentanément indisponible" in accueil.text
        assert "set-cookie" not in accueil.headers
        assert session.client.cookies["lp_session"] == jeton
    finally:
        plateforme.compose("up", "-d", "--no-build", "--wait", "--wait-timeout", "240", "identity")
    accueil = session.client.get("/", follow_redirects=False)
    assert accueil.status_code == 200
    assert "<h1>À faire</h1>" in accueil.text
    session.client.close()


def test_nginx__limite_de_debit_sur_auth__429_json(plateforme: Plateforme) -> None:
    """N13 (C9, ADR 0006) : 10 par minute et rafale de 10 : 11 requêtes passent, la 12e reçoit 429.

    Avec la vraie limite : nginx recréé à partir de compose.dev.yml seul (10r/m), compteurs neufs ; puis remis
    à la valeur des essais (compose.essai.yml) pour les essais suivants.
    """
    _recreer_nginx(plateforme, valeur_reelle=True)
    try:
        _limite_de_debit_reelle(plateforme)
    finally:
        _recreer_nginx(plateforme, valeur_reelle=False)


def _recreer_nginx(plateforme: Plateforme, valeur_reelle: bool) -> None:
    attente = ["--wait", "--wait-timeout", "240"]
    options = ["up", "-d", "--no-build", "--no-deps", "--force-recreate", *attente, "nginx"]
    plateforme.compose(*options, faux_front=not valeur_reelle)


def _limite_de_debit_reelle(plateforme: Plateforme) -> None:
    client = _client(plateforme)
    # une adresse e-mail par requête : le verrou d'identity (5 échecs par compte et adresse IP) ne joue pas
    statuts = [
        client.post(
            "/api/identity/auth/connexion", json={"email": f"x{n}@essai.local", "mot_de_passe": "faux"}
        )
        for n in range(12)
    ]
    assert [r.status_code for r in statuts[:11]].count(429) == 0
    refus = statuts[11]
    assert refus.status_code == 429
    corps = refus.json()
    assert (corps["code"], corps["message"], corps["details"]) == (
        "trop_de_requetes",
        "Trop de demandes en peu de temps. Patientez une minute, puis réessayez.",
        {},
    )
    assert re.fullmatch(r"[0-9a-f]{32}", corps["trace_id"])


# --- jeu de recette du lot 0 ----------------------------------------------------------------------------


def test_recette_lot0__jeu_cree_dans_identity__invitations_au_nom_du_gerant_puis_relance_sans_effet(
    plateforme: Plateforme,
) -> None:
    """make recette LOT=0 sur le projet d'essai : lien du gérant affiché une fois, deux invitations."""
    prefixe = ["docker", "compose", "-f", str(RACINE / "compose.dev.yml"), "-f", str(ESSAI)]
    env = {
        **plateforme.env,
        "LEPALIER_COMPOSE": shlex.join([*prefixe, "--env-file", str(plateforme.fichier_env), "-p", PROJET]),
    }

    def lancer() -> subprocess.CompletedProcess[str]:
        commande = ["python3", str(RACINE / "scripts" / "recette" / "lot-0.py")]
        return subprocess.run(commande, cwd=RACINE, env=env, capture_output=True, text=True, check=False)

    premier = lancer()
    assert premier.returncode == 0, premier.stdout + premier.stderr
    assert len(re.findall(r"/activation#[A-Za-z0-9_-]{43}", premier.stdout)) == 1
    assert premier.stdout.count("Invitation créée pour") == 2
    invite_par = plateforme.python(
        "from sqlalchemy import select; from app.db import fabrique; from app.models import UTILISATEUR;"
        "s = fabrique()(); r = dict(s.execute(select(UTILISATEUR.c.email, UTILISATEUR.c.invite_par)).all());"
        "print(r['associe.jeu@test.local'] == r['operateur.jeu@test.local'] == "
        "s.execute(select(UTILISATEUR.c.id).where(UTILISATEUR.c.email == 'gerant@test.local')).scalar_one())"
    )
    assert invite_par.stdout.strip() == "True"
    api = f"http://127.0.0.1:{plateforme.env['LEPALIER_PORT_MAILPIT']}/api/v1"
    attendus = {"associe.jeu@test.local", "operateur.jeu@test.local"}
    recus: set[str] = set()
    limite = time.monotonic() + 60
    while time.monotonic() < limite and recus != attendus:
        messages = httpx.get(f"{api}/messages").json()["messages"]
        recus = {d["Address"] for m in messages for d in m["To"]} & attendus
        time.sleep(1)
    assert recus == attendus

    second = lancer()
    assert second.returncode == 0, second.stdout + second.stderr
    assert "/activation#" not in second.stdout
    assert second.stdout.count("déjà présent") == 3
