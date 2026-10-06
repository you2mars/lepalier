"""identity : utilisateurs, sessions, appareils, codes de secours, liens, tentatives de connexion

Révision : 0003
Précédente : 0002
Créée le : 2026-10-04

Schéma validé le 4 octobre 2026 (ADR 0006 et 0007). Jetons jamais stockés, seulement leur empreinte SHA-256 ;
secret TOTP chiffré (octet de version de clé en tête) ; e-mail pseudonymisé (HMAC) dans les tentatives.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

from migrations.droits import accorder

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TZ = pg.TIMESTAMP(timezone=True)
UUID = pg.UUID(as_uuid=True)
MOTIFS = "'deconnexion', 'rotation', 'essais_totp', 'suspension', 'reinitialisation', 'totp_reinitialise'"


def _lien(nom: str, *colonnes: sa.Column) -> None:  # type: ignore[type-arg]
    op.create_table(
        nom,
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "utilisateur_id",
            UUID,
            sa.ForeignKey("utilisateur.id", name=f"fk_{nom}_utilisateur"),
            nullable=False,
        ),
        sa.Column("empreinte", pg.BYTEA, nullable=False, unique=True),
        sa.Column("cree_le", TZ, nullable=False, server_default=sa.func.now()),
        sa.Column("expire_le", TZ, nullable=False),
        sa.Column("utilisee_le", TZ),
        sa.Column("invalidee_le", TZ),
        *colonnes,
        sa.CheckConstraint("octet_length(empreinte) = 32", name=f"ck_{nom}_empreinte"),
    )
    op.create_index(
        f"uq_{nom}_actif",
        nom,
        ["utilisateur_id"],
        unique=True,
        postgresql_where=sa.text("utilisee_le IS NULL AND invalidee_le IS NULL"),
    )


def upgrade() -> None:
    op.create_table(
        "utilisateur",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("email", sa.Text, nullable=False),
        sa.Column("nom_affiche", sa.Text, nullable=False),
        sa.Column("role", sa.Text, nullable=False),
        sa.Column("statut", sa.Text, nullable=False, server_default="invite"),
        sa.Column("associe_id", UUID),
        sa.Column("mot_de_passe_hache", sa.Text),
        sa.Column("mot_de_passe_change_le", TZ),
        sa.Column("totp_secret_chiffre", pg.BYTEA),
        sa.Column("totp_dernier_pas", sa.BigInteger),
        sa.Column("derniere_alerte_echecs_le", TZ),
        sa.Column("origine", sa.Text, nullable=False),
        sa.Column("invite_par", UUID, sa.ForeignKey("utilisateur.id", name="fk_utilisateur_invite_par")),
        sa.Column("cree_le", TZ, nullable=False, server_default=sa.func.now()),
        sa.Column("active_le", TZ),
        sa.Column("suspendu_le", TZ),
        sa.CheckConstraint("role IN ('gerant', 'associe', 'operateur')", name="ck_utilisateur_role"),
        sa.CheckConstraint("statut IN ('invite', 'actif', 'suspendu')", name="ck_utilisateur_statut"),
        sa.CheckConstraint("origine IN ('invitation', 'commande_locale')", name="ck_utilisateur_origine"),
        sa.CheckConstraint(
            "char_length(nom_affiche) BETWEEN 1 AND 60 AND nom_affiche !~ '@' "
            "AND nom_affiche ~ '[^[:space:]]'",
            name="ck_utilisateur_nom_affiche",
        ),
        sa.CheckConstraint(
            "statut <> 'actif' OR (mot_de_passe_hache IS NOT NULL AND totp_secret_chiffre IS NOT NULL)",
            name="ck_utilisateur_actif_complet",
        ),
        sa.CheckConstraint(
            "origine = 'commande_locale' OR invite_par IS NOT NULL", name="ck_utilisateur_invitant"
        ),
        sa.CheckConstraint(
            "totp_secret_chiffre IS NULL OR "
            "(octet_length(totp_secret_chiffre) >= 49 AND get_byte(totp_secret_chiffre, 0) >= 1)",
            name="ck_utilisateur_totp_secret_chiffre",
        ),
    )
    op.create_index("uq_utilisateur_email", "utilisateur", [sa.text("lower(email)")], unique=True)

    op.create_table(
        "appareil",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "utilisateur_id",
            UUID,
            sa.ForeignKey("utilisateur.id", name="fk_appareil_utilisateur"),
            nullable=False,
        ),
        sa.Column("empreinte", pg.BYTEA, nullable=False, unique=True),
        sa.Column("cree_le", TZ, nullable=False, server_default=sa.func.now()),
        sa.Column("vu_le", TZ, nullable=False, server_default=sa.func.now()),
        sa.Column("expire_le", TZ, nullable=False),
        sa.Column("revoque_le", TZ),
        sa.CheckConstraint("octet_length(empreinte) = 32", name="ck_appareil_empreinte"),
    )

    op.create_table(
        "session",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("empreinte", pg.BYTEA, nullable=False, unique=True),
        sa.Column(
            "utilisateur_id",
            UUID,
            sa.ForeignKey("utilisateur.id", name="fk_session_utilisateur"),
            nullable=False,
        ),
        sa.Column("etat", sa.Text, nullable=False),
        sa.Column("essais_totp", sa.SmallInteger, nullable=False, server_default="0"),
        sa.Column("cree_le", TZ, nullable=False, server_default=sa.func.now()),
        sa.Column("derniere_activite_le", TZ, nullable=False),
        sa.Column("expire_le", TZ, nullable=False),
        sa.Column("revoquee_le", TZ),
        sa.Column("motif_revocation", sa.Text),
        sa.Column("appareil_id", UUID, sa.ForeignKey("appareil.id", name="fk_session_appareil")),
        sa.Column("ip_creation", pg.INET),
        sa.CheckConstraint("octet_length(empreinte) = 32", name="ck_session_empreinte"),
        sa.CheckConstraint("etat IN ('pre_totp', 'active')", name="ck_session_etat"),
        sa.CheckConstraint("essais_totp >= 0", name="ck_session_essais_totp"),
        sa.CheckConstraint(
            f"motif_revocation IS NULL OR motif_revocation IN ({MOTIFS})", name="ck_session_motif_revocation"
        ),
        sa.CheckConstraint(
            "(revoquee_le IS NULL) = (motif_revocation IS NULL)", name="ck_session_revocation"
        ),
    )
    op.create_index(
        "ix_session_utilisateur_active",
        "session",
        ["utilisateur_id"],
        postgresql_where=sa.text("revoquee_le IS NULL"),
    )

    op.create_table(
        "code_secours",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "utilisateur_id",
            UUID,
            sa.ForeignKey("utilisateur.id", name="fk_code_secours_utilisateur"),
            nullable=False,
        ),
        sa.Column("empreinte", sa.Text, nullable=False),
        sa.Column("genere_le", TZ, nullable=False, server_default=sa.func.now()),
        sa.Column("utilise_le", TZ),
        sa.Column("invalide_le", TZ),
    )
    op.create_index(
        "ix_code_secours_disponibles",
        "code_secours",
        ["utilisateur_id"],
        postgresql_where=sa.text("utilise_le IS NULL AND invalide_le IS NULL"),
    )

    _lien(
        "invitation",
        sa.Column(
            "par_utilisateur_id", UUID, sa.ForeignKey("utilisateur.id", name="fk_invitation_par_utilisateur")
        ),
    )
    _lien("reinitialisation")
    op.create_index(
        "ix_reinitialisation_utilisateur_cree_le", "reinitialisation", ["utilisateur_id", "cree_le"]
    )

    op.create_table(
        "tentative_connexion",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("cree_le", TZ, nullable=False, server_default=sa.func.now()),
        sa.Column("cle_compte", pg.BYTEA, nullable=False),
        sa.Column(
            "utilisateur_id", UUID, sa.ForeignKey("utilisateur.id", name="fk_tentative_connexion_utilisateur")
        ),
        sa.Column("ip", pg.INET, nullable=False),
        sa.Column("etape", sa.Text, nullable=False),
        sa.Column("reussie", sa.Boolean, nullable=False),
        sa.CheckConstraint("octet_length(cle_compte) = 32", name="ck_tentative_connexion_cle_compte"),
        sa.CheckConstraint(
            "etape IN ('mot_de_passe', 'totp', 'secours')", name="ck_tentative_connexion_etape"
        ),
    )
    op.create_index(
        "ix_tentative_connexion_compte_ip", "tentative_connexion", ["cle_compte", "ip", "cree_le"]
    )
    op.create_index("ix_tentative_connexion_compte", "tentative_connexion", ["cle_compte", "cree_le"])

    # suppression logique seulement (TEC-DAT-02)
    accorder(
        ["utilisateur", "appareil", "code_secours", "invitation", "reinitialisation"], "sans_suppression"
    )
    # purges : sessions expirées (90 j, TEC-DAT-02), tentatives (30 j, données de sécurité avec IP)
    accorder(["session", "tentative_connexion"], "lecture_ecriture")


def downgrade() -> None:
    for table in (
        "tentative_connexion",
        "reinitialisation",
        "invitation",
        "code_secours",
        "session",
        "appareil",
        "utilisateur",
    ):
        op.drop_table(table)
