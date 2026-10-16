"""identity : invitation annulée (statut annule), adresse réutilisable

Révision : 0006
Précédente : 0005
Créée le : 2026-10-06

Un gérant peut annuler une invitation envoyée par erreur : le compte invité passe au statut `annule`, jamais
supprimé (suppression logique). L'unicité de l'adresse (sans tenir compte de la casse) ne vaut plus que pour
les comptes non annulés, pour que la même adresse puisse être invitée de nouveau. Contrainte et index
remplacés sans perte de données (aucun compte n'a encore le statut annule).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_utilisateur_statut", "utilisateur", type_="check")
    op.create_check_constraint(
        "ck_utilisateur_statut", "utilisateur", "statut IN ('invite', 'actif', 'suspendu', 'annule')"
    )
    op.drop_index("uq_utilisateur_email", table_name="utilisateur")
    op.create_index(
        "uq_utilisateur_email",
        "utilisateur",
        [sa.text("lower(email)")],
        unique=True,
        postgresql_where=sa.text("statut <> 'annule'"),
    )


def downgrade() -> None:
    # refusé tant qu'un compte a le statut annule (la contrainte d'origine ne l'accepte pas)
    op.drop_index("uq_utilisateur_email", table_name="utilisateur")
    op.create_index("uq_utilisateur_email", "utilisateur", [sa.text("lower(email)")], unique=True)
    op.drop_constraint("ck_utilisateur_statut", "utilisateur", type_="check")
    op.create_check_constraint(
        "ck_utilisateur_statut", "utilisateur", "statut IN ('invite', 'actif', 'suspendu')"
    )
