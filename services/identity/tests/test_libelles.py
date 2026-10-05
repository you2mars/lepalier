from __future__ import annotations

import ast
import json
from collections import Counter
from pathlib import Path

import pytest

from app.engines.mot_de_passe import Motif
from app.libelles import libelles, message, message_mot_de_passe
from app.settings import settings

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


# --- messages des parcours de compte (validés le 4 octobre 2026) --------------------------------------

AUTRES_MESSAGES = {
    "connexion.identifiants_incorrects": (
        "L'adresse e-mail ou le mot de passe est incorrect. Vérifiez-les puis réessayez, "
        "ou choisissez « Mot de passe oublié »."
    ),
    "connexion.trop_d_essais": "Trop d'essais. Réessayez dans 15 minutes.",
    "connexion.compte_suspendu": "Votre accès a été suspendu. Contactez le gérant de la SCI.",
    "code.incorrect": (
        "Ce code ne correspond pas. Saisissez le code à 6 chiffres affiché en ce moment dans votre "
        "application d'authentification, ou l'un de vos codes de secours."
    ),
    "code.delai_depasse": (
        "Le délai pour saisir le code est dépassé. "
        "Reconnectez-vous avec votre adresse e-mail et votre mot de passe."
    ),
    "code.trop_de_codes": (
        "Trop de codes incorrects. Reconnectez-vous avec votre adresse e-mail et votre mot de passe."
    ),
    "activation.code_incorrect": (
        "Ce code ne correspond pas. Vérifiez que LePalier apparaît bien dans votre application "
        "d'authentification, puis saisissez le code à 6 chiffres qu'elle affiche en ce moment."
    ),
    "invitation.lien_invalide": (
        "Ce lien d'invitation n'est plus valable : il a expiré ou a déjà servi. "
        "Demandez-en un nouveau au gérant de la SCI."
    ),
    "invitation.deja_activee": "Ce compte est déjà activé : il n'y a pas d'invitation à renvoyer.",
    "reinitialisation.demande_envoyee": (
        "Si un compte existe pour cette adresse, un e-mail vient d'être envoyé avec un lien valable 1 heure. "
        "Pensez à regarder dans les courriers indésirables."
    ),
    "reinitialisation.lien_invalide": (
        "Ce lien n'est plus valable : il a expiré ou a déjà servi. "
        "Faites une nouvelle demande avec « Mot de passe oublié »."
    ),
    "reinitialisation.trop_de_codes": (
        "Trop de codes incorrects : ce lien n'est plus valable. "
        "Faites une nouvelle demande avec « Mot de passe oublié »."
    ),
    "nom_affiche.invalide": (
        "Indiquez un nom de 60 caractères au plus, sans « @ ». Par exemple : « Mme Durand »."
    ),
    "utilisateurs.email_invalide": (
        "Cette adresse e-mail ne semble pas correcte. Vérifiez-la, par exemple : « marie.durand@exemple.fr »."
    ),
    "utilisateurs.email_deja_utilise": (
        "Cette adresse e-mail est déjà celle d'un compte. "
        "Vérifiez la liste des utilisateurs ou choisissez une autre adresse."
    ),
    "utilisateurs.dernier_gerant": (
        "Cette modification n'est pas possible : ce compte est le dernier gérant actif. "
        "Nommez d'abord un autre gérant, puis recommencez."
    ),
    "utilisateurs.son_propre_acces": (
        "Vous ne pouvez pas réinitialiser votre propre accès ici. "
        "Demandez-le à un autre gérant, ou utilisez la commande d'administration sur le serveur."
    ),
    "idempotence.cle_manquante": (
        "Votre demande n'a pas pu être enregistrée. Rechargez la page puis réessayez."
    ),
    "idempotence.requete_en_cours": (
        "Votre demande est déjà en cours d'enregistrement. Patientez quelques secondes."
    ),
    "idempotence.cle_reutilisee": (
        "Cette demande a déjà été envoyée avec d'autres informations. Rechargez la page puis réessayez."
    ),
}


@pytest.mark.parametrize("cle", sorted(AUTRES_MESSAGES))
def test_message__parcours_de_compte__mot_pour_mot(cle: str) -> None:
    assert message(cle) == AUTRES_MESSAGES[cle]


