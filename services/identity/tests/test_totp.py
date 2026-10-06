from __future__ import annotations

import base64
from urllib.parse import parse_qs, quote, unquote, urlsplit

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.engines.totp import (
    EMETTEUR,
    code,
    nouveau_secret,
    pas_a,
    uri_provisionnement,
    verifier,
)

# RFC 6238, annexe B (SHA-1) : secret ASCII « 12345678901234567890 », codes à 8 chiffres ramenés à 6
SECRET_RFC = b"12345678901234567890"
VECTEURS_RFC = [
    (59, "287082"),
    (1111111109, "081804"),
    (1111111111, "050471"),
    (1234567890, "005924"),
    (2000000000, "279037"),
    (20000000000, "353130"),
]
INSTANT = 1_800_000_015.0
SECRET = bytes(range(20))


@pytest.mark.parametrize(("instant", "attendu"), VECTEURS_RFC)
def test_code__vecteurs_rfc_6238(instant: int, attendu: str) -> None:
    assert code(SECRET_RFC, pas_a(instant)) == attendu


def test_pas_a__tranches_de_30_secondes() -> None:
    assert pas_a(0) == 0
    assert pas_a(29.999) == 0
    assert pas_a(30) == 1


@pytest.mark.parametrize("decalage", [-30, 0, 30])
def test_verifier__fenetre_plus_ou_moins_un_pas__accepte_et_renvoie_le_pas(decalage: int) -> None:
    pas = pas_a(INSTANT + decalage)
    assert verifier(SECRET, code(SECRET, pas), INSTANT, dernier_pas=None) == pas


@pytest.mark.parametrize("decalage", [-60, 60, -3600])
def test_verifier__hors_fenetre__refuse(decalage: int) -> None:
    assert verifier(SECRET, code(SECRET, pas_a(INSTANT + decalage)), INSTANT, dernier_pas=None) is None


def test_verifier__pas_deja_utilise__refuse() -> None:
    courant = pas_a(INSTANT)
    assert verifier(SECRET, code(SECRET, courant), INSTANT, dernier_pas=courant) is None


def test_verifier__pas_anterieur_au_dernier_utilise__refuse() -> None:
    courant = pas_a(INSTANT)
    assert verifier(SECRET, code(SECRET, courant - 1), INSTANT, dernier_pas=courant) is None


def test_verifier__pas_suivant_le_dernier_utilise__accepte() -> None:
    courant = pas_a(INSTANT)
    assert verifier(SECRET, code(SECRET, courant + 1), INSTANT, dernier_pas=courant) == courant + 1


@given(st.integers(min_value=-5, max_value=5))
def test_verifier__propriete__jamais_un_pas_inferieur_ou_egal_au_dernier(ecart: int) -> None:
    courant = pas_a(INSTANT)
    dernier = courant + ecart
    for pas in (courant - 1, courant, courant + 1):
        accepte = verifier(SECRET, code(SECRET, pas), INSTANT, dernier_pas=dernier)
        assert accepte is None or accepte > dernier


@pytest.mark.parametrize("saisie", ["12345", "abcdef", "", "1234567", "12345a", "١٢٣٤٥٦"])
def test_verifier__code_mal_forme__refuse_sans_exception(saisie: str) -> None:
    assert verifier(SECRET, saisie, INSTANT, dernier_pas=None) is None


@pytest.mark.parametrize("forme", ["{} {}", "{}-{}", " {}{} ", "{}  {}"])
def test_verifier__espaces_et_tiret_de_saisie_toleres(forme: str) -> None:
    attendu = code(SECRET, pas_a(INSTANT))
    saisie = forme.format(attendu[:3], attendu[3:])
    assert verifier(SECRET, saisie, INSTANT, dernier_pas=None) == pas_a(INSTANT)


def test_nouveau_secret__20_octets_aleatoires() -> None:
    secrets_ = {nouveau_secret() for _ in range(1000)}
    assert len(secrets_) == 1000
    assert all(len(s) == 20 for s in secrets_)


def _decouper(uri: str) -> tuple[str, dict[str, list[str]]]:
    parties = urlsplit(uri)
    assert (parties.scheme, parties.netloc) == ("otpauth", "totp")
    return parties.path.removeprefix("/"), parse_qs(parties.query)


def test_uri_provisionnement__emetteur_lepalier_secret_base32_sans_bourrage() -> None:
    libelle, parametres = _decouper(uri_provisionnement(SECRET, "Mme Durand"))
    assert EMETTEUR == "LePalier"
    assert libelle == "LePalier:Mme%20Durand"
    assert parametres["issuer"] == ["LePalier"]
    assert parametres["secret"] == [base64.b32encode(SECRET).decode().rstrip("=")]
    assert (parametres["algorithm"], parametres["digits"], parametres["period"]) == (["SHA1"], ["6"], ["30"])


@pytest.mark.parametrize("nom", ["Jean-Pierre O'Neil : 3e étage", "Élodie:Gérante", "D'Aragon Ç"])
def test_uri_provisionnement__nom_avec_deux_points_accents_apostrophe__libelle_encode(nom: str) -> None:
    libelle, _ = _decouper(uri_provisionnement(SECRET, nom))
    emetteur, separateur, compte = libelle.partition(":")
    assert (emetteur, separateur) == ("LePalier", ":")
    assert ":" not in compte
    assert "'" not in compte and " " not in compte
    assert compte == quote(nom, safe="")
    assert unquote(compte) == nom
