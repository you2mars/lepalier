"""identity : nom affiché sans caractère de contrôle

Révision : 0005
Précédente : 0004
Créée le : 2026-10-04

Un retour à la ligne dans le nom affiché pourrait injecter des lignes dans les e-mails envoyés aux gérants ;
une marque de sens d'écriture pourrait en retourner l'affichage. Refusés : contrôles C0 et C1, séparateurs
de ligne et de paragraphe (U+2028, U+2029), marques de sens d'écriture (U+202A à U+202E, U+2066 à U+2069).
Contrainte ajoutée sans toucher à 0003 ; l'octet nul est déjà refusé par PostgreSQL dans un texte.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_utilisateur_nom_affiche_sans_controle",
        "utilisateur",
        r"nom_affiche !~ '[\x01-\x1f\x7f-\x9f\u2028-\u202e\u2066-\u2069]'",
    )


def downgrade() -> None:
    op.drop_constraint("ck_utilisateur_nom_affiche_sans_controle", "utilisateur", type_="check")
