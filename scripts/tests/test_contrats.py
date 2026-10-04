"""make contracts (scripts/check_contracts.py) : règles générales et contrats utilisateur.* (ADR 0006)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

RACINE = Path(__file__).resolve().parents[2]
CONTRATS = RACINE / "contracts"
FAITS_UTILISATEUR = ["cree", "role_change", "suspendu", "reactive"]


def _verifier(dossier: Path = CONTRATS) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "CONTRATS_DIR": str(dossier)}
    return subprocess.run(
        [sys.executable, str(RACINE / "scripts" / "check_contracts.py")],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _schema(fait: str) -> dict[str, Any]:
    return json.loads((CONTRATS / "events" / "utilisateur" / f"{fait}.v1.json").read_text())  # type: ignore[no-any-return]


def _validateur(fait: str) -> Draft202012Validator:
    return Draft202012Validator(_schema(fait), format_checker=Draft202012Validator.FORMAT_CHECKER)


@pytest.fixture
def copie(tmp_path: Path) -> Path:
    cible = tmp_path / "contracts"
    shutil.copytree(CONTRATS, cible)
    return cible


def _modifier(copie: Path, relatif: str, modification: Callable[[dict[str, Any]], None]) -> None:
    chemin = copie / "events" / relatif
    schema = json.loads(chemin.read_text())
    modification(schema)
    chemin.write_text(json.dumps(schema))


def _refuse(copie: Path, message: str) -> None:
    r = _verifier(copie)
    assert r.returncode == 1, r.stdout
    assert message in r.stdout


# --- dépôt et contrats utilisateur.* ------------------------------------------------------------------


def test_contrats__depot_actuel__valides() -> None:
    r = _verifier()
    assert r.returncode == 0, r.stdout
    assert "contrats OK" in r.stdout


@pytest.mark.parametrize("fait", FAITS_UTILISATEUR)
def test_contrat_utilisateur_v1__exemples_valides_formats_compris(fait: str) -> None:
    schema = _schema(fait)
    for exemple in schema["examples"]:
        assert list(_validateur(fait).iter_errors(exemple)) == []
    attendus = {"utilisateur_id", "role", "associe_id", "nom_affiche", "par_utilisateur_id"}
    assert attendus <= set(schema["required"])
    assert schema["properties"]["nom_affiche"]["maxLength"] == 60


def test_contrat_utilisateur_role_change__porte_l_ancien_role() -> None:
    assert "ancien_role" in _schema("role_change")["required"]


@pytest.mark.parametrize("fait", FAITS_UTILISATEUR)
@pytest.mark.parametrize("nom", ["jean.dupont@exemple.fr", "a@b", "", " ", "   \t", "x" * 61])
def test_contrat_utilisateur__nom_affiche_email_vide_ou_trop_long__refuse(fait: str, nom: str) -> None:
    exemple = {**_schema(fait)["examples"][0], "nom_affiche": nom}
    assert list(_validateur(fait).iter_errors(exemple)) != []


@pytest.mark.parametrize("nom", ["Mme Durand", "Jean-Pierre O'Neil", "É", "x" * 60])
def test_contrat_utilisateur__nom_affiche_ordinaire__accepte(nom: str) -> None:
    exemple = {**_schema("cree")["examples"][0], "nom_affiche": nom}
    assert list(_validateur("cree").iter_errors(exemple)) == []


@pytest.mark.parametrize("fait", FAITS_UTILISATEUR)
def test_contrat_utilisateur__auteur_requis_null_pour_l_administration_locale(fait: str) -> None:
    exemple = dict(_schema(fait)["examples"][0])
    assert list(_validateur(fait).iter_errors({**exemple, "par_utilisateur_id": None})) == []
    del exemple["par_utilisateur_id"]
    assert list(_validateur(fait).iter_errors(exemple)) != []


# --- champs interdits dans utilisateur.* (mots du nom, pas sous-chaîne) -------------------------------


def _ajouter_champ(copie: Path, champ: str, imbrique: bool = False) -> None:
    def ajouter(schema: dict[str, Any]) -> None:
        definition: dict[str, Any] = {"type": "string"}
        if imbrique:
            schema["properties"]["details"] = {"type": "object", "properties": {champ: definition}}
        else:
            schema["properties"][champ] = definition

    _modifier(copie, "utilisateur/cree.v1.json", ajouter)


@pytest.mark.parametrize(
    "champ",
    [
        "email",
        "Email",
        "eMail",
        "courriel",
        "adresse_electronique",
        "adresse_mail",
        "mot_de_passe_hache",
        "mdp",
        "ip",
        "ip_source",
        "totp_secret",
        "jeton_invitation",
        "code_secours",
        "user_agent",
        "cle_api",
        "émpreinte",
    ],
)
def test_contrat_utilisateur__email_ou_secret__refuse(copie: Path, champ: str) -> None:
    _ajouter_champ(copie, champ)
    _refuse(copie, "interdit dans utilisateur.*")


@pytest.mark.parametrize("champ", ["code_postal", "description", "equipe", "type_bail", "Code"])
def test_contrat_utilisateur__mot_proche_mais_autorise__accepte(copie: Path, champ: str) -> None:
    _ajouter_champ(copie, champ)
    r = _verifier(copie)
    assert r.returncode == 0, r.stdout


def test_contrat_utilisateur__champ_interdit_imbrique__refuse(copie: Path) -> None:
    _ajouter_champ(copie, "email", imbrique=True)
    _refuse(copie, "details.email interdit dans utilisateur.*")


# --- autres règles du contrôleur ----------------------------------------------------------------------


@pytest.mark.parametrize("champ", ["role", "nouveau_role"])
def test_contrat__role_hors_enumeration__refuse(copie: Path, champ: str) -> None:
    def ajouter(schema: dict[str, Any]) -> None:
        schema["properties"][champ] = {"type": "string", "enum": ["gerant", "admin"]}

    _modifier(copie, "utilisateur/suspendu.v1.json", ajouter)
    _refuse(copie, f"{champ} doit reprendre l'énumération role")


def test_contrat__exemple_au_format_invalide__refuse(copie: Path) -> None:
    def casser(schema: dict[str, Any]) -> None:
        schema["examples"][0]["utilisateur_id"] = "pas-un-uuid"

    _modifier(copie, "utilisateur/reactive.v1.json", casser)
    _refuse(copie, "exemple 0")


def test_contrat__montant_sans_motif_decimal__refuse(copie: Path) -> None:
    def retirer(schema: dict[str, Any]) -> None:
        del schema["properties"]["loyer_du"]["pattern"]

    _modifier(copie, "echeance/payee.v1.json", retirer)
    _refuse(copie, "loyer_du doit porter le motif décimal")


def test_contrat__montant_imbrique_en_nombre__refuse(copie: Path) -> None:
    def casser(schema: dict[str, Any]) -> None:
        schema["properties"]["paiements"]["items"]["properties"]["montant"] = {"type": "number"}

    _modifier(copie, "echeance/payee.v1.json", casser)
    _refuse(copie, "paiements[].montant doit être une chaîne décimale")


def test_contrat__id_ou_titre_sans_rapport_avec_le_chemin__refuse(copie: Path) -> None:
    def renommer(schema: dict[str, Any]) -> None:
        schema["title"] = "utilisateur.autre v1"

    _modifier(copie, "utilisateur/cree.v1.json", renommer)
    _refuse(copie, "title attendu « utilisateur.cree v1 »")


def test_contrat__evenement_non_declare_dans_consumers__refuse(copie: Path) -> None:
    consumers = copie / "consumers.yaml"
    consumers.write_text(consumers.read_text().replace("  utilisateur.reactive: [reporting]\n", ""))
    _refuse(copie, "utilisateur.reactive absent de consumers.yaml")


def test_contrat__evenement_declare_sous_un_autre_producteur__refuse(copie: Path) -> None:
    consumers = copie / "consumers.yaml"
    texte = consumers.read_text().replace("  utilisateur.reactive: [reporting]\n", "")
    texte = texte.replace("referentiel:\n", "referentiel:\n  utilisateur.reactive: [reporting]\n", 1)
    consumers.write_text(texte)
    _refuse(copie, "utilisateur.reactive déclaré sous referentiel, producteur attendu : identity")
