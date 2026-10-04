#!/usr/bin/env python3
"""Valide les contrats d'événements (make contracts) : schémas, exemples, montants en chaîne, graphe sans cycle.

Dépendances : jsonschema, pyyaml (installées par `make doctor`).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

try:
    import yaml
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover
    print("pip install jsonschema pyyaml (ou make doctor)")
    sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent / "contracts"
CORE = {"facturation", "charges-eau", "documents", "envois"}
DECIMAL = re.compile(r"\\d\+\\\.\\d\{2\}")
errors: list[str] = []

env = json.loads((ROOT / "enveloppe.schema.json").read_text())
Draft202012Validator.check_schema(env)

for schema_path in sorted((ROOT / "events").glob("*/*.v*.json")):
    schema = json.loads(schema_path.read_text())
    try:
        Draft202012Validator.check_schema(schema)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"{schema_path}: schéma invalide: {exc}")
        continue
    if schema.get("additionalProperties") is not False:
        errors.append(f"{schema_path}: additionalProperties doit être false")
    validator = Draft202012Validator(schema)
    for i, ex in enumerate(schema.get("examples", [])):
        for err in validator.iter_errors(ex):
            errors.append(f"{schema_path}: exemple {i}: {err.message}")
    if not schema.get("examples"):
        errors.append(f"{schema_path}: au moins un exemple requis")
    # montants : toute propriété nommée *montant*, loyer*, charges*, total*, depot* doit être string + pattern
    def walk(props: dict, path: str = "") -> None:
        for name, prop in props.items():
            if re.search(r"(montant|loyer|charges|total|depot|rappel|cout|valeur)", name) and prop.get("type") not in ("string", ["string", "null"]):
                errors.append(f"{schema_path}: {path}{name} doit être une chaîne décimale")
            if "properties" in prop:
                walk(prop["properties"], f"{path}{name}.")
            if "items" in prop and isinstance(prop["items"], dict) and "properties" in prop["items"]:
                walk(prop["items"]["properties"], f"{path}{name}[].")
    walk(schema.get("properties", {}))

# graphe producteur -> consommateurs : pas de cycle entre les services du cœur
graph = yaml.safe_load((ROOT / "consumers.yaml").read_text()) or {}
edges: dict[str, set[str]] = {s: set() for s in graph}
ack_edges: list[tuple[str, str, str]] = []
for producer, events in graph.items():
    for event, spec in (events or {}).items():
        consumers = spec.get("consumers", []) if isinstance(spec, dict) else (spec or [])
        acks = spec.get("ack", []) if isinstance(spec, dict) else []
        for c in consumers:
            edges.setdefault(producer, set()).add(c)
        for a in acks:
            ack_edges.append((producer, event, a))
# une arête `ack` doit pointer vers un service qui est lui-même producteur amont du producteur courant
for producer, event, a in ack_edges:
    if producer not in edges.get(a, set()):
        errors.append(f"{producer}.{event}: ack vers {a} sans arête amont {a} -> {producer} (ce n'est pas un retour)")

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
                return stack[stack.index(m):] + [m]
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
