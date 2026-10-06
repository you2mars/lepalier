"""Plateforme de développement (étape 5) : images, Compose et nginx, essayés pour de vrai avec Docker.

Lancés seulement par `make test-plateforme` (LEPALIER_PLATEFORME=1), qui construit d'abord les images
locales ; `make test` les ignore. Job CI « plateforme », filtré par chemins.
"""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import httpx
import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("LEPALIER_PLATEFORME") != "1", reason="make test-plateforme (images construites, Docker)"
)

IMAGE_IDENTITY = "ghcr.io/you2mars/identity:dev"
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
URL_PUBLIQUE = "https://192.0.2.10"


def _port_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@dataclass
class Plateforme:
    env: dict[str, str]
    secrets: Path

    def compose(self, *arguments: str, verifier: bool = True) -> subprocess.CompletedProcess[str]:
        r = subprocess.run(
            ["docker", "compose", "-f", str(RACINE / "compose.dev.yml"), "-p", PROJET, *arguments],
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
    plateforme.compose("up", "-d", "--no-build", "--wait", "--wait-timeout", "240", "identity")


@pytest.fixture(scope="module")
def plateforme(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Plateforme]:
    dossier = tmp_path_factory.mktemp("plateforme")
    secrets = dossier / "secrets"
    env = {
        **os.environ,
        "SECRETS_DIR": str(secrets),
        "LEPALIER_SECRETS": str(secrets),
        "LEPALIER_URL_PUBLIQUE": URL_PUBLIQUE,
        "LEPALIER_PORT_POSTGRES": str(_port_libre()),
        "LEPALIER_PORT_NATS": str(_port_libre()),
        "LEPALIER_PORT_NATS_SUIVI": str(_port_libre()),
        "LEPALIER_PORT_MAILPIT": str(_port_libre()),
        "LEPALIER_PORT_SMTP": str(_port_libre()),
    }
    subprocess.run(["bash", "scripts/dev-secrets.sh"], cwd=RACINE, env=env, check=True, capture_output=True)
    essai = Plateforme(env=env, secrets=secrets)
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


def test_compose__reseaux_de_chaque_conteneur(plateforme: Plateforme) -> None:
    """P3 (TEC-SEC-06) : identity sur backend et egress-mail seulement ; backend interne."""
    assert _reseaux(plateforme, "identity") == {"backend", "egress-mail"}
    assert _reseaux(plateforme, "identity-migrations") == {"backend"}
    assert _reseaux(plateforme, "postgres") == {"backend", "outils-dev"}
    assert _reseaux(plateforme, "nats") == {"backend", "outils-dev"}
    assert _reseaux(plateforme, "mailpit") == {"egress-mail"}
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
    assert re.search(rf"{re.escape(URL_PUBLIQUE)}/activation#[A-Za-z0-9_-]{{43}}", texte)


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
