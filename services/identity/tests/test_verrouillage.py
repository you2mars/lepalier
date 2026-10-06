from __future__ import annotations

from datetime import UTC, datetime, timedelta

from hypothesis import given
from hypothesis import strategies as st

from app.engines.verrouillage import (
    Tentative,
    alerte_compte,
    reinitialisation_autorisee,
    verrou_couple,
)

T0 = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)


def _min(minutes: float) -> datetime:
    return T0 + timedelta(minutes=minutes)


def _echecs(*minutes: float) -> list[Tentative]:
    return [Tentative(_min(m), reussie=False) for m in minutes]


def test_couple__cinq_echecs_en_15_min__verrouille_jusqu_au_5e_echec_plus_15_min() -> None:
    tentatives = _echecs(0, 1, 2, 3, 4)
    assert verrou_couple(tentatives, _min(4)) == _min(19)
    assert verrou_couple(tentatives, _min(18.99)) == _min(19)


def test_couple__a_15_min_plus_1_s_apres_le_5e_echec__deverrouille() -> None:
    assert verrou_couple(_echecs(0, 1, 2, 3, 4), _min(19) + timedelta(seconds=1)) is None


def test_couple__quatre_echecs__pas_de_verrou() -> None:
    assert verrou_couple(_echecs(0, 1, 2, 3), _min(3)) is None


def test_couple__echecs_avant_la_derniere_reussite__non_comptes() -> None:
    tentatives = [*_echecs(0, 1, 2, 3), Tentative(_min(4), reussie=True), *_echecs(5, 6, 7, 8)]
    assert verrou_couple(tentatives, _min(8)) is None
    assert verrou_couple([*tentatives, *_echecs(9)], _min(9)) == _min(24)


def test_couple__echecs_de_plus_de_15_min__non_comptes() -> None:
    assert verrou_couple(_echecs(0, 20, 21, 22, 23), _min(23)) is None
    assert verrou_couple(_echecs(0, 5, 10, 14, 15.5), _min(15.5)) is None


def test_couple__ordre_des_tentatives_indifferent() -> None:
    assert verrou_couple(list(reversed(_echecs(0, 1, 2, 3, 4))), _min(5)) == _min(19)


def test_couple__echecs_pendant_le_verrou__ne_le_prolongent_pas() -> None:
    tentatives = _echecs(0, 1, 2, 3, 4, 10, 11, 12, 13, 14)
    assert verrou_couple(tentatives, _min(14)) == _min(19)


def test_couple__echecs_apres_la_fin_d_un_verrou__recomptes_depuis_zero() -> None:
    tentatives = _echecs(0, 1, 2, 3, 4, 20, 21, 22, 23)
    assert verrou_couple(tentatives, _min(23)) is None
    assert verrou_couple([*tentatives, *_echecs(24)], _min(24)) == _min(39)


@given(
    st.lists(
        st.tuples(st.integers(min_value=0, max_value=120), st.booleans()),
        max_size=30,
    )
)
def test_couple__propriete__jamais_verrouille_avec_moins_de_5_echecs(liste: list[tuple[int, bool]]) -> None:
    tentatives = [Tentative(_min(m), reussie=r) for m, r in liste]
    if sum(1 for t in tentatives if not t.reussie) < 5:
        assert verrou_couple(tentatives, _min(121)) is None


@given(
    st.lists(st.integers(min_value=0, max_value=200), max_size=30), st.integers(min_value=0, max_value=200)
)
def test_couple__propriete__verrou_jamais_au_dela_de_15_min_apres_un_echec(
    minutes: list[int], maintenant: int
) -> None:
    jusqu_au = verrou_couple(_echecs(*minutes), _min(maintenant))
    if jusqu_au is not None:
        assert jusqu_au > _min(maintenant)
        assert any(jusqu_au == _min(m) + timedelta(minutes=15) for m in minutes)


def _echecs_compte(n: int) -> list[datetime]:
    return [_min(i * 2) for i in range(n)]


def test_alerte__20_echecs_dans_l_heure_toutes_ip__alerte() -> None:
    assert alerte_compte(_echecs_compte(20), derniere_alerte=None, maintenant=_min(40), compte_connu=True)


def test_alerte__19_echecs__pas_d_alerte() -> None:
    assert not alerte_compte(_echecs_compte(19), derniere_alerte=None, maintenant=_min(40), compte_connu=True)


def test_alerte__echecs_de_plus_d_une_heure__non_comptes() -> None:
    assert not alerte_compte(
        _echecs_compte(20), derniere_alerte=None, maintenant=_min(100), compte_connu=True
    )


def test_alerte__derniere_alerte_il_y_a_moins_d_une_heure__pas_de_nouvelle_alerte() -> None:
    echecs = _echecs_compte(20)
    assert not alerte_compte(echecs, derniere_alerte=_min(10), maintenant=_min(40), compte_connu=True)
    assert alerte_compte(echecs, derniere_alerte=_min(-20), maintenant=_min(40), compte_connu=True)


def test_alerte__compte_inconnu__jamais_d_alerte() -> None:
    assert not alerte_compte(
        _echecs_compte(50), derniere_alerte=None, maintenant=_min(98), compte_connu=False
    )


def test_reinitialisation__trois_demandes_par_heure__quatrieme_refusee() -> None:
    demandes = [_min(0), _min(10), _min(20)]
    assert reinitialisation_autorisee(demandes[:2], _min(30))
    assert not reinitialisation_autorisee(demandes, _min(30))
    assert reinitialisation_autorisee(demandes, _min(60) + timedelta(seconds=1))
