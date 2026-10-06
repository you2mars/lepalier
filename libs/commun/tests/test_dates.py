"""Dates en toutes lettres et heures à l'heure de Paris (UX-6, UX-13), pour les e-mails, PDF et commandes."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from hypothesis import given
from hypothesis import strategies as st

from commun.dates import PARIS, date_en_toutes_lettres, date_heure_paris, heure_paris


@pytest.mark.parametrize(
    ("jour", "attendu"),
    [
        (date(2026, 10, 1), "jeudi 1er octobre 2026"),
        (date(2026, 10, 5), "lundi 5 octobre 2026"),
        (date(2026, 2, 28), "samedi 28 février 2026"),
        (date(2026, 8, 15), "samedi 15 août 2026"),
        (date(2026, 12, 31), "jeudi 31 décembre 2026"),
    ],
)
def test_date_en_toutes_lettres__jour_mois_annee(jour: date, attendu: str) -> None:
    assert date_en_toutes_lettres(jour) == attendu


@pytest.mark.parametrize(
    ("instant", "attendu"),
    [
        (datetime(2026, 7, 14, 23, 30, tzinfo=UTC), ("mercredi 15 juillet 2026", "1 h 30")),
        (datetime(2026, 1, 10, 23, 30, tzinfo=UTC), ("dimanche 11 janvier 2026", "0 h 30")),
        (datetime(2026, 10, 4, 12, 5, tzinfo=UTC), ("dimanche 4 octobre 2026", "14 h 05")),
        (datetime(2026, 10, 1, 8, 0, tzinfo=UTC), ("jeudi 1er octobre 2026", "10 h 00")),
        # passage à l'heure d'hiver le 25 octobre 2026 à 3 h (heure d'été)
        (datetime(2026, 10, 25, 0, 59, tzinfo=UTC), ("dimanche 25 octobre 2026", "2 h 59")),
        (datetime(2026, 10, 25, 1, 0, tzinfo=UTC), ("dimanche 25 octobre 2026", "2 h 00")),
    ],
)
def test_date_heure_paris__toutes_lettres_heure_de_paris(instant: datetime, attendu: tuple[str, str]) -> None:
    assert date_heure_paris(instant) == attendu
    assert heure_paris(instant) == attendu[1]


def test_date_heure_paris__instant_sans_fuseau__refuse() -> None:
    with pytest.raises(ValueError, match="fuseau"):
        date_heure_paris(datetime(2026, 10, 4, 12, 5))


@given(st.datetimes(min_value=datetime(2000, 1, 1), max_value=datetime(2100, 1, 1), timezones=st.just(UTC)))
def test_date_heure_paris__propriete__date_du_jour_civil_a_paris(instant: datetime) -> None:
    local = instant.astimezone(PARIS)
    date_lettres, heure = date_heure_paris(instant)
    assert date_lettres == date_en_toutes_lettres(local.date())
    assert heure == f"{local.hour} h {local.minute:02d}"
    assert date_heure_paris(instant + timedelta(0)) == (date_lettres, heure)
