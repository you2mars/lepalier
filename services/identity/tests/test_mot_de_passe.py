from __future__ import annotations

import string
from itertools import pairwise
from pathlib import Path

import pytest
from argon2 import PasswordHasher
from argon2.low_level import Type
from hypothesis import assume, given
from hypothesis import strategies as st

from app.engines.mot_de_passe import (
    HACHAGE_FACTICE,
    Motif,
    hacher,
    lire_courants,
    motif_refus,
    rehachage_necessaire,
    verifier,
    verifier_factice,
)

DONNEES = Path(__file__).resolve().parents[1] / "app" / "engines" / "donnees" / "mots_de_passe_courants.txt"
COURANTS = lire_courants(DONNEES.read_text())
EMAIL = "jean.durand@exemple.fr"


def _motif(mot_de_passe: str, email: str = EMAIL) -> Motif | None:
    return motif_refus(mot_de_passe, email, COURANTS)


# --- liste locale des mots de passe courants -------------------------------------------------------


def test_liste_courants__en_tete_source_et_licence_mit() -> None:
    entete = DONNEES.read_text().split("\n---\n", 1)[0]
    assert "SecLists" in entete
    assert "MIT License" in entete


def test_liste_courants__aucune_entree_de_moins_de_12_caracteres() -> None:
    assert len(COURANTS) > 40_000
    assert min(len(m) for m in COURANTS) >= 12


def test_liste_courants__entree_commencant_par_diese_conservee() -> None:
    assert "###int_made###" in COURANTS


def test_lire_courants__normalise_nfkc_et_minuscules() -> None:
    assert lire_courants("en-tête\n---\nMotDePasse12345\n\n") == frozenset({"motdepasse12345"})


# --- motifs de refus, dans l'ordre ------------------------------------------------------------------


@pytest.mark.parametrize("mot_de_passe", ["", "court", "onze caract"])
def test_robustesse__moins_de_12_caracteres__trop_court(mot_de_passe: str) -> None:
    assert _motif(mot_de_passe) is Motif.TROP_COURT


def test_robustesse__plus_de_128_caracteres__trop_long() -> None:
    assert _motif("une phrase " * 12) is Motif.TROP_LONG
    assert _motif("abcdefg " * 16) is None


def test_robustesse__longueur_comptee_en_caracteres_apres_nfkc() -> None:
    assert _motif("éléphant été") is None
    assert _motif("éléphant ét") is Motif.TROP_COURT


@pytest.mark.parametrize(
    "mot_de_passe",
    [
        "aaaaaaaaaaaa",
        "abababababab",
        "abcdabcdabcd",
        "AAAA aaaa AAAA",
        "123456789012",
        "210987654321",
        "abcdefghijklm",
        "azertyuiopqs",
        "qwertyuiopasdf",
        "nbvcxwmlkjhg",
    ],
)
def test_robustesse__repetition_ou_suite__refus(mot_de_passe: str) -> None:
    assert _motif(mot_de_passe) is Motif.SUITE_OU_REPETITION


def test_robustesse__suite_noyee_dans_une_phrase__acceptee() -> None:
    assert _motif("mon chat 1234 dort") is None


@pytest.mark.parametrize("mot_de_passe", ["lepalier2026!", "mon palier est beau", "Le Palier Le Palier"])
def test_robustesse__nom_de_l_application__refus(mot_de_passe: str) -> None:
    assert _motif(mot_de_passe) is Motif.NOM_APPLICATION


@pytest.mark.parametrize(
    "mot_de_passe", ["jean.durand@exemple.fr!", "JEAN.DURAND est là", "x jean.durand y z"]
)
def test_robustesse__adresse_ou_partie_locale__refus(mot_de_passe: str) -> None:
    assert _motif(mot_de_passe) is Motif.ADRESSE_EMAIL


def test_robustesse__partie_locale_de_moins_de_4_caracteres__ignoree() -> None:
    assert _motif("jo et ses amis partent", email="jo@exemple.fr") is None
    assert _motif("ecrire a jo@exemple.fr", email="jo@exemple.fr") is Motif.ADRESSE_EMAIL


def test_robustesse__mot_de_passe_courant__refus_insensible_a_la_casse_et_aux_espaces() -> None:
    courant = next(iter(sorted(COURANTS)))
    assert _motif(courant) is Motif.COURANT
    assert motif_refus("Mot De Passe Secret", EMAIL, frozenset({"motdepassesecret"})) is Motif.COURANT


def test_robustesse__premier_motif_rencontre__ordre_fixe() -> None:
    assert motif_refus("aaaaaaaaaaaa", EMAIL, frozenset({"aaaaaaaaaaaa"})) is Motif.SUITE_OU_REPETITION
    assert _motif("lepalier jean.durand") is Motif.NOM_APPLICATION


PHRASE = st.lists(
    st.text(alphabet=string.ascii_lowercase + "éèàç", min_size=4, max_size=9), min_size=3, max_size=8
).map(" ".join)


@given(PHRASE)
def test_robustesse__propriete__phrase_ordinaire_acceptee(phrase: str) -> None:
    compacte = phrase.replace(" ", "")
    assume(12 <= len(phrase) <= 128)
    assume(len(set(compacte)) > 4)
    assume(any(abs(ord(b) - ord(a)) != 1 for a, b in pairwise(compacte)))
    assume("palier" not in compacte and "jean" not in compacte)
    assert motif_refus(phrase, EMAIL, frozenset()) is None


# --- hachage Argon2id (TEC-SEC-01) -----------------------------------------------------------------


def test_hachage__argon2id_m19456_t2_p1() -> None:
    hache = hacher("correct cheval agrafe")
    assert hache.startswith("$argon2id$v=19$m=19456,t=2,p=1$")


def test_hachage__deux_hachages_differents_verification_ok() -> None:
    a, b = hacher("correct cheval agrafe"), hacher("correct cheval agrafe")
    assert a != b
    assert verifier(a, "correct cheval agrafe") and verifier(b, "correct cheval agrafe")


def test_mot_de_passe_avec_espaces__accepte_et_verifie_tel_quel() -> None:
    phrase = "mon chat dort sur le toit"
    assert _motif(phrase) is None
    hache = hacher(phrase)
    assert verifier(hache, phrase)
    assert not verifier(hache, "monchatdortsurletoit")
    assert not verifier(hache, "mon chat dort sur le toit ")


def test_hachage__nfkc_pour_qu_une_meme_saisie_corresponde() -> None:
    assert verifier(hacher("ﬁlet de pêche du matin"), "filet de pêche du matin")


@pytest.mark.parametrize("hache", ["", "pas un hachage", "$argon2id$v=19$m=19456,t=2,p=1$abc$def"])
def test_verification__hachage_corrompu__false_sans_exception(hache: str) -> None:
    assert verifier(hache, "correct cheval agrafe") is False


def test_verification__mauvais_mot_de_passe__false() -> None:
    assert verifier(hacher("correct cheval agrafe"), "correct cheval agraf") is False


def test_rehachage_necessaire__parametres_anciens__true() -> None:
    ancien = PasswordHasher(time_cost=1, memory_cost=8192, parallelism=1, type=Type.ID).hash("x" * 12)
    assert rehachage_necessaire(ancien) is True
    assert rehachage_necessaire(hacher("correct cheval agrafe")) is False
    assert rehachage_necessaire("illisible") is True


def test_hachage_factice__memes_parametres_et_toujours_faux() -> None:
    assert HACHAGE_FACTICE.startswith("$argon2id$v=19$m=19456,t=2,p=1$")
    assert verifier_factice("correct cheval agrafe") is False
