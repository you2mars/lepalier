from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import BaseModel, ValidationError

from commun.decimales import CENTIME, Montant, arrondir, en_chaine, repartir_plus_fort_reste, vers_decimal


@pytest.mark.parametrize(
    ("valeur", "attendu"),
    [("2.675", "2.68"), ("0.005", "0.01"), ("1.004", "1.00"), ("-1.005", "-1.01"), ("650", "650.00")],
)
def test_arrondir__demi_superieur_au_centime(valeur: str, attendu: str) -> None:
    assert arrondir(Decimal(valeur)) == Decimal(attendu)


def test_arrondir__autre_pas() -> None:
    assert arrondir(Decimal("12.5"), Decimal("1")) == Decimal("13")


@pytest.mark.parametrize(("valeur", "attendu"), [("650.00", "650.00"), (650, "650"), (Decimal("1.2"), "1.2")])
def test_vers_decimal__accepte_chaine_entier_decimal(valeur: object, attendu: str) -> None:
    assert vers_decimal(valeur) == Decimal(attendu)


@pytest.mark.parametrize("valeur", [1.5, True, "1,5", "abc", "NaN", "Infinity", "", None])
def test_vers_decimal__refuse_flottants_et_valeurs_non_decimales(valeur: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        vers_decimal(valeur)


@pytest.mark.parametrize(
    ("valeur", "attendu"),
    [
        (Decimal("650"), "650.00"),
        (Decimal("-3.5"), "-3.50"),
        (Decimal("1E+3"), "1000.00"),
        (Decimal("0.10"), "0.10"),
    ],
)
def test_en_chaine__deux_decimales(valeur: Decimal, attendu: str) -> None:
    assert en_chaine(valeur) == attendu


def test_en_chaine__refuse_un_montant_non_arrondi() -> None:
    with pytest.raises(ValueError, match="arrondi"):
        en_chaine(Decimal("1.234"))


MONTANTS = st.integers(min_value=0, max_value=10**11).map(lambda c: Decimal(c) / 100)
POIDS = st.lists(
    st.decimals(min_value=0, max_value=10**6, places=3, allow_nan=False, allow_infinity=False),
    min_size=1,
    max_size=30,
).filter(lambda p: sum(p) > 0)


@given(MONTANTS, POIDS)
def test_repartir__somme_exacte_parts_au_centime_ecart_inferieur_a_un_centime(
    total: Decimal, poids: list[Decimal]
) -> None:
    parts = repartir_plus_fort_reste(total, poids)
    assert len(parts) == len(poids)
    assert sum(parts) == total
    somme_poids = sum(poids)
    for part, poids_lot in zip(parts, poids, strict=True):
        assert part >= 0
        assert part == part.quantize(CENTIME)
        assert abs(part - total * poids_lot / somme_poids) < CENTIME
        if poids_lot == 0:
            assert part == 0
    assert repartir_plus_fort_reste(total, poids) == parts


def test_repartir__egalite_des_restes_departagee_par_l_ordre() -> None:
    parts = repartir_plus_fort_reste(Decimal("100.00"), [Decimal(1), Decimal(1), Decimal(1)])
    assert parts == [Decimal("33.34"), Decimal("33.33"), Decimal("33.33")]


def test_repartir__poids_nul_ne_recoit_rien() -> None:
    assert repartir_plus_fort_reste(Decimal("10.00"), [Decimal(0), Decimal(3)]) == [
        Decimal("0.00"),
        Decimal("10.00"),
    ]


@pytest.mark.parametrize(
    ("total", "poids"),
    [
        (Decimal("1.005"), [Decimal(1)]),
        (Decimal("-1.00"), [Decimal(1)]),
        (Decimal("1.00"), []),
        (Decimal("1.00"), [Decimal(0), Decimal(0)]),
        (Decimal("1.00"), [Decimal(1), Decimal(-1)]),
    ],
)
def test_repartir__refuse_les_entrees_incoherentes(total: Decimal, poids: list[Decimal]) -> None:
    with pytest.raises(ValueError):
        repartir_plus_fort_reste(total, poids)


class _Saisie(BaseModel):
    montant: Montant


@pytest.mark.parametrize(("valeur", "attendu"), [("650.5", "650.50"), (650, "650.00"), ("0", "0.00")])
def test_montant__normalise_et_serialise_en_chaine(valeur: object, attendu: str) -> None:
    saisie = _Saisie.model_validate({"montant": valeur})
    assert saisie.montant == Decimal(attendu)
    assert saisie.model_dump(mode="json") == {"montant": attendu}


@pytest.mark.parametrize("valeur", [650.5, "1.234", "abc", True])
def test_montant__refuse_flottant_et_plus_de_deux_decimales(valeur: object) -> None:
    with pytest.raises(ValidationError):
        _Saisie.model_validate({"montant": valeur})
