"""make recette LOT=0 : jeu de comptes invités, gérant par la commande locale, associé et opérateur par le
service d'invitation d'identity (docs/RECETTE/lot-0.md, journal du lot 0).

Docker Compose est remplacé par une fausse exécution qui tient la liste des comptes ; l'essai réel est dans
test_plateforme.py.
"""

from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType

import pytest

RACINE = Path(__file__).resolve().parents[2]
GERANT_ID = "01900000-0000-7000-8000-000000000001"


def _module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "recette_lot_0", RACINE / "scripts" / "recette" / "lot-0.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


lot0 = _module()


@dataclass
class FauxCompose:
    """Le service des comptes vu par le script : comptes existants, commandes reçues."""

    comptes: list[dict[str, str]] = field(default_factory=list)
    identity_demarre: bool = True
    code_creer_gerant: int = 0
    appels: list[tuple[list[str], bool]] = field(default_factory=list)

    def __call__(self, arguments: list[str], capturer: bool) -> subprocess.CompletedProcess[str]:
        self.appels.append((arguments, capturer))
        if arguments[:1] == ["ps"]:
            return subprocess.CompletedProcess(
                arguments, 0, "identity\n" if self.identity_demarre else "", ""
            )
        assert arguments[:3] == ["exec", "-T", "identity"], arguments
        commande = arguments[3:]
        if commande[:3] == ["python", "-m", "app.admin"]:
            if self.code_creer_gerant == 0:
                self._ajouter(commande[commande.index("--email") + 1], "gerant", GERANT_ID)
            return subprocess.CompletedProcess(arguments, self.code_creer_gerant, None, None)
        assert commande[:2] == ["python", "-c"], commande
        if commande[2] == lot0.LIRE_COMPTES:
            return subprocess.CompletedProcess(arguments, 0, json.dumps(self.comptes) + "\n", "")
        assert commande[2] == lot0.INVITER, commande
        par, email, _nom, role = commande[3:]
        assert par == GERANT_ID
        self._ajouter(email, role, f"01900000-0000-7000-8000-00000000000{len(self.comptes) + 1}")
        return subprocess.CompletedProcess(arguments, 0, "", "")

    def _ajouter(self, email: str, role: str, uid: str) -> None:
        self.comptes.append(
            {
                "id": uid,
                "email": email,
                "role": role,
                "statut": "invite",
                "statut_libelle": "Invitation envoyée",
            }
        )

    def commandes(self) -> list[list[str]]:
        return [a[3:] for a, _ in self.appels if a[:1] == ["exec"] and a[4:6] != ["-c", lot0.LIRE_COMPTES]]


def _lancer(compose: FauxCompose) -> tuple[int, str]:
    sortie = io.StringIO()
    code = lot0.charger(compose, sortie)
    return code, sortie.getvalue()


ACCUEIL = "Jeu de recette du lot 0 : un gérant, un associé invité et un opérateur invité.\n"


def test_recette_lot0__base_vide__gerant_par_commande_locale_puis_deux_invitations_au_nom_du_gerant() -> None:
    compose = FauxCompose()
    code, texte = _lancer(compose)
    assert code == 0
    assert compose.commandes() == [
        ["python", "-m", "app.admin", "creer-gerant", "--email", "gerant@test.local", "--nom", "M. Martin"],
        ["python", "-c", lot0.INVITER, GERANT_ID, "associe.jeu@test.local", "M. Bernard", "associe"],
        ["python", "-c", lot0.INVITER, GERANT_ID, "operateur.jeu@test.local", "Mme Petit", "operateur"],
    ]
    assert texte == (
        ACCUEIL + "Invitation créée pour M. Bernard (associe.jeu@test.local), rôle Associé : "
        "l'e-mail d'invitation arrive dans Mailpit.\n"
        "Invitation créée pour Mme Petit (operateur.jeu@test.local), rôle Opérateur : "
        "l'e-mail d'invitation arrive dans Mailpit.\n"
        "Les invitations de l'associé et de l'opérateur ont été créées par ce script au nom du gérant "
        "(M. Martin), avant l'activation de son compte.\n"
        "Suite : ouvrez dans l'heure le lien d'activation du gérant affiché plus haut, puis suivez "
        "docs/RECETTE/lot-0.md.\n"
    )


def test_recette_lot0__lien_du_gerant_affiche_par_la_commande_locale_jamais_lu_par_le_script() -> None:
    """ADR 0006 : le lien n'est affiché qu'une fois, par app.admin lui-même ; le script ne le capture pas."""
    compose = FauxCompose()
    _lancer(compose)
    (capturer,) = [c for a, c in compose.appels if "creer-gerant" in a]
    assert capturer is False
    assert all(c for a, c in compose.appels if "creer-gerant" not in a)


def test_recette_lot0__relance__rien_cree_ni_modifie_aucun_nouveau_lien() -> None:
    compose = FauxCompose()
    _lancer(compose)
    compose.appels.clear()
    code, texte = _lancer(compose)
    assert code == 0
    assert compose.commandes() == []
    assert texte == (
        ACCUEIL
        + "Compte gérant gerant@test.local déjà présent (statut : Invitation envoyée) : aucun nouveau lien. "
        "Pour en obtenir un : docker compose -f compose.dev.yml exec identity python -m app.admin "
        "reinitialiser-acces --email gerant@test.local\n"
        "Compte associe.jeu@test.local déjà présent (statut : Invitation envoyée) : rien n'a été modifié.\n"
        "Compte operateur.jeu@test.local déjà présent (statut : Invitation envoyée) : rien n'a été modifié.\n"
        "Suite : suivez docs/RECETTE/lot-0.md.\n"
    )


