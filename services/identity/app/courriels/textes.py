"""Textes des e-mails de compte, validés le 4 octobre 2026, revus le 16 octobre 2026 (ADR 0006, UX-13, UX-16).

Objet « [LePalier] … », 5 lignes au plus, aucun mot de passe ni code ; dates en toutes lettres, heure de
Paris.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.libelles import libelle_role
from commun.dates import PARIS, date_heure_paris


@dataclass(frozen=True)
class Courriel:
    objet: str
    corps: str


def _valable(duree: str, expire_le: datetime) -> str:
    """« Ce lien est valable 7 jours, jusqu'au jeudi 23 octobre 2026 à 14 h 05. » (UX-13), heure de Paris."""
    date, heure = date_heure_paris(expire_le)
    return f"Ce lien est valable {duree}, jusqu'au {date} à {heure}."


def nouvel_appareil(nom_affiche: str, instant: datetime, role: str) -> Courriel:
    """Le gérant n'a personne à prévenir : la phrase s'arrête au changement de mot de passe."""
    date, heure = date_heure_paris(instant)
    prevenir = "" if role == "gerant" else ", puis prévenez le gérant"
    return Courriel(
        objet="[LePalier] Nouvelle connexion à votre compte",
        corps=(
            f"Bonjour {nom_affiche},\n"
            f"Votre compte LePalier a été utilisé le {date} à {heure} depuis un appareil ou un navigateur "
            "utilisé pour la première fois.\n"
            "Si c'est vous, il n'y a rien à faire. Sinon, changez tout de suite votre mot de passe avec "
            f"« Mot de passe oublié » sur la page de connexion{prevenir}."
        ),
    )


def alerte_echecs(nom_gerant: str, nom_affiche: str, debut: datetime, instant: datetime) -> Courriel:
    """`debut` : premier des échecs comptés dans l'heure ; `instant` : celui qui a atteint le seuil. Une heure
    qui passe minuit porte deux dates, la seconde sans l'année si c'est la même."""
    date, h1 = date_heure_paris(debut)
    date2, h2 = date_heure_paris(instant)
    if date2 == date:
        quand = f"le {date} entre {h1} et {h2}"
    else:
        annee = f" {debut.astimezone(PARIS).year}"
        fin = date2.removesuffix(annee) if date2.endswith(annee) else date2
        quand = f"entre le {date} à {h1} et le {fin} à {h2}"
    return Courriel(
        objet="[LePalier] Nombreux essais de connexion sur un compte",
        corps=(
            f"Bonjour {nom_gerant},\n"
            "Au moins 20 essais de connexion ont échoué en une heure sur le compte de "
            f"{nom_affiche}, {quand}.\n"
            f"Ces essais viennent peut-être d'une autre personne. Vérifiez avec {nom_affiche} et, si besoin, "
            "suspendez son accès dans Administration, Utilisateurs."
        ),
    )


def alerte_compte_suspendu(nom_gerant: str, nom_affiche: str, instant: datetime) -> Courriel:
    date, heure = date_heure_paris(instant)
    return Courriel(
        objet="[LePalier] Connexion d'un compte suspendu",
        corps=(
            f"Bonjour {nom_gerant},\n"
            f"{nom_affiche} a essayé de se connecter le {date} à {heure}, avec le bon mot de passe et le "
            "bon code, alors que son accès est suspendu.\n"
            "Si cet accès doit être rétabli, réactivez-le dans Administration, Utilisateurs."
        ),
    )


def invitation(nom_affiche: str, nom_gerant: str, role: str, lien: str, expire_le: datetime) -> Courriel:
    return Courriel(
        objet="[LePalier] Votre invitation",
        corps=(
            f"Bonjour {nom_affiche},\n"
            f"{nom_gerant} vous invite à utiliser LePalier, "
            "l'application de gestion de l'immeuble de la SCI, "
            f"avec le rôle {libelle_role(role)}.\n"
            "Pour créer votre accès, ouvrez ce lien et suivez les étapes à l'écran. Prévoyez 5 minutes et "
            f"gardez votre téléphone à portée de main : {lien}\n"
            f"{_valable('7 jours', expire_le)} Si vous n'attendiez pas cette invitation, ignorez ce message."
        ),
    )


def reinitialisation(nom_affiche: str, lien: str, expire_le: datetime) -> Courriel:
    return Courriel(
        objet="[LePalier] Choisir un nouveau mot de passe",
        corps=(
            f"Bonjour {nom_affiche},\n"
            "Vous avez demandé à changer votre mot de passe LePalier. "
            f"Ouvrez ce lien pour en choisir un nouveau : {lien}\n"
            "Vous aurez besoin de votre téléphone pour saisir votre code.\n"
            f"{_valable('1 heure', expire_le)} Si vous n'avez rien demandé, ignorez ce message : "
            "votre mot de passe ne change pas."
        ),
    )


def mot_de_passe_change(nom_affiche: str, instant: datetime) -> Courriel:
    date, heure = date_heure_paris(instant)
    return Courriel(
        objet="[LePalier] Votre mot de passe a été changé",
        corps=(
            f"Bonjour {nom_affiche},\n"
            f"Le mot de passe de votre compte LePalier a été changé le {date} à {heure}. "
            "Tous vos appareils ont été déconnectés.\n"
            "Si ce n'est pas vous, contactez tout de suite le gérant de la SCI."
        ),
    )


def acces_reinitialise(nom_affiche: str, lien: str, expire_le: datetime) -> Courriel:
    return Courriel(
        objet="[LePalier] Votre accès a été réinitialisé",
        corps=(
            f"Bonjour {nom_affiche},\n"
            "Le gérant de la SCI a réinitialisé votre accès à LePalier : "
            "votre ancien mot de passe, vos codes de secours et les codes de votre application "
            "d'authentification ne fonctionnent plus.\n"
            "Pour retrouver votre accès, ouvrez ce lien et suivez les étapes à l'écran. "
            f"Prévoyez 5 minutes et gardez votre téléphone à portée de main : {lien}\n"
            f"{_valable('7 jours', expire_le)} Si vous ne savez pas pourquoi votre accès a été réinitialisé, "
            "contactez le gérant de la SCI."
        ),
    )
