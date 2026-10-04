from __future__ import annotations

import re

import pytest

from app.engines.codes_secours import ALPHABET, NOMBRE, generer, hacher, normaliser, trouver, verifier

FORME = re.compile(r"^[0-9A-HJKMNP-TV-Z]{4}-[0-9A-HJKMNP-TV-Z]{4}-[0-9A-HJKMNP-TV-Z]{4}$")


def test_generer__dix_codes_uniques_format_lisible() -> None:
    codes = generer()
    assert len(codes) == NOMBRE == 10
    assert len(set(codes)) == 10
    assert all(FORME.fullmatch(c) for c in codes)


def test_alphabet__crockford_sans_caractere_ambigu() -> None:
    assert len(ALPHABET) == 32
    assert not set("ILOU") & set(ALPHABET)


@pytest.mark.parametrize(
    ("saisie", "attendu"),
    [
        ("ABCD-EFGH-JKMN", "ABCDEFGHJKMN"),
        ("abcd efgh-jkmn", "ABCDEFGHJKMN"),
        (" abcd  efgh jkmn ", "ABCDEFGHJKMN"),
        ("o0il-OIL0-1234", "001101101234"),
    ],
)
def test_normaliser__casse_espaces_tirets_et_confusions_ignores(saisie: str, attendu: str) -> None:
    assert normaliser(saisie) == attendu


@pytest.mark.parametrize("saisie", ["", "ABCD-EFGH", "ABCD-EFGH-JKMN-P", "ABCD-EFGH-JKM!", "ABCD-EFGH-JKMÉ"])
def test_normaliser__longueur_ou_caractere_invalide__none(saisie: str) -> None:
    assert normaliser(saisie) is None


def test_hacher_et_verifier__argon2id() -> None:
    code = generer()[0]
    hache = hacher(code)
    assert hache.startswith("$argon2id$v=19$m=19456,t=2,p=1$")
    assert verifier(hache, code)
    assert verifier(hache, code.lower().replace("-", " "))
    assert not verifier(hache, generer()[0])


def test_trouver__code_valide__index_du_code_dans_la_liste() -> None:
    codes = generer()
    empreintes = [hacher(c) for c in codes[:4]]
    assert trouver(codes[2].lower(), empreintes) == 2


def test_trouver__code_inconnu_ou_illisible__none() -> None:
    codes = generer()
    empreintes = [hacher(c) for c in codes[:3]]
    assert trouver(codes[5], empreintes) is None
    assert trouver("pas un code", empreintes) is None
    assert trouver(codes[0], []) is None


def test_hacher__code_mal_forme__refus() -> None:
    with pytest.raises(ValueError, match="mal formé"):
        hacher("pas un code")


def test_verifier__saisie_illisible__false() -> None:
    assert verifier(hacher(generer()[0]), "pas un code") is False
