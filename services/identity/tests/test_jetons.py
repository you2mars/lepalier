from __future__ import annotations

import base64
import hashlib

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.engines.jetons import empreinte, jeton_correspond, nouveau_jeton


def test_nouveau_jeton__32_octets_aleatoires_encodage_url() -> None:
    jeton = nouveau_jeton()
    assert len(base64.urlsafe_b64decode(jeton + "=")) == 32
    assert "=" not in jeton and "+" not in jeton and "/" not in jeton
    assert len({nouveau_jeton() for _ in range(10_000)}) == 10_000


def test_empreinte__sha256_32_octets_deterministe() -> None:
    jeton = nouveau_jeton()
    assert empreinte(jeton) == hashlib.sha256(jeton.encode()).digest()
    assert len(empreinte(jeton)) == 32
    assert empreinte(jeton) == empreinte(jeton)


def test_jeton_correspond__jeton_d_origine__vrai() -> None:
    jeton = nouveau_jeton()
    assert jeton_correspond(jeton, empreinte(jeton)) is True


@given(st.integers(min_value=0, max_value=42), st.sampled_from("ABCDEFabcdef0123456789-_"))
def test_jeton_correspond__un_caractere_altere__faux(position: int, caractere: str) -> None:
    jeton = nouveau_jeton()
    altere = jeton[:position] + caractere + jeton[position + 1 :]
    assert jeton_correspond(altere, empreinte(jeton)) is (altere == jeton)


@pytest.mark.parametrize("jeton", ["", "court", "x" * 44, "!" * 43, "é" * 43, "a b" + "c" * 40])
def test_jeton_correspond__jeton_illisible__faux_sans_exception(jeton: str) -> None:
    assert jeton_correspond(jeton, empreinte(nouveau_jeton())) is False


def test_jeton_correspond__empreinte_de_mauvaise_taille__faux() -> None:
    jeton = nouveau_jeton()
    assert jeton_correspond(jeton, empreinte(jeton)[:16]) is False