def _toutes_les_cles() -> set[str]:
    return {f"{groupe}.{nom}" for groupe, textes in libelles().items() for nom in textes}


def test_libelles__aucune_cle_en_double_dans_le_fichier() -> None:
    doublons: list[str] = []

    def crochet(paires: list[tuple[str, object]]) -> dict[str, object]:
        doublons.extend(k for k, n in Counter(k for k, _ in paires).items() if n > 1)
        return dict(paires)

    json.loads((settings.libelles_dir / "identity.json").read_text(), object_pairs_hook=crochet)
    assert doublons == []


def test_libelles__26_messages_tous_verifies_mot_pour_mot() -> None:
    attendues = {f"mot_de_passe.{m.value}" for m in Motif} | set(AUTRES_MESSAGES)
    assert _toutes_les_cles() == attendues
    assert len(attendues) == 26


@pytest.mark.parametrize("cle", sorted(AUTRES_MESSAGES))
def test_message__parcours_de_compte__charte_ux(cle: str) -> None:
    texte = message(cle)
    assert "!" not in texte
    assert texte.endswith(".")
    for mot in ("erreur", "invalide", "token", "http", "session"):
        assert mot not in texte.lower()


def test_message__cle_inconnue__erreur_de_programmation() -> None:
    with pytest.raises(KeyError):
        message("connexion.inexistante")


# --- cohérence code ↔ fichier de libellés ----------------------------------------------------------
# Une clé du fichier pas encore utilisée par le code doit figurer dans EN_ATTENTE ; la retirer dès que le
# service qui l'utilise arrive (le test le signale).

UTILISEES_PAR_LA_CONNEXION = {
    "connexion.identifiants_incorrects",
    "connexion.trop_d_essais",
    "connexion.compte_suspendu",
    "code.incorrect",
    "code.delai_depasse",
    "code.trop_de_codes",
}
UTILISEES_PAR_L_INVITATION = {
    "activation.code_incorrect",
    "invitation.lien_invalide",
    "invitation.deja_activee",
    "nom_affiche.invalide",
    "utilisateurs.email_invalide",
    "utilisateurs.email_deja_utilise",
}
UTILISEES_PAR_LA_REINITIALISATION = {
    "reinitialisation.demande_envoyee",
    "reinitialisation.lien_invalide",
    "reinitialisation.trop_de_codes",
}
EN_ATTENTE = (
    set(AUTRES_MESSAGES)
    - UTILISEES_PAR_LA_CONNEXION
    - UTILISEES_PAR_L_INVITATION
    - UTILISEES_PAR_LA_REINITIALISATION
)
APP = Path(__file__).resolve().parents[1] / "app"


# fonctions du code qui reçoivent une clé de libellé ; à compléter quand un service en ajoute une
FONCTIONS_LIBELLES = {"message", "refuser"}


def _cles_utilisees_par_le_code() -> set[str]:
    """Chaînes « groupe.nom » passées à une fonction de FONCTIONS_LIBELLES dans app/, plus les clés tirées de
    Motif ; les actions du journal (« connexion.reussie ») ne sont pas des libellés."""
    cles = {f"mot_de_passe.{m.value}" for m in Motif}
    for fichier in APP.rglob("*.py"):
        for noeud in ast.walk(ast.parse(fichier.read_text())):
            if (
                isinstance(noeud, ast.Call)
                and isinstance(noeud.func, ast.Name)
                and noeud.func.id in FONCTIONS_LIBELLES
            ):
                for argument in noeud.args:
                    if (
                        isinstance(argument, ast.Constant)
                        and isinstance(argument.value, str)
                        and "." in argument.value
                    ):
                        cles.add(argument.value)
    return cles


def test_coherence__toute_cle_utilisee_par_le_code_existe_dans_le_fichier() -> None:
    assert _cles_utilisees_par_le_code() - _toutes_les_cles() == set()


def test_coherence__toute_cle_du_fichier_est_utilisee_ou_en_attente() -> None:
    assert _toutes_les_cles() - _cles_utilisees_par_le_code() - EN_ATTENTE == set()


def test_coherence__liste_d_attente_a_jour() -> None:
    deja_utilisees = EN_ATTENTE & _cles_utilisees_par_le_code()
    assert deja_utilisees == set(), f"à retirer de EN_ATTENTE : {sorted(deja_utilisees)}"
