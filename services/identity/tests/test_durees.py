from __future__ import annotations

from datetime import UTC, datetime, timedelta

from hypothesis import given
from hypothesis import strategies as st

from app.engines.durees import (
    ESSAIS_TOTP_MAX,
    expiration_appareil,
    expiration_invitation,
    expiration_pre_session,
    expiration_reinitialisation,
    expiration_session,
    pre_session_epuisee,
    session_valide,
)

T0 = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)
SECONDE = timedelta(seconds=1)


def test_pre_session__expire_5_min_apres_creation() -> None:
    assert expiration_pre_session(T0) == T0 + timedelta(minutes=5)


def test_pre_session__cinq_codes_faux__epuisee() -> None:
    assert ESSAIS_TOTP_MAX == 5
    assert not pre_session_epuisee(4)
    assert pre_session_epuisee(5)


@given(st.integers(min_value=0, max_value=40 * 24 * 3600))
def test_session__propriete__expiration_min_12h_glissantes_30_jours_max(depuis_creation: int) -> None:
    derniere = T0 + timedelta(seconds=depuis_creation)
    expiration = expiration_session(T0, derniere)
    assert expiration <= T0 + timedelta(days=30)
    assert expiration == min(derniere + timedelta(hours=12), T0 + timedelta(days=30))


def test_session__active_depuis_30_jours__expiree_meme_utilisee_a_l_instant() -> None:
    fin = T0 + timedelta(days=30)
    assert session_valide(T0, fin - SECONDE, fin - SECONDE)
    assert not session_valide(T0, fin, fin)


def test_session__inactive_12_h__expiree() -> None:
    assert session_valide(T0, T0, T0 + timedelta(hours=12) - SECONDE)
    assert not session_valide(T0, T0, T0 + timedelta(hours=12))


def test_liens__invitation_7_jours_reinitialisation_1_heure_appareil_1_an() -> None:
    assert expiration_invitation(T0) == T0 + timedelta(days=7)
    assert expiration_reinitialisation(T0) == T0 + timedelta(hours=1)
    assert expiration_appareil(T0) == T0 + timedelta(days=365)
