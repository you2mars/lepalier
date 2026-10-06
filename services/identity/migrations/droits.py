"""Droits du rôle applicatif, accordés table par table dans les migrations (TEC-DAT-03)."""

from __future__ import annotations

import re
from typing import Literal

from alembic import context, op

_IDENTIFIANT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")
PRIVILEGES = {
    "lecture_ecriture": "SELECT, INSERT, UPDATE, DELETE",
    # suppression logique seulement (TEC-DAT-02) : pas de DELETE pour le rôle applicatif
    "sans_suppression": "SELECT, INSERT, UPDATE",
    # tables immuables (journal) : jamais UPDATE ni DELETE pour le rôle applicatif
    "ajout_seul": "SELECT, INSERT",
}


def accorder(
    tables: list[str], niveau: Literal["lecture_ecriture", "sans_suppression", "ajout_seul"]
) -> None:
    role = context.config.attributes["role_applicatif"]
    for nom in [role, *tables]:
        if not _IDENTIFIANT.fullmatch(nom):
            raise ValueError(f"identifiant SQL refusé : {nom!r}")
    liste = ", ".join(f'"{t}"' for t in tables)
    op.execute(f'GRANT {PRIVILEGES[niveau]} ON {liste} TO "{role}"')
