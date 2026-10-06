from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from commun.secrets import SecretInvalide, lire_cles_hmac, lire_empreintes, lire_jeton, lire_secret


def _ecrire(dossier: Path, nom: str, contenu: str, mode: int = 0o400) -> Path:
    chemin = dossier / nom
    chemin.write_text(contenu)
    chemin.chmod(mode)
    return chemin


@pytest.mark.parametrize("mode", [0o400, 0o600])
def test_lire_secret__droits_du_seul_proprietaire__accepte(tmp_path: Path, mode: int) -> None:
    assert lire_secret(_ecrire(tmp_path, "s", "  valeur\n", mode)) == "valeur"


@pytest.mark.parametrize("mode", [0o440, 0o404, 0o644, 0o640])
def test_lire_secret__lisible_par_le_groupe_ou_les_autres__refuse(tmp_path: Path, mode: int) -> None:
    with pytest.raises(SecretInvalide, match="ADR 0007"):
        lire_secret(_ecrire(tmp_path, "s", "valeur", mode))


def test_lire_secret__absent__message_qui_dit_quoi_faire(tmp_path: Path) -> None:
    with pytest.raises(SecretInvalide, match="make dev-secrets"):
        lire_secret(tmp_path / "absent")


def test_lire_secret__vide__refuse(tmp_path: Path) -> None:
    with pytest.raises(SecretInvalide, match="vide"):
        lire_secret(_ecrire(tmp_path, "s", "\n"))


def test_lire_cles_hmac__une_cle_par_ligne_la_premiere_signe(tmp_path: Path) -> None:
    courante, ancienne = "ab" * 32, "cd" * 32
    chemin = _ecrire(tmp_path, "cle_hmac_identite", f"{courante}\n\n{ancienne}\n")
    assert lire_cles_hmac(chemin) == [bytes.fromhex(courante), bytes.fromhex(ancienne)]


@pytest.mark.parametrize("contenu", ["pas-de-l-hexa", "ab" * 8])
def test_lire_cles_hmac__cle_illisible_ou_trop_courte__refusee(tmp_path: Path, contenu: str) -> None:
    with pytest.raises(SecretInvalide):
        lire_cles_hmac(_ecrire(tmp_path, "cle_hmac_identite", contenu))


def test_lire_jeton__par_couple(tmp_path: Path) -> None:
    _ecrire(tmp_path, "jeton_facturation_vers_documents", "jeton-secret")
    assert lire_jeton(tmp_path, "facturation", "documents") == "jeton-secret"


def test_lire_empreintes__celles_de_l_appele_seulement(tmp_path: Path) -> None:
    empreinte = hashlib.sha256(b"jeton-secret").hexdigest()
    _ecrire(tmp_path, "empreinte_facturation_vers_documents", empreinte + "\n")
    _ecrire(tmp_path, "empreinte_envois_vers_documents", empreinte)
    _ecrire(tmp_path, "empreinte_documents_vers_envois", empreinte)
    _ecrire(tmp_path, "cle_hmac_identite", "ab" * 32)
    assert lire_empreintes(tmp_path, "documents") == {
        "facturation": bytes.fromhex(empreinte),
        "envois": bytes.fromhex(empreinte),
    }


def test_lire_empreintes__aucun_appel_interne__dictionnaire_vide(tmp_path: Path) -> None:
    assert lire_empreintes(tmp_path, "identity") == {}
    assert lire_empreintes(tmp_path / "absent", "identity") == {}


@pytest.mark.parametrize("contenu", ["abc", "ab" * 16])
def test_lire_empreintes__empreinte_mal_formee__refusee(tmp_path: Path, contenu: str) -> None:
    _ecrire(tmp_path, "empreinte_facturation_vers_documents", contenu)
    with pytest.raises(SecretInvalide):
        lire_empreintes(tmp_path, "documents")
