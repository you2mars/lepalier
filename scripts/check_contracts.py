#!/usr/bin/env python3
"""Valide les contrats d'événements (make contracts) : schémas, exemples, montants, données personnelles et
secrets, producteurs, graphe sans cycle.

Dépendances : jsonschema, pyyaml, rfc3339-validator (environnement de libs/commun, `make contracts`).
"""

from __future__ import annotations

import json
import os
import re
import sys
import unicodedata
from collections.abc import Iterator
from pathlib import Path
from typing import Any

try:
    import yaml
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover
    print("uv run --project libs/commun python scripts/check_contracts.py (ou make contracts)")
    sys.exit(2)

# CONTRATS_DIR ne sert qu'aux tests (copie temporaire de contracts/)
ROOT = Path(os.environ.get("CONTRATS_DIR") or Path(__file__).resolve().parent.parent / "contracts")
CORE = {"facturation", "charges-eau", "documents", "envois"}
# producteur de chaque agrégat (SYNTHESE_SPECS § 3)
PRODUCTEURS = {
    "utilisateur": "identity",
    "location": "referentiel",
    "locataire": "referentiel",
    "lot": "referentiel",
    "diagnostic": "referentiel",
    "cle": "referentiel",
    "demande": "referentiel",
    "echeance": "facturation",
    "paiement": "facturation",
    "revision": "facturation",
    "releve": "charges-eau",
    "facture": "charges-eau",
    "charge": "charges-eau",
    "regularisation": "charges-eau",
    "conso": "charges-eau",
    "document": "documents",
    "fichier": "documents",
    "envoi": "envois",
    "irl": "veille",
    "veille": "veille",
    "export": "reporting",
}
MONTANT = re.compile(r"(montant|loyer|charges|total|depot|rappel|cout|valeur)")
MOTIFS_DECIMAUX = {r"^\d+\.\d{2}$", r"^-?\d+\.\d{2}$"}
# utilisateur.* : jamais d'adresse e-mail ni de secret (ADR 0006). Correspondance sur les mots du nom de champ
# (minuscules, sans accents), pas sur une sous-chaîne : code_postal est accepté, email, mdp ou ip refusés.
MOTS_INTERDITS = {
    "email",
    "mail",
    "courriel",
    "mdp",
    "password",
    "passwd",
    "pwd",
    "totp",
    "otp",
    "secret",
    "secrets",
    "jeton",
    "jetons",
    "token",
    "tokens",
    "hash",
    "empreinte",
    "salt",
    "sel",
    "credential",
    "credentials",
    "recovery",
    "secours",
    "ip",
}
SUITES_INTERDITES = [
    ("mot", "de", "passe"),
    ("adresse", "electronique"),
    ("adresse", "mail"),
    ("user", "agent"),
    ("api", "key"),
    ("cle", "api"),
]
errors: list[str] = []
enums = json.loads((ROOT / "enums.json").read_text())


