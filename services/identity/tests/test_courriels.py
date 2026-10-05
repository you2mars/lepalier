"""E-mails de compte (ADR 0006, UX-13, UX-16) : textes validés le 4 octobre 2026, heure de Paris."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.courriels.envoi import ExpediteurSmtp
from app.courriels.textes import (
    Courriel,
    alerte_compte_suspendu,
    alerte_echecs,
    date_heure_paris,
    invitation,
    mot_de_passe_change,
    nouvel_appareil,
    reinitialisation,
)
from commun.jobs import ErreurReseau

ETE = datetime(2026, 7, 14, 23, 30, tzinfo=UTC)


@pytest.mark.parametrize(
    ("instant", "attendu"),
    [
        (ETE, ("mercredi 15 juillet 2026", "1 h 30")),
        (datetime(2026, 1, 10, 23, 30, tzinfo=UTC), ("dimanche 11 janvier 2026", "0 h 30")),
        (datetime(2026, 10, 4, 12, 5, tzinfo=UTC), ("dimanche 4 octobre 2026", "14 h 05")),
        (datetime(2026, 10, 1, 8, 0, tzinfo=UTC), ("jeudi 1er octobre 2026", "10 h 00")),
    ],
)
def test_date_heure_paris__toutes_lettres_heure_de_paris(instant: datetime, attendu: tuple[str, str]) -> None:
    assert date_heure_paris(instant) == attendu


def test_courriel_nouvel_appareil__mot_pour_mot() -> None:
    assert nouvel_appareil("Mme Durand", ETE) == Courriel(
        objet="[LePalier] Nouvelle connexion à votre compte",
        corps=(
            "Bonjour Mme Durand,\n"
            "Votre compte LePalier a été utilisé le mercredi 15 juillet 2026 à 1 h 30 depuis un appareil "
            "ou un navigateur utilisé pour la première fois.\n"
            "Si c'est vous, il n'y a rien à faire. Sinon, contactez tout de suite le gérant de la SCI."
        ),
    )


def test_courriel_alerte_echecs__mot_pour_mot() -> None:
    assert alerte_echecs("M. Martin", "Mme Durand", ETE) == Courriel(
        objet="[LePalier] Nombreux essais de connexion sur un compte",
        corps=(
            "Bonjour M. Martin,\n"
            "Au moins 20 essais de connexion ont échoué en une heure sur le compte de Mme Durand, "
            "le mercredi 15 juillet 2026.\n"
            "Ces essais viennent peut-être d'une autre personne. Vérifiez avec Mme Durand et, si besoin, "
            "suspendez son accès dans Administration, Utilisateurs."
        ),
    )


def test_courriel_alerte_compte_suspendu__mot_pour_mot() -> None:
    assert alerte_compte_suspendu("M. Martin", "Mme Durand", ETE) == Courriel(
        objet="[LePalier] Connexion d'un compte suspendu",
        corps=(
            "Bonjour M. Martin,\n"
            "Mme Durand a essayé de se connecter le mercredi 15 juillet 2026 à 1 h 30, avec le bon mot "
            "de passe et le bon code, alors que son accès est suspendu.\n"
            "Si cet accès doit être rétabli, réactivez-le dans Administration, Utilisateurs."
        ),
    )


def test_courriel_invitation__mot_pour_mot() -> None:
    lien = "https://lepalier.essai/activation#" + "A" * 43
    assert invitation("Mme Durand", "M. Martin", lien) == Courriel(
        objet="[LePalier] Votre invitation",
        corps=(
            "Bonjour Mme Durand,\n"
            "M. Martin vous invite à utiliser LePalier, l'application de gestion de l'immeuble de la SCI.\n"
            "Pour créer votre accès, ouvrez ce lien et suivez les étapes à l'écran. Prévoyez 5 minutes et "
            f"gardez votre téléphone à portée de main : {lien}\n"
            "Ce lien est valable 7 jours. Si vous n'attendiez pas cette invitation, ignorez ce message."
        ),
    )


def test_courriel_reinitialisation__mot_pour_mot() -> None:
    lien = "https://lepalier.essai/reinitialisation#" + "A" * 43
    assert reinitialisation("Mme Durand", lien) == Courriel(
        objet="[LePalier] Choisir un nouveau mot de passe",
        corps=(
            "Bonjour Mme Durand,\n"
            "Vous avez demandé à changer votre mot de passe LePalier. "
            f"Ouvrez ce lien pour en choisir un nouveau : {lien}\n"
            "Vous aurez besoin de votre téléphone pour saisir votre code.\n"
            "Ce lien est valable 1 heure. Si vous n'avez rien demandé, ignorez ce message : "
            "votre mot de passe ne change pas."
        ),
    )


def test_courriel_mot_de_passe_change__mot_pour_mot() -> None:
    assert mot_de_passe_change("Mme Durand", ETE) == Courriel(
        objet="[LePalier] Votre mot de passe a été changé",
        corps=(
            "Bonjour Mme Durand,\n"
            "Le mot de passe de votre compte LePalier a été changé le mercredi 15 juillet 2026 à 1 h 30. "
            "Toutes vos connexions ont été fermées.\n"
            "Si ce n'est pas vous, contactez tout de suite le gérant de la SCI."
        ),
    )


@pytest.mark.parametrize(
    "courriel",
    [
        reinitialisation("Mme Durand", "https://lepalier.essai/reinitialisation#jeton"),
        mot_de_passe_change("Mme Durand", ETE),
        invitation("Mme Durand", "M. Martin", "https://lepalier.essai/activation#jeton"),
        nouvel_appareil("Mme Durand", ETE),
        alerte_echecs("M. Martin", "Mme Durand", ETE),
        alerte_compte_suspendu("M. Martin", "Mme Durand", ETE),
    ],
)
def test_courriels__charte_objet_lepalier_5_lignes_au_plus_sans_exclamation(courriel: Courriel) -> None:
    assert courriel.objet.startswith("[LePalier] ")
    assert len(courriel.corps.splitlines()) <= 5
    assert "!" not in courriel.objet + courriel.corps


def test_expediteur_smtp__serveur_injoignable__erreur_reseau() -> None:
    expediteur = ExpediteurSmtp(hote="127.0.0.1", port=1, adresse="lepalier@localhost", delai_secondes=1)
    with pytest.raises(ErreurReseau):
        expediteur.envoyer("associe@essai.local", nouvel_appareil("Mme Durand", ETE))


@pytest.mark.integration
def test_expediteur_smtp__mailpit__courriel_recu_tel_quel() -> None:
    import httpx
    from testcontainers.core.container import DockerContainer
    from testcontainers.core.wait_strategies import LogMessageWaitStrategy

    conteneur = (
        DockerContainer("axllent/mailpit")
        .with_exposed_ports(1025, 8025)
        .waiting_for(LogMessageWaitStrategy("accessible via"))
    )
    with conteneur:
        hote = conteneur.get_container_host_ip()
        courriel = nouvel_appareil("Mme Durand", ETE)
        ExpediteurSmtp(hote, int(conteneur.get_exposed_port(1025)), "LePalier <lepalier@localhost>").envoyer(
            "associe@essai.local", courriel
        )
        api = f"http://{hote}:{conteneur.get_exposed_port(8025)}/api/v1"
        (resume,) = httpx.get(f"{api}/messages").json()["messages"]
        message = httpx.get(f"{api}/message/{resume['ID']}").json()
    assert [d["Address"] for d in message["To"]] == ["associe@essai.local"]
    assert message["From"]["Address"] == "lepalier@localhost"
    assert message["Subject"] == courriel.objet
    # SMTP transporte les fins de ligne en CRLF
    assert message["Text"].replace("\r\n", "\n").strip() == courriel.corps