@pytest.mark.parametrize("libelle", ["Invitation envoyée", "Invitation expirée"])
def test_recette_lot0__relance_gerant_invite__commande_du_nouveau_lien_proposee(libelle: str) -> None:
    compose = FauxCompose()
    _lancer(compose)
    compose.comptes[0]["statut_libelle"] = libelle
    _, texte = _lancer(compose)
    assert (
        f"Compte gérant gerant@test.local déjà présent (statut : {libelle}) : aucun nouveau lien. "
        "Pour en obtenir un : docker compose -f compose.dev.yml exec identity python -m app.admin "
        "reinitialiser-acces --email gerant@test.local\n"
    ) in texte


@pytest.mark.parametrize(("statut", "libelle"), [("actif", "Accès actif"), ("suspendu", "Accès suspendu")])
def test_recette_lot0__relance_gerant_actif_ou_suspendu__aucune_commande_proposee(statut: str, libelle: str) -> None:
    compose = FauxCompose()
    _lancer(compose)
    compose.comptes[0].update(statut=statut, statut_libelle=libelle)
    _, texte = _lancer(compose)
    assert f"Compte gérant gerant@test.local déjà présent (statut : {libelle}) : aucun nouveau lien.\n" in texte
    assert "reinitialiser-acces" not in texte


def test_recette_lot0__gerant_present_operateur_absent__seul_l_operateur_est_invite() -> None:
    compose = FauxCompose()
    _lancer(compose)
    compose.comptes.pop()
    compose.appels.clear()
    code, texte = _lancer(compose)
    assert code == 0
    assert [c[4] for c in compose.commandes()] == ["operateur.jeu@test.local"]
    assert "Invitation créée pour Mme Petit (operateur.jeu@test.local)" in texte
    assert "Les invitations de l'associé et de l'opérateur" not in texte
    assert texte.endswith(
        "L'invitation de l'opérateur a été créée par ce script au nom du gérant (M. Martin), "
        "avant l'activation de son compte.\nSuite : suivez docs/RECETTE/lot-0.md.\n"
    )


def test_recette_lot0__identity_non_demarre__message_et_aucune_commande() -> None:
    compose = FauxCompose(identity_demarre=False)
    code, texte = _lancer(compose)
    assert code == 1
    assert compose.commandes() == []
    assert texte == (
        ACCUEIL + "Rien n'a été créé : le service des comptes (identity) n'est pas démarré. "
        "Lancez make dev-up, puis recommencez make recette LOT=0.\n"
    )


def test_recette_lot0__echec_de_la_commande_locale__aucune_invitation() -> None:
    compose = FauxCompose(code_creer_gerant=1)
    code, texte = _lancer(compose)
    assert code == 1
    assert [c[3] for c in compose.commandes()] == ["creer-gerant"]
    assert texte == (
        ACCUEIL + "Le compte gérant n'a pas été créé (message ci-dessus) : aucune invitation n'a été faite. "
        "Corrigez la cause, puis recommencez make recette LOT=0.\n"
    )


def test_recette_lot0__adresse_du_gerant_prise_par_un_autre_role__rien_cree() -> None:
    compose = FauxCompose(
        comptes=[
            {
                "id": GERANT_ID,
                "email": "gerant@test.local",
                "role": "associe",
                "statut": "actif",
                "statut_libelle": "Accès actif",
            }
        ]
    )
    code, texte = _lancer(compose)
    assert code == 1
    assert compose.commandes() == []
    assert texte == (
        ACCUEIL + "Rien n'a été créé : l'adresse gerant@test.local est celle d'un compte Associé, pas d'un "
        "gérant. Vérifiez la liste des utilisateurs dans Administration, puis recommencez "
        "make recette LOT=0.\n"
    )


def test_recette_lot0__echec_d_une_invitation__arret_avec_le_message_du_service() -> None:
    compose = FauxCompose()

    def refuser(arguments: list[str], capturer: bool) -> subprocess.CompletedProcess[str]:
        if lot0.INVITER in arguments:
            compose.appels.append((arguments, capturer))
            return subprocess.CompletedProcess(arguments, 1, "", "Traceback…\nHTTPException: 409\n")
        return compose(arguments, capturer)

    sortie = io.StringIO()
    code = lot0.charger(refuser, sortie)
    assert code == 1
    assert [c[4] for c in compose.commandes() if c[1] == "-c"] == ["associe.jeu@test.local"]
    assert sortie.getvalue().endswith(
        "L'invitation de M. Bernard (associe.jeu@test.local) n'a pas été créée ; réponse du service des "
        "comptes :\nTraceback…\nHTTPException: 409\n"
        "Les comptes déjà créés sont gardés : corrigez la cause, puis recommencez make recette LOT=0.\n"
    )


def test_recette_lot0__commande_compose_reglable_pour_les_essais(monkeypatch: pytest.MonkeyPatch) -> None:
    assert lot0.commande_compose() == ["docker", "compose", "-f", "compose.dev.yml"]
    monkeypatch.setenv("LEPALIER_COMPOSE", "docker compose -f a.yml -p essai")
    assert lot0.commande_compose() == ["docker", "compose", "-f", "a.yml", "-p", "essai"]


def test_recette_lot0__code_lance_dans_identity__passe_par_le_service_sans_ecriture_sql() -> None:
    """Décision de Youssef (15 octobre 2026) : le service et ses règles, aucune écriture SQL directe."""
    assert "services.utilisateurs import inviter" in lot0.INVITER
    assert "email_saisi" in lot0.INVITER and "nom_affiche_saisi" in lot0.INVITER
    for code in (lot0.INVITER, lot0.LIRE_COMPTES):
        assert not any(mot in code for mot in ("insert", "update(", "execute", "sqlalchemy"))
