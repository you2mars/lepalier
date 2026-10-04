from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.engines.nom_affiche import LONGUEUR_MAX, nettoyer, nom_affiche_valide

CONTRATS = Path(__file__).resolve().parents[3] / "contracts" / "events" / "utilisateur"


@pytest.mark.parametrize(
    "nom",
    [
        "Mme Durand",
        "Jean-Pierre O'Neil",
        "Élodie Gérante",
        "x" * 60,
        "  Mme Durand  ",
        "Mme\xa0Durand",
        "Mme\u202fDurand",
        "Mme\u2070",
    ],
)
def test_nom_affiche__ordinaire__accepte(nom: str) -> None:
    assert nom_affiche_valide(nom)


@pytest.mark.parametrize(
    "nom",
    [
        "",
        "   ",
        "jean@exemple.fr",
        "x" * 61,
        "Mme\nDurand",
        "Mme\rDurand",
        "Mme\tDurand",
        "Mme\x00",
        "Mme\x7f",
        "\x1f",
        "Mme\x80Durand",
        "Mme\x85Durand",
        "Mme\x9fDurand",
        "Mme\u2028Durand",
        "Mme\u2029Durand",
        "\u202aMme Durand",
        "Mme \u202eDurand",
        "\u2066Mme Durand",
        "Mme Durand\u2069",
    ],
)
def test_nom_affiche__vide_arobase_trop_long_ou_caractere_de_controle__refuse(nom: str) -> None:
    assert not nom_affiche_valide(nom)


def test_nettoyer__espaces_autour_retires_seulement() -> None:
    assert nettoyer("  Mme  Durand  ") == "Mme  Durand"
    assert LONGUEUR_MAX == 60


# latin et contrôles, ponctuation générale (U+2000 à U+206F), puis tout Unicode
_ALPHABET = st.one_of(
    st.characters(max_codepoint=0x2FF),
    st.characters(min_codepoint=0x2000, max_codepoint=0x206F),
    st.characters(),
)


@pytest.mark.parametrize("fait", ["cree", "role_change", "suspendu", "reactive"])
@given(st.text(alphabet=_ALPHABET, max_size=70))
def test_nom_affiche__propriete__meme_decision_que_le_contrat(fait: str, nom: str) -> None:
    """La saisie et le contrat décident pareil (la base est testée dans test_migrations_identity)."""
    prop = json.loads((CONTRATS / f"{fait}.v1.json").read_text())["properties"]["nom_affiche"]
    nettoye = nettoyer(nom)
    selon_le_contrat = (
        prop["minLength"] <= len(nettoye) <= prop["maxLength"]
        and re.search(prop["pattern"], nettoye) is not None
    )
    assert nom_affiche_valide(nom) == selon_le_contrat
