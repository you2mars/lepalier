"""Hook Git pre-push (règle 9 de CLAUDE.md) : aucun push direct sur main, quelle que soit la branche locale.

Dépôts temporaires seulement (un serveur nu et un clone), jamais le dépôt LePalier.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[2]
HOOK = RACINE / "scripts" / "git-hooks" / "pre-push"
MESSAGE = "Refusé : aucun push direct sur main (règle 9 de CLAUDE.md)."


def _git(dossier: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "GIT_AUTHOR_NAME": "essai", "GIT_AUTHOR_EMAIL": "essai@essai.local"}
    env |= {"GIT_COMMITTER_NAME": "essai", "GIT_COMMITTER_EMAIL": "essai@essai.local"}
    return subprocess.run(
        ["git", *arguments], cwd=dossier, env=env, capture_output=True, text=True, check=False
    )


@pytest.fixture
def clone(tmp_path: Path) -> Path:
    serveur, local = tmp_path / "serveur.git", tmp_path / "local"
    _git(tmp_path, "init", "--bare", "-b", "main", str(serveur))
    _git(tmp_path, "clone", str(serveur), str(local))
    _git(local, "checkout", "-b", "main")
    (local / "a.txt").write_text("a\n")
    _git(local, "add", "a.txt")
    _git(local, "commit", "-m", "premier")
    # premier push de main avant l'installation du hook : le serveur a une branche main, comme GitHub
    assert _git(local, "push", "origin", "main").returncode == 0
    (local / ".git" / "hooks" / "pre-push").symlink_to(HOOK)
    return local


def _commit(depot: Path, nom: str) -> None:
    (depot / nom).write_text(nom)
    _git(depot, "add", nom)
    _git(depot, "commit", "-m", nom)


def test_hook__push_sur_main__refuse_avec_message(clone: Path) -> None:
    _commit(clone, "b.txt")
    r = _git(clone, "push", "origin", "main")
    assert r.returncode != 0
    assert MESSAGE in r.stderr


def test_hook__autre_branche_locale_vers_main__refuse(clone: Path) -> None:
    _git(clone, "checkout", "-b", "lot/9-essai")
    _commit(clone, "c.txt")
    assert _git(clone, "push", "origin", "lot/9-essai:main").returncode != 0
    assert _git(clone, "push", "origin", "HEAD:refs/heads/main").returncode != 0


def test_hook__suppression_de_main__refusee(clone: Path) -> None:
    assert _git(clone, "push", "origin", ":main").returncode != 0


def test_hook__autre_branche__acceptee(clone: Path) -> None:
    _git(clone, "checkout", "-b", "lot/9-essai")
    _commit(clone, "d.txt")
    r = _git(clone, "push", "origin", "lot/9-essai")
    assert r.returncode == 0, r.stderr
    assert MESSAGE not in r.stderr


def test_make_hooks__installe_le_lien_sans_ecraser_un_hook_existant(tmp_path: Path) -> None:
    depot = tmp_path / "depot"
    _git(tmp_path, "init", str(depot))
    r = subprocess.run(
        ["make", "-C", str(RACINE), "hooks", f"DEPOT_GIT={depot}"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    installe = depot / ".git" / "hooks" / "pre-push"
    assert installe.is_symlink() and installe.resolve() == HOOK.resolve()
    assert _git(depot, "config", "--get", "core.hooksPath").stdout == ""
    # deuxième passage : rien ne change
    assert (
        subprocess.run(
            ["make", "-C", str(RACINE), "hooks", f"DEPOT_GIT={depot}"], capture_output=True, check=False
        ).returncode
        == 0
    )
    # un pre-push personnel déjà présent n'est jamais écrasé
    autre = tmp_path / "autre"
    _git(tmp_path, "init", str(autre))
    (autre / ".git" / "hooks" / "pre-push").write_text("#!/bin/sh\nexit 0\n")
    r = subprocess.run(
        ["make", "-C", str(RACINE), "hooks", f"DEPOT_GIT={autre}"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode != 0
    assert (autre / ".git" / "hooks" / "pre-push").read_text() == "#!/bin/sh\nexit 0\n"
