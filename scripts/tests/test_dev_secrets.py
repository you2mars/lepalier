"""make dev-secrets (ADR 0007) : génération, droits, et lecture par l'uid 10001 d'un secret monté par Compose.

Travaille uniquement dans des dossiers temporaires, jamais dans deploy/secrets/. Docker requis.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(shutil.which("docker") is None, reason="Docker requis")

RACINE = Path(__file__).resolve().parents[2]
SCRIPT = RACINE / "scripts" / "dev-secrets.sh"
# même image que le script (épinglée par digest)
IMAGE = next(
    ligne.split("=", 1)[1].strip('"')
    for ligne in SCRIPT.read_text().splitlines()
    if ligne.startswith("IMAGE_OUTIL=")
)


def _generer(
    dossier: Path, appels: str, force: bool = False, chemin: str | None = None
) -> subprocess.CompletedProcess[str]:
    fichier_appels = dossier.parent / "appels.txt"
    fichier_appels.write_text(appels)
    env = {**os.environ, "SECRETS_DIR": str(dossier), "APPELS_INTERNES": str(fichier_appels)}
    if chemin is not None:
        env["PATH"] = chemin
    env.pop("FORCE", None)
    if force:
        env["FORCE"] = "1"
    return subprocess.run(
        ["bash", str(SCRIPT)], cwd=RACINE, env=env, capture_output=True, text=True, check=False
    )


def _lire_en_tant_que(uid: int, fichier: Path) -> str | None:
    """Contenu lu par un conteneur tournant sous `uid`, ou None si la lecture est refusée."""
    r = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--user",
            f"{uid}:{uid}",
            "-v",
            f"{fichier}:/run/secrets/s:ro",
            IMAGE,
            "cat",
            "/run/secrets/s",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return r.stdout if r.returncode == 0 else None


@pytest.fixture
def dossier(tmp_path: Path) -> Path:
    return tmp_path / "secrets"


APPELS = "# commentaire\n\nfacturation documents\nenvois documents\n"
ATTENDUS = {
    "cle_hmac_identite",
    "jeton_facturation_vers_documents",
    "empreinte_facturation_vers_documents",
    "jeton_envois_vers_documents",
    "empreinte_envois_vers_documents",
}


def test_dev_secrets__fichiers_attendus_10001_0400_dans_un_dossier_0700(dossier: Path) -> None:
    r = _generer(dossier, APPELS)
    assert r.returncode == 0, r.stdout + r.stderr
    assert {f.name for f in dossier.iterdir()} == ATTENDUS
    assert dossier.stat().st_mode & 0o777 == 0o700
    for f in dossier.iterdir():
        etat = f.stat()
        assert (etat.st_uid, etat.st_gid, etat.st_mode & 0o777) == (10001, 10001, 0o400), f.name


def test_dev_secrets__valeurs_jamais_affichees_et_bien_formees(dossier: Path) -> None:
    r = _generer(dossier, APPELS)
    sortie = r.stdout + r.stderr
    cle = _lire_en_tant_que(10001, dossier / "cle_hmac_identite")
    jeton = _lire_en_tant_que(10001, dossier / "jeton_facturation_vers_documents")
    empreinte = _lire_en_tant_que(10001, dossier / "empreinte_facturation_vers_documents")
    assert cle is not None and jeton is not None and empreinte is not None
    assert len(cle.strip()) == 64 and int(cle, 16) >= 0
    assert len(jeton) >= 43 and "\n" not in jeton and "=" not in jeton
    assert empreinte.strip() == hashlib.sha256(jeton.encode()).hexdigest()
    for valeur in (cle.strip(), jeton, empreinte.strip()):
        assert valeur not in sortie


def test_dev_secrets__uid_10001_lit_les_autres_non(dossier: Path) -> None:
    _generer(dossier, APPELS)
    cible = dossier / "jeton_facturation_vers_documents"
    assert _lire_en_tant_que(10001, cible)
    assert _lire_en_tant_que(10002, cible) is None
    with pytest.raises(PermissionError):
        cible.read_text()


def test_dev_secrets__secret_monte_par_compose__lisible_par_10001_seulement(
    dossier: Path, tmp_path: Path
) -> None:
    _generer(dossier, APPELS)
    compose = tmp_path / "compose.yml"
    compose.write_text(
        f"""
name: essai-dev-secrets-{os.getpid()}
services:
  service:
    image: {IMAGE}
    network_mode: none
    entrypoint: ["cat", "/run/secrets/cle_hmac_identite"]
    secrets: [cle_hmac_identite]
secrets:
  cle_hmac_identite:
    file: {dossier / "cle_hmac_identite"}
"""
    )

    def lancer(uid: int) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "docker",
                "compose",
                "-f",
                str(compose),
                "run",
                "--rm",
                "--no-deps",
                "-q",
                "--user",
                f"{uid}:{uid}",
                "service",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    assert lancer(10001).returncode == 0
    assert lancer(10002).returncode != 0


def test_dev_secrets__sans_force__rien_n_est_regenere(dossier: Path) -> None:
    _generer(dossier, APPELS)
    avant = _lire_en_tant_que(10001, dossier / "cle_hmac_identite")
    r = _generer(dossier, APPELS)
    assert r.returncode == 0
    assert "FORCE=1" in r.stdout
    assert _lire_en_tant_que(10001, dossier / "cle_hmac_identite") == avant


def test_dev_secrets__avec_force__nouvelles_valeurs(dossier: Path) -> None:
    _generer(dossier, APPELS)
    avant = _lire_en_tant_que(10001, dossier / "cle_hmac_identite")
    assert _generer(dossier, "facturation documents\n", force=True).returncode == 0
    assert _lire_en_tant_que(10001, dossier / "cle_hmac_identite") != avant
    assert "jeton_envois_vers_documents" not in {f.name for f in dossier.iterdir()}


@pytest.mark.parametrize(
    "ligne", ["facturation", "facturation inconnu", "facturation facturation", "facturation documents envois"]
)
def test_dev_secrets__ligne_invalide__echec_et_secrets_existants_conserves(dossier: Path, ligne: str) -> None:
    _generer(dossier, APPELS)
    avant = _lire_en_tant_que(10001, dossier / "cle_hmac_identite")
    r = _generer(dossier, ligne + "\n", force=True)
    assert r.returncode != 0
    assert "Ligne invalide" in r.stdout
    assert {f.name for f in dossier.iterdir()} == ATTENDUS
    assert _lire_en_tant_que(10001, dossier / "cle_hmac_identite") == avant


def test_dev_secrets__image_outil_epinglee_par_digest() -> None:
    assert "@sha256:" in IMAGE


def test_dev_secrets__echec_de_docker_run__message_clair_et_code_d_erreur(
    dossier: Path, tmp_path: Path
) -> None:
    faux = tmp_path / "bin"
    faux.mkdir()
    (faux / "docker").write_text("#!/bin/sh\nexit 1\n")
    (faux / "docker").chmod(0o755)
    r = _generer(dossier, APPELS, chemin=f"{faux}:{os.environ['PATH']}")
    assert r.returncode != 0
    assert "leurs droits n'ont pas pu être posés" in r.stderr
    assert "make dev-secrets FORCE=1" in r.stderr
    for f in dossier.iterdir():
        assert f.stat().st_mode & 0o077 == 0, f.name
