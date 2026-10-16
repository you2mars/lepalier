"""Jeu de données de la recette du lot 0 (make recette LOT=0, docs/RECETTE/lot-0.md).

Trois comptes invités, aucun activé : le gérant par la commande locale d'identity (son lien d'activation est
affiché une seule fois par la commande elle-même, jamais lu par ce script, ADR 0006), puis l'associé et
l'opérateur par le service d'invitation d'identity, au nom du gérant, avant son activation ; leurs e-mails
arrivent dans Mailpit. Aucune écriture SQL directe. Relancé, le script garde les comptes déjà présents.

LEPALIER_COMPOSE remplace la commande Docker Compose (essais de la plateforme seulement).
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TextIO

Executer = Callable[[list[str], bool], subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class Compte:
    email: str
    nom: str
    role: str


GERANT = Compte("gerant@test.local", "M. Martin", "gerant")
# adresses distinctes de associe@test.local, invitée à la main en R0-04 et R0-38
INVITES = (
    Compte("associe.jeu@test.local", "M. Bernard", "associe"),
    Compte("operateur.jeu@test.local", "Mme Petit", "operateur"),
)
ROLES = {"gerant": "Gérant", "associe": "Associé", "operateur": "Opérateur"}
DESIGNATIONS = {"associe": "l'associé", "operateur": "l'opérateur"}

# code lancé dans le conteneur d'identity : uniquement ses services, avec leurs règles
LIRE_COMPTES = """
import json
from app.db import fabrique
from app.services.utilisateurs import lister
print(json.dumps(lister(fabrique())))
"""
INVITER = """
import sys
from uuid import UUID
from app.api.saisie import email_saisi, nom_affiche_saisi
from app.db import fabrique
from app.services.utilisateurs import inviter
par, email, nom, role = sys.argv[1:]
inviter(fabrique(), UUID(par), email_saisi(email), nom_affiche_saisi(nom), role, None)
"""

SUITE = "suivez docs/RECETTE/lot-0.md."


def commande_compose() -> list[str]:
    return shlex.split(os.environ.get("LEPALIER_COMPOSE", "docker compose -f compose.dev.yml"))


def executer_compose(arguments: list[str], capturer: bool) -> subprocess.CompletedProcess[str]:
    """capturer=False : sortie affichée directement dans le terminal, jamais lue par le script."""
    return subprocess.run(  # noqa: S603 - commande fixe, arguments sans shell
        [*commande_compose(), *arguments], capture_output=capturer, text=True, check=False
    )


class Arret(Exception):
    """Message final affiché tel quel ; le script s'arrête avec le code 1."""


def _identity(*commande: str) -> list[str]:
    return ["exec", "-T", "identity", *commande]


def _comptes(executer: Executer) -> dict[str, dict[str, Any]]:
    r = executer(_identity("python", "-c", LIRE_COMPTES), True)
    if r.returncode != 0:
        raise Arret(
            "Rien n'a été créé : la liste des comptes n'a pas pu être lue ; réponse du service des "
            f"comptes :\n{r.stderr.rstrip()}"
        )
    return {u["email"].lower(): u for u in json.loads(r.stdout)}


def _gerant(executer: Executer, sortie: TextIO) -> tuple[str, bool]:
    """Identifiant du gérant, et vrai s'il vient d'être créé (lien affiché par la commande locale)."""
    present = _comptes(executer).get(GERANT.email)
    if present is not None:
        if present["role"] != "gerant":
            raise Arret(
                f"Rien n'a été créé : l'adresse {GERANT.email} est celle d'un compte "
                f"{ROLES[present['role']]}, pas d'un gérant. Vérifiez la liste des utilisateurs dans "
                "Administration, puis recommencez make recette LOT=0."
            )
        ligne = f"Compte gérant {GERANT.email} déjà présent (statut : {present['statut_libelle']}) : aucun nouveau lien."
        if present["statut"] == "invite":
            # invitation envoyée ou expirée : la commande invalide les liens précédents et en affiche un neuf
            ligne += (
                " Pour en obtenir un : docker compose -f compose.dev.yml exec identity python -m app.admin "
                f"reinitialiser-acces --email {GERANT.email}"
            )
        sortie.write(f"{ligne}\n")
        return present["id"], False
    sortie.flush()
    commande = ("python", "-m", "app.admin", "creer-gerant", "--email", GERANT.email, "--nom", GERANT.nom)
    if executer(_identity(*commande), False).returncode != 0:
        raise Arret(
            "Le compte gérant n'a pas été créé (message ci-dessus) : aucune invitation n'a été faite. "
            "Corrigez la cause, puis recommencez make recette LOT=0."
        )
    return _comptes(executer)[GERANT.email]["id"], True


def _inviter(executer: Executer, sortie: TextIO, gerant_id: str) -> list[Compte]:
    presents = _comptes(executer)
    crees = []
    for compte in INVITES:
        present = presents.get(compte.email)
        if present is not None:
            sortie.write(
                f"Compte {compte.email} déjà présent (statut : {present['statut_libelle']}) : rien n'a été "
                "modifié.\n"
            )
            continue
        r = executer(
            _identity("python", "-c", INVITER, gerant_id, compte.email, compte.nom, compte.role), True
        )
        if r.returncode != 0:
            raise Arret(
                f"L'invitation de {compte.nom} ({compte.email}) n'a pas été créée ; réponse du service des "
                f"comptes :\n{r.stderr.rstrip()}\nLes comptes déjà créés sont gardés : corrigez la cause, "
                "puis recommencez make recette LOT=0."
            )
        sortie.write(
            f"Invitation créée pour {compte.nom} ({compte.email}), rôle {ROLES[compte.role]} : l'e-mail "
            "d'invitation arrive dans Mailpit.\n"
        )
        crees.append(compte)
    return crees


def _resume(crees: list[Compte]) -> str:
    fin = f"créée{'s' if len(crees) > 1 else ''} par ce script au nom du gérant ({GERANT.nom}), avant "
    fin += "l'activation de son compte.\n"
    if len(crees) > 1:
        return "Les invitations de " + " et de ".join(DESIGNATIONS[c.role] for c in crees) + " ont été " + fin
    return f"L'invitation de {DESIGNATIONS[crees[0].role]} a été " + fin


def charger(executer: Executer, sortie: TextIO) -> int:
    sortie.write("Jeu de recette du lot 0 : un gérant, un associé invité et un opérateur invité.\n")
    try:
        demarres = executer(["ps", "--services", "--status", "running"], True)
        if "identity" not in demarres.stdout.split():
            raise Arret(
                "Rien n'a été créé : le service des comptes (identity) n'est pas démarré. Lancez "
                "make dev-up, puis recommencez make recette LOT=0."
            )
        gerant_id, gerant_cree = _gerant(executer, sortie)
        crees = _inviter(executer, sortie, gerant_id)
    except Arret as arret:
        sortie.write(f"{arret}\n")
        return 1
    if crees:
        sortie.write(_resume(crees))
    if gerant_cree:
        sortie.write(f"Suite : ouvrez dans l'heure le lien d'activation du gérant affiché plus haut, puis {SUITE}\n")
    else:
        sortie.write(f"Suite : {SUITE}\n")
    return 0


if __name__ == "__main__":
    sys.exit(charger(executer_compose, sys.stdout))
