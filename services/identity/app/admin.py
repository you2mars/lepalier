"""Commande d'administration locale (ADR 0006, décision 5), exécutable seulement dans le conteneur :

    python -m app.admin creer-gerant --email <adresse> --nom <nom affiché>
    python -m app.admin reinitialiser-acces --email <adresse>

Aucune route HTTP ne l'expose. Le lien d'activation, valable 1 heure, est affiché une seule fois sur la sortie
standard : jamais journalisé, jamais écrit dans un fichier ni dans un job ; le journal porte un auteur null.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from datetime import datetime
from typing import TextIO

from sqlalchemy import func, insert, select
from sqlalchemy.orm import Session

from app.api.saisie import email_saisi, nom_affiche_saisi
from app.engines import durees
from app.engines.jetons import empreinte, nouveau_jeton
from app.libelles import message
from app.models import INVITATION, JOURNAL_SVC, UTILISATEUR
from app.services.utilisateurs import effacer_acces
from commun.dates import heure_paris
from commun.ids import uuid7

Fabrique = Callable[[], Session]

COMPTE_INCONNU = "Aucun compte n'a cette adresse e-mail. Vérifiez l'adresse puis recommencez."


def consigne_lien(expire_le: datetime) -> str:
    """Heure limite à l'heure de Paris (UX-13)."""
    heure = heure_paris(expire_le)
    return (
        f"Lien d'activation, valable 1 heure (jusqu'à {heure}) et affiché une seule fois : "
        "ouvrez-le, puis suivez les étapes à l'écran."
    )


class Refus(Exception):
    """Message affiché tel quel sur la sortie d'erreur ; rien n'a été écrit en base."""


def _lien(s: Session, utilisateur_id: object, url_publique: str) -> str:
    """Consigne (avec l'heure limite) puis lien, une ligne chacun."""
    maintenant = s.execute(select(func.now())).scalar_one()
    expire_le = maintenant + durees.DUREE_LIEN_COMMANDE_LOCALE
    jeton = nouveau_jeton()
    s.execute(
        insert(INVITATION).values(
            id=uuid7(),
            utilisateur_id=utilisateur_id,
            empreinte=empreinte(jeton),
            cree_le=maintenant,
            expire_le=expire_le,
            par_utilisateur_id=None,
        )
    )
    return f"{consigne_lien(expire_le)}\n{url_publique.rstrip('/')}/activation#{jeton}"


def _saisie(controle: Callable[[str], str], valeur: str) -> str:
    try:
        return controle(valeur)
    except ValueError as exc:
        raise Refus(str(exc)) from exc


def creer_gerant(fabrique: Fabrique, email: str, nom: str, url_publique: str) -> str:
    adresse = _saisie(email_saisi, email)
    nom_affiche = _saisie(nom_affiche_saisi, nom)
    with fabrique() as s, s.begin():
        existe = s.execute(
            select(UTILISATEUR.c.id).where(
                func.lower(UTILISATEUR.c.email) == adresse.lower(), UTILISATEUR.c.statut != "annule"
            )
        ).first()
        if existe is not None:
            raise Refus(message("utilisateurs.email_deja_utilise"))
        uid = uuid7()
        s.execute(
            insert(UTILISATEUR).values(
                id=uid,
                email=adresse,
                nom_affiche=nom_affiche,
                role="gerant",
                statut="invite",
                origine="commande_locale",
                invite_par=None,
            )
        )
        JOURNAL_SVC.ecrire(
            s,
            action="utilisateur.invite",
            table_cible="utilisateur",
            enregistrement_id=uid,
            apres={"role": "gerant", "statut": "invite", "origine": "commande_locale"},
        )
        lien = _lien(s, uid, url_publique)
    return f"Compte gérant créé pour {nom_affiche}.\n{lien}\n"


def reinitialiser_acces(fabrique: Fabrique, email: str, url_publique: str) -> str:
    """Pour un gérant bloqué (téléphone perdu, plus de codes de secours) : même effet que la réinitialisation
    par un gérant, sans e-mail ; le lien est affiché ici."""
    with fabrique() as s, s.begin():
        u = (
            s.execute(
                select(UTILISATEUR)
                .where(
                    func.lower(UTILISATEUR.c.email) == email.strip().lower(), UTILISATEUR.c.statut != "annule"
                )
                .with_for_update()
            )
            .mappings()
            .first()
        )
        if u is None:
            raise Refus(COMPTE_INCONNU)
        if u["statut"] == "suspendu":
            # même règle que la route : réactiver d'abord
            raise Refus(message("utilisateurs.acces_suspendu"))
        effacer_acces(s, u, s.execute(select(func.now())).scalar_one(), None, None)
        lien = _lien(s, u["id"], url_publique)
    return (
        f"Accès de {u['nom_affiche']} réinitialisé : ancien mot de passe, codes de secours et codes de "
        f"l'application d'authentification ne fonctionnent plus.\n{lien}\n"
    )


def _analyseur() -> argparse.ArgumentParser:
    analyseur = argparse.ArgumentParser(
        prog="python -m app.admin", description="Administration locale d'identity"
    )
    commandes = analyseur.add_subparsers(dest="commande", required=True)
    creer = commandes.add_parser(
        "creer-gerant", help="créer un compte gérant et afficher son lien d'activation"
    )
    creer.add_argument("--email", required=True)
    creer.add_argument("--nom", required=True, help="nom affiché, par exemple « M. Martin »")
    reinit = commandes.add_parser("reinitialiser-acces", help="réinitialiser l'accès d'un compte bloqué")
    reinit.add_argument("--email", required=True)
    return analyseur


def main(
    arguments: Sequence[str] | None = None,
    *,
    fabrique: Fabrique | None = None,
    url_publique: str | None = None,
    sortie: TextIO = sys.stdout,
    erreur: TextIO = sys.stderr,
) -> int:
    try:
        lus = _analyseur().parse_args(arguments)
    except SystemExit as exc:
        return int(exc.code or 0)
    if fabrique is None or url_publique is None:  # pragma: no cover - valeurs réelles dans le conteneur
        from app.db import fabrique as fabrique_reelle
        from app.settings import settings

        fabrique = fabrique or fabrique_reelle()
        url_publique = url_publique or settings.url_publique
    try:
        if lus.commande == "creer-gerant":
            texte = creer_gerant(fabrique, lus.email, lus.nom, url_publique)
        else:
            texte = reinitialiser_acces(fabrique, lus.email, url_publique)
    except Refus as exc:
        erreur.write(f"{exc}\n")
        return 1
    sortie.write(texte)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
