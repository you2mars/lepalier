#!/usr/bin/env python3
"""Vérifie que les specs exportées existent et que les identifiants APP-/TEC- cités dans le plan et les recettes y figurent."""
from __future__ import annotations
import re, sys
from pathlib import Path
docs = Path(__file__).resolve().parent.parent / "docs"
missing = [f for f in ("SPEC_FONCTIONNELLE.md", "SPEC_TECHNIQUE.md") if not (docs / f).exists()]
if missing:
    print("Specs manquantes dans docs/ (exporter les Claude Docs en Markdown) :", ", ".join(missing)); sys.exit(1)
corpus = (docs / "SPEC_FONCTIONNELLE.md").read_text() + (docs / "SPEC_TECHNIQUE.md").read_text()
ids = set()
for f in [docs / "PLAN_DE_DEV.md", *sorted((docs / "RECETTE").glob("lot-*.md"))]:
    ids |= set(re.findall(r"\b(?:APP|TEC)-[A-Z]+-\d{2}\b", f.read_text()))
absent = sorted(i for i in ids if i not in corpus)
if absent:
    print("Identifiants cités mais absents des specs :", ", ".join(absent)); sys.exit(1)
print(f"docs OK ({len(ids)} identifiants vérifiés)")