def mots(nom: str) -> list[str]:
    sans_accents = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode()
    return [
        m for m in re.split(r"[^a-z0-9]+", re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", sans_accents).lower()) if m
    ]


def interdit(nom: str) -> bool:
    liste = mots(nom)
    if MOTS_INTERDITS & set(liste):
        return True
    return any(liste[i : i + len(s)] == list(s) for s in SUITES_INTERDITES for i in range(len(liste)))


def proprietes(schema: dict[str, Any], chemin: str = "") -> Iterator[tuple[str, str, dict[str, Any]]]:
    """(nom, chemin, définition) de chaque propriété, imbriquées comprises (items, $defs, etc.)."""
    for cle in ("properties", "patternProperties", "$defs"):
        for nom, prop in (schema.get(cle) or {}).items():
            if isinstance(prop, dict):
                yield nom, f"{chemin}{nom}", prop
                yield from proprietes(prop, f"{chemin}{nom}.")
    for cle in ("items", "additionalProperties"):
        if isinstance(schema.get(cle), dict):
            yield from proprietes(schema[cle], f"{chemin.rstrip('.')}[]." if cle == "items" else chemin)


env = json.loads((ROOT / "enveloppe.schema.json").read_text())
Draft202012Validator.check_schema(env)

schemas: dict[str, Path] = {}
for schema_path in sorted((ROOT / "events").glob("*/*.v*.json")):
    agregat, fait, version = (
        schema_path.parent.name,
        schema_path.name.split(".v")[0],
        schema_path.name.split(".v")[1],
    )
    version = version.removesuffix(".json")
    schemas[f"{agregat}.{fait}"] = schema_path
    schema = json.loads(schema_path.read_text())
    try:
        Draft202012Validator.check_schema(schema)
    except Exception as exc:
        errors.append(f"{schema_path}: schéma invalide: {exc}")
        continue
    if schema.get("additionalProperties") is not False:
        errors.append(f"{schema_path}: additionalProperties doit être false")
    if not str(schema.get("$id", "")).endswith(f"/events/{agregat}/{fait}.v{version}.json"):
        errors.append(f"{schema_path}: $id ne correspond pas au chemin du fichier")
    if schema.get("title") != f"{agregat}.{fait} v{version}":
        errors.append(f"{schema_path}: title attendu « {agregat}.{fait} v{version} »")
    validator = Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)
    for i, ex in enumerate(schema.get("examples", [])):
        for err in validator.iter_errors(ex):
            errors.append(f"{schema_path}: exemple {i}: {err.message}")
    if not schema.get("examples"):
        errors.append(f"{schema_path}: au moins un exemple requis")
    for nom, chemin, prop in proprietes(schema):
        if MONTANT.search(nom) and "enum" not in prop:  # une énumération (mode_charges) n'est pas un montant
            if prop.get("type") not in ("string", ["string", "null"]):
                errors.append(f"{schema_path}: {chemin} doit être une chaîne décimale")
            elif prop.get("pattern") not in MOTIFS_DECIMAUX:
                errors.append(f"{schema_path}: {chemin} doit porter le motif décimal ^-?\\d+\\.\\d{{2}}$")
        if mots(nom)[-1:] == ["role"] and prop.get("enum") != enums["role"]:
            errors.append(f"{schema_path}: {chemin} doit reprendre l'énumération role de enums.json")
        if agregat == "utilisateur" and interdit(nom):
            errors.append(
                f"{schema_path}: {chemin} interdit dans utilisateur.* (ni e-mail ni secret, ADR 0006)"
            )

# graphe producteur -> consommateurs : pas de cycle entre les services du cœur
graph = yaml.safe_load((ROOT / "consumers.yaml").read_text()) or {}
edges: dict[str, set[str]] = {s: set() for s in graph}
ack_edges: list[tuple[str, str, str]] = []
producteur_de: dict[str, str] = {}
for producer, events in graph.items():
    for event, spec in (events or {}).items():
        if event in producteur_de:
            errors.append(f"{event} déclaré par {producteur_de[event]} et par {producer}")
        producteur_de[event] = producer
        attendu = PRODUCTEURS.get(event.split(".")[0])
        if attendu != producer:
            errors.append(
                f"{event} déclaré sous {producer}, producteur attendu : {attendu or 'agrégat inconnu'}"
            )
        consumers = spec.get("consumers", []) if isinstance(spec, dict) else (spec or [])
        acks = spec.get("ack", []) if isinstance(spec, dict) else []
        for c in consumers:
            edges.setdefault(producer, set()).add(c)
        for a in acks:
            ack_edges.append((producer, event, a))
# tout schéma d'événement est déclaré par son producteur dans consumers.yaml
for nom, schema_path in schemas.items():
    if nom not in producteur_de:
        errors.append(f"{schema_path}: {nom} absent de consumers.yaml")
# une arête `ack` doit pointer vers un service qui est lui-même producteur amont du producteur courant
for producer, event, a in ack_edges:
    if producer not in edges.get(a, set()):
        errors.append(
            f"{producer}.{event}: ack vers {a} sans arête amont {a} -> {producer} (ce n'est pas un retour)"
        )


def has_cycle(nodes: set[str]) -> list[str] | None:
    state: dict[str, int] = {}
    stack: list[str] = []

    def visit(n: str) -> list[str] | None:
        state[n] = 1
        stack.append(n)
        for m in edges.get(n, ()):
            if m not in nodes:
                continue
            if state.get(m) == 1:
                return [*stack[stack.index(m) :], m]
            if state.get(m) is None and (cyc := visit(m)):
                return cyc
        stack.pop()
        state[n] = 2
        return None

    for n in nodes:
        if state.get(n) is None and (cyc := visit(n)):
            return cyc
    return None


if cyc := has_cycle(CORE):
    errors.append("cycle entre services du cœur: " + " -> ".join(cyc))

if errors:
    print("\n".join(errors))
    sys.exit(1)
print("contrats OK")
