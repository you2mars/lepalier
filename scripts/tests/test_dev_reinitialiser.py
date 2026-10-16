"""make dev-reinitialiser : efface les données de dev (base, flux NATS, Mailpit) seulement sur confirmation
(règle 6 de CLAUDE.md). L'essai réel, sur une copie isolée de la plateforme, est décrit au journal du lot 0."""

from __future__ import annotations

import subprocess
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]


def _make(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - commande fixe
        ["make", "-s", "--no-print-directory", *arguments],  # noqa: S607
        cwd=RACINE,
        capture_output=True,
        text=True,
        check=False,
    )


def test_dev_reinitialiser__sans_confirmation__rien_n_est_efface() -> None:
    r = _make("dev-reinitialiser", "COMPOSE_DEV=false")
    assert r.returncode != 0
    assert r.stdout == (
        "Rien n'a été effacé. Cette commande supprime les comptes, les événements et les e-mails de la "
        "plateforme de dev ; pour confirmer : make dev-reinitialiser CONFIRMER=oui\n"
    )


def test_dev_reinitialiser__confirme__volumes_supprimes_puis_redemarrage() -> None:
    r = _make("-n", "dev-reinitialiser", "CONFIRMER=oui")
    lignes = [ligne for ligne in r.stdout.splitlines() if ligne.startswith("docker compose")]
    assert lignes[0] == "docker compose -f compose.dev.yml down --volumes --remove-orphans"
    assert lignes[-1] == "docker compose -f compose.dev.yml up -d --wait --wait-timeout 240"
