"""E-mails de compte (ADR 0006, UX-13, UX-16) : textes validés le 4 octobre 2026, revus le 16 octobre 2026,
heure de Paris."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.courriels.envoi import ExpediteurSmtp
from app.courriels.textes import (
    Courriel,
    acces_reinitialise,
    alerte_compte_suspendu,
    alerte_echecs,
    invitation,
    mot_de_passe_change,
    nouvel_appareil,
    reinitialisation,
)
from commun.jobs import ErreurReseau

ETE = datetime(2026, 7, 14, 23, 30, tzinfo=UTC)
# fin d'un lien : jeudi 22 octobre 2026 à 14 h 05, heure de Paris (12 h 05 UTC, heure d'été)
FIN_DU_LIEN = datetime(2026, 10, 22, 12, 5, tzinfo=UTC)
# fin d'un lien après le passage à l'heure d'hiver (25 octobre 2026) : 23 h 30 UTC = 0 h 30 le lendemain
FIN_EN_HIVER = datetime(2026, 11, 30, 23, 30, tzinfo=UTC)


@pytest.mark.parametrize("role", ["associe", "operateur"])
def test_courriel_nouvel_appareil__associe_ou_operateur__prevenir_le_gerant__mot_pour_mot(role: str) -> None:
    assert nouvel_appareil("Mme Durand", ETE, role) == Courriel(
        objet="[LePalier] Nouvelle connexion à votre compte",
        corps=(
            "Bonjour Mme Durand,\n"
            "Votre compte LePalier a été utilisé le mercredi 15 juillet 2026 à 1 h 30 depuis un appareil "
            "ou un navigateur utilisé pour la première fois.\n"
            "Si c'est vous, il n'y a rien à faire. Sinon, changez tout de suite votre mot de passe avec "
            "« Mot de passe oublié » sur la page de connexion, puis prévenez le gérant."
        ),
    )


def test_courriel_nouvel_appareil__gerant__personne_a_prevenir__mot_pour_mot() -> None:
    assert nouvel_appareil("M. Martin", ETE, "gerant") == Courriel(
        objet="[LePalier] Nouvelle connexion à votre compte",
        corps=(
            "Bonjour M. Martin,\n"
            "Votre compte LePalier a été utilisé le mercredi 15 juillet 2026 à 1 h 30 depuis un appareil "
            "ou un navigateur utilisé pour la première fois.\n"
            "Si c'est vous, il n'y a rien à faire. Sinon, changez tout de suite votre mot de passe avec "
            "« Mot de passe oublié » sur la page de connexion."
        ),
    )


def test_courriel_alerte_echecs__mot_pour_mot() -> None:
    assert alerte_echecs("M. Martin", "Mme Durand", ETE - timedelta(minutes=47), ETE) == Courriel(
        objet="[LePalier] Nombreux essais de connexion sur un compte",
        corps=(
            "Bonjour M. Martin,\n"
            "Au moins 20 essais de connexion ont échoué en une heure sur le compte de Mme Durand, "
            "le mercredi 15 juillet 2026 entre 0 h 43 et 1 h 30.\n"
            "Ces essais viennent peut-être d'une autre personne. Vérifiez avec Mme Durand et, si besoin, "
            "suspendez son accès dans Administration, Utilisateurs."
        ),
    )


def test_courriel_alerte_echecs__heure_qui_passe_minuit__deux_dates__mot_pour_mot() -> None:
    # lundi 19 octobre 2026 à 23 h 40 et mardi 20 octobre à 0 h 20, heure de Paris (UTC+2)
    debut = datetime(2026, 10, 19, 21, 40, tzinfo=UTC)
    assert alerte_echecs("M. Martin", "Mme Durand", debut, debut + timedelta(minutes=40)) == Courriel(
        objet="[LePalier] Nombreux essais de connexion sur un compte",
        corps=(
            "Bonjour M. Martin,\n"
            "Au moins 20 essais de connexion ont échoué en une heure sur le compte de Mme Durand, "
            "entre le lundi 19 octobre 2026 à 23 h 40 et le mardi 20 octobre à 0 h 20.\n"
            "Ces essais viennent peut-être d'une autre personne. Vérifiez avec Mme Durand et, si besoin, "
            "suspendez son accès dans Administration, Utilisateurs."
        ),
    )


def test_courriel_alerte_echecs__heure_qui_passe_le_nouvel_an__annee_aux_deux_dates() -> None:
    debut = datetime(2026, 12, 31, 22, 50, tzinfo=UTC)  # 23 h 50 à Paris (UTC+1)
    courriel = alerte_echecs("M. Martin", "Mme Durand", debut, debut + timedelta(minutes=30))
    assert (
        "entre le jeudi 31 décembre 2026 à 23 h 50 et le vendredi 1er janvier 2027 à 0 h 20.\n"
        in courriel.corps
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
    assert invitation("Mme Durand", "M. Martin", "associe", lien, FIN_DU_LIEN) == Courriel(
        objet="[LePalier] Votre invitation",
        corps=(
            "Bonjour Mme Durand,\n"
            "M. Martin vous invite à utiliser LePalier, l'application de gestion de l'immeuble de la SCI, "
            "avec le rôle Associé.\n"
            "Pour créer votre accès, ouvrez ce lien et suivez les étapes à l'écran. Prévoyez 5 minutes et "
            f"gardez votre téléphone à portée de main : {lien}\n"
            "Ce lien est valable 7 jours, jusqu'au jeudi 22 octobre 2026 à 14 h 05. "
            "Si vous n'attendiez pas cette invitation, ignorez ce message."
        ),
    )


@pytest.mark.parametrize(
    ("role", "libelle"), [("gerant", "Gérant"), ("associe", "Associé"), ("operateur", "Opérateur")]
)
def test_courriel_invitation__role_en_mots_de_contracts_libelles(role: str, libelle: str) -> None:
    courriel = invitation("Mme Durand", "M. Martin", role, "https://lepalier.essai/activation#jeton", ETE)
    assert f"de l'immeuble de la SCI, avec le rôle {libelle}.\n" in courriel.corps


def test_courriel_invitation__fin_du_lien_a_l_heure_de_paris_en_hiver() -> None:
    courriel = invitation("Mme Durand", "M. Martin", "associe", "https://x#j", FIN_EN_HIVER)
    assert "Ce lien est valable 7 jours, jusqu'au mardi 1er décembre 2026 à 0 h 30. " in courriel.corps


def test_courriel_acces_reinitialise__mot_pour_mot() -> None:
    lien = "https://lepalier.essai/activation#" + "A" * 43
    assert acces_reinitialise("Mme Durand", lien, FIN_DU_LIEN) == Courriel(
        objet="[LePalier] Votre accès a été réinitialisé",
        corps=(
            "Bonjour Mme Durand,\n"
            "Le gérant de la SCI a réinitialisé votre accès à LePalier : "
            "votre ancien mot de passe, vos codes de secours et les codes de votre application "
            "d'authentification ne fonctionnent plus.\n"
            "Pour retrouver votre accès, ouvrez ce lien et suivez les étapes à l'écran. "
            f"Prévoyez 5 minutes et gardez votre téléphone à portée de main : {lien}\n"
            "Ce lien est valable 7 jours, jusqu'au jeudi 22 octobre 2026 à 14 h 05. "
            "Si vous ne savez pas pourquoi votre accès a été réinitialisé, "
            "contactez le gérant de la SCI."
        ),
    )


def test_courriel_reinitialisation__mot_pour_mot() -> None:
    lien = "https://lepalier.essai/reinitialisation#" + "A" * 43
    assert reinitialisation("Mme Durand", lien, FIN_DU_LIEN) == Courriel(
        objet="[LePalier] Choisir un nouveau mot de passe",
        corps=(
            "Bonjour Mme Durand,\n"
            "Vous avez demandé à changer votre mot de passe LePalier. "
            f"Ouvrez ce lien pour en choisir un nouveau : {lien}\n"
            "Vous aurez besoin de votre téléphone pour saisir votre code.\n"
            "Ce lien est valable 1 heure, jusqu'au jeudi 22 octobre 2026 à 14 h 05. "
            "Si vous n'avez rien demandé, ignorez ce message : "
            "votre mot de passe ne change pas."
        ),
    )


def test_courriel_mot_de_passe_change__mot_pour_mot() -> None:
    assert mot_de_passe_change("Mme Durand", ETE) == Courriel(
        objet="[LePalier] Votre mot de passe a été changé",
        corps=(
            "Bonjour Mme Durand,\n"
            "Le mot de passe de votre compte LePalier a été changé le mercredi 15 juillet 2026 à 1 h 30. "
            "Tous vos appareils ont été déconnectés.\n"
            "Si ce n'est pas vous, contactez tout de suite le gérant de la SCI."
        ),
    )


@pytest.mark.parametrize(
    "courriel",
    [
        acces_reinitialise("Mme Durand", "https://lepalier.essai/activation#jeton", FIN_DU_LIEN),
        reinitialisation("Mme Durand", "https://lepalier.essai/reinitialisation#jeton", FIN_DU_LIEN),
        mot_de_passe_change("Mme Durand", ETE),
        invitation(
            "Mme Durand", "M. Martin", "operateur", "https://lepalier.essai/activation#jeton", FIN_DU_LIEN
        ),
        nouvel_appareil("Mme Durand", ETE, "associe"),
        nouvel_appareil("M. Martin", ETE, "gerant"),
        alerte_echecs("M. Martin", "Mme Durand", ETE - timedelta(minutes=47), ETE),
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
        expediteur.envoyer("associe@essai.local", nouvel_appareil("Mme Durand", ETE, "associe"))


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
        courriel = nouvel_appareil("Mme Durand", ETE, "associe")
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
