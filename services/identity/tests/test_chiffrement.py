from __future__ import annotations

import hashlib
import hmac
import os

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.engines.chiffrement import (
    Cle,
    CleInvalide,
    DechiffrementImpossible,
    chiffrer,
    dechiffrer,
    lire_cles,
    pseudonymiser,
)
from commun.ids import uuid7

CLE_1 = Cle(version=1, valeur=b"\x11" * 32)
CLE_2 = Cle(version=2, valeur=b"\x22" * 32)
UTILISATEUR = uuid7().bytes


def test_lire_cles__format_version_espace_hexa__premiere_chiffre() -> None:
    texte = f"2 {'22' * 32}\n\n1 {'11' * 32}\n"
    assert lire_cles(texte) == [CLE_2, CLE_1]


@pytest.mark.parametrize(
    "texte",
    [
        "",
        f"1 {'11' * 16}",
        f"1 {'zz' * 32}",
        f"0 {'11' * 32}",
        f"256 {'11' * 32}",
        f"un {'11' * 32}",
        f"1 {'11' * 32}\n1 {'22' * 32}",
        "11" * 32,
    ],
)
def test_lire_cles__version_dupliquee_ou_cle_de_mauvaise_taille__refus(texte: str) -> None:
    with pytest.raises(CleInvalide):
        lire_cles(texte)


def test_chiffrer__format_version_nonce_texte_etiquette() -> None:
    secret = os.urandom(20)
    donnees = chiffrer(secret, [CLE_2, CLE_1], UTILISATEUR)
    assert donnees[0] == 2
    assert len(donnees) == 1 + 12 + 20 + 16
    assert len(donnees) >= 49


def test_chiffrer__deux_chiffrements_du_meme_secret_different() -> None:
    secret = os.urandom(20)
    assert chiffrer(secret, [CLE_1], UTILISATEUR) != chiffrer(secret, [CLE_1], UTILISATEUR)


@given(st.binary(min_size=1, max_size=64))
def test_dechiffrer__aller_retour(secret: bytes) -> None:
    assert dechiffrer(chiffrer(secret, [CLE_1], UTILISATEUR), [CLE_1], UTILISATEUR) == secret


def test_dechiffrer__autre_utilisateur_en_donnee_associee__refus() -> None:
    donnees = chiffrer(os.urandom(20), [CLE_1], UTILISATEUR)
    with pytest.raises(DechiffrementImpossible):
        dechiffrer(donnees, [CLE_1], uuid7().bytes)


@pytest.mark.parametrize("position", [0, 1, 13, 40, -1])
def test_dechiffrer__octet_altere__refus(position: int) -> None:
    donnees = bytearray(chiffrer(os.urandom(20), [CLE_1, CLE_2], UTILISATEUR))
    donnees[position] ^= 0x01
    with pytest.raises(DechiffrementImpossible):
        dechiffrer(bytes(donnees), [CLE_1, CLE_2], UTILISATEUR)


def test_dechiffrer__ancienne_version_encore_presente__ok_absente__refus() -> None:
    secret = os.urandom(20)
    ancien = chiffrer(secret, [CLE_1], UTILISATEUR)
    assert dechiffrer(ancien, [CLE_2, CLE_1], UTILISATEUR) == secret
    with pytest.raises(DechiffrementImpossible):
        dechiffrer(ancien, [CLE_2], UTILISATEUR)


@pytest.mark.parametrize("donnees", [b"", b"\x01", b"\x01" + b"\x00" * 20])
def test_dechiffrer__donnees_tronquees__refus(donnees: bytes) -> None:
    with pytest.raises(DechiffrementImpossible):
        dechiffrer(donnees, [CLE_1], UTILISATEUR)


def test_chiffrer__aucune_cle__refus() -> None:
    with pytest.raises(CleInvalide):
        chiffrer(b"secret", [], UTILISATEUR)


def test_pseudonymiser__hmac_sha256_email_minuscules_32_octets() -> None:
    cle = b"\x33" * 32
    attendu = hmac.new(cle, b"associe@x.fr", hashlib.sha256).digest()
    assert pseudonymiser("  Associe@X.fr ", cle) == attendu
    assert pseudonymiser("associe@x.fr", cle) == attendu
    assert len(attendu) == 32
    assert pseudonymiser("associe@x.fr", b"\x44" * 32) != attendu
