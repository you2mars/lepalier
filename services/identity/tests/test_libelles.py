from __future__ import annotations

import pytest

from app.engines.mot_de_passe import Motif
from app.libelles import libelles, message_mot_de_passe

MESSAGES = {
    Motif.TROP_COURT: (
        "Choisissez au moins 12 caractères. Une phrase de plusieurs mots est plus facile à retenir."
    ),
    Motif.TROP_LONG: (
        "Ce mot de passe est trop long : 128 caractères au plus. Une phrase de quelques mots suffit."
    ),
    Motif.SUITE_OU_REPETITION: (
        "Ce mot de passe est trop facile à deviner : il répète ou enchaîne les mêmes caractères "
        "(comme « aaaa » ou « 1234 »). Choisissez plutôt une phrase de plusieurs mots."
    ),
    Motif.NOM_APPLICATION: (
        "Ce mot de passe est trop facile à deviner : il contient le nom de l'application. "
        "Choisissez une phrase sans « LePalier » ni « palier »."
    ),
    Motif.ADRESSE_EMAIL: (
        "Ce mot de passe est trop facile à deviner : il contient votre adresse e-mail "
        "ou une partie de celle-ci. "
        "Choisissez une phrase sans rapport avec votre adresse."
    ),
    Motif.COURANT: (
        "Ce mot de passe est trop facile à deviner : il fait partie des plus utilisés. "
        "Choisissez une phrase de plusieurs mots qui vous est propre."
    ),
}


@pytest.mark.parametrize("motif", list(Motif))
def test_message_mot_de_passe__mot_pour_mot(motif: Motif) -> None:
    assert message_mot_de_passe(motif) == MESSAGES[motif]


def test_libelles_mot_de_passe__un_message_par_motif_ni_plus_ni_moins() -> None:
    assert set(libelles()["mot_de_passe"]) == {m.value for m in Motif}


@pytest.mark.parametrize("motif", list(Motif))
def test_message_mot_de_passe__charte_ux_sans_exclamation_ni_jargon(motif: Motif) -> None:
    message = message_mot_de_passe(motif)
    assert "!" not in message
    assert message.endswith(".")
    for mot in ("erreur", "invalide", "code", "regex"):
        assert mot not in message.lower()
