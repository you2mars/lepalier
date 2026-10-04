"""Tables d'identity (schéma validé le 4 octobre 2026, ADR 0006 et 0007).

Les jetons (session, appareil, liens) ne sont jamais stockés : seule leur empreinte SHA-256 l'est. Le secret
TOTP est chiffré (version de clé, nonce, texte chiffré, étiquette) ; l'e-mail d'un compte n'apparaît dans les
tentatives que sous forme de HMAC (clé de pseudonymisation).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    SmallInteger,
    Table,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import BYTEA, INET, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.models.socle import METADATA

TZ = TIMESTAMP(timezone=True)


def _uuid() -> PG_UUID[uuid.UUID]:
    return PG_UUID(as_uuid=True)


def _empreinte(nom: str, table: str) -> CheckConstraint:
    return CheckConstraint(f"octet_length({nom}) = 32", name=f"ck_{table}_{nom}")


UTILISATEUR = Table(
    "utilisateur",
    METADATA,
    Column("id", _uuid(), primary_key=True),
    Column("email", Text, nullable=False),
    Column("nom_affiche", Text, nullable=False),
    Column("role", Text, nullable=False),
    Column("statut", Text, nullable=False, server_default="invite"),
    Column("associe_id", _uuid()),
    Column("mot_de_passe_hache", Text),
    Column("mot_de_passe_change_le", TZ),
    Column("totp_secret_chiffre", BYTEA),
    Column("totp_dernier_pas", BigInteger),
    Column("derniere_alerte_echecs_le", TZ),
    # alerte « connexion d'un compte suspendu » : au plus une par compte et par heure (0004)
    Column("derniere_alerte_suspension_le", TZ),
    Column("origine", Text, nullable=False),
    Column("invite_par", _uuid(), ForeignKey("utilisateur.id", name="fk_utilisateur_invite_par")),
    Column("cree_le", TZ, nullable=False, server_default=func.now()),
    Column("active_le", TZ),
    Column("suspendu_le", TZ),
    CheckConstraint("role IN ('gerant', 'associe', 'operateur')", name="ck_utilisateur_role"),
    CheckConstraint("statut IN ('invite', 'actif', 'suspendu')", name="ck_utilisateur_statut"),
    CheckConstraint("origine IN ('invitation', 'commande_locale')", name="ck_utilisateur_origine"),
    CheckConstraint(
        "char_length(nom_affiche) BETWEEN 1 AND 60 AND nom_affiche !~ '@' AND nom_affiche ~ '[^[:space:]]'",
        name="ck_utilisateur_nom_affiche",
    ),
    CheckConstraint(
        "statut <> 'actif' OR (mot_de_passe_hache IS NOT NULL AND totp_secret_chiffre IS NOT NULL)",
        name="ck_utilisateur_actif_complet",
    ),
    CheckConstraint("origine = 'commande_locale' OR invite_par IS NOT NULL", name="ck_utilisateur_invitant"),
    CheckConstraint(
        "totp_secret_chiffre IS NULL OR "
        "(octet_length(totp_secret_chiffre) >= 49 AND get_byte(totp_secret_chiffre, 0) >= 1)",
        name="ck_utilisateur_totp_secret_chiffre",
    ),
)
Index("uq_utilisateur_email", func.lower(UTILISATEUR.c.email), unique=True)

APPAREIL = Table(
    "appareil",
    METADATA,
    Column("id", _uuid(), primary_key=True),
    Column(
        "utilisateur_id",
        _uuid(),
        ForeignKey("utilisateur.id", name="fk_appareil_utilisateur"),
        nullable=False,
    ),
    Column("empreinte", BYTEA, nullable=False, unique=True),
    Column("cree_le", TZ, nullable=False, server_default=func.now()),
    Column("vu_le", TZ, nullable=False, server_default=func.now()),
    Column("expire_le", TZ, nullable=False),
    Column("revoque_le", TZ),
    _empreinte("empreinte", "appareil"),
)

MOTIFS_REVOCATION = (
    "deconnexion",
    "rotation",
    "essais_totp",
    "suspension",
    "reinitialisation",
    "totp_reinitialise",
)

SESSION = Table(
    "session",
    METADATA,
    Column("id", _uuid(), primary_key=True),
    Column("empreinte", BYTEA, nullable=False, unique=True),
    Column(
        "utilisateur_id", _uuid(), ForeignKey("utilisateur.id", name="fk_session_utilisateur"), nullable=False
    ),
    Column("etat", Text, nullable=False),
    Column("essais_totp", SmallInteger, nullable=False, server_default="0"),
    Column("cree_le", TZ, nullable=False, server_default=func.now()),
    Column("derniere_activite_le", TZ, nullable=False),
    Column("expire_le", TZ, nullable=False),
    Column("revoquee_le", TZ),
    Column("motif_revocation", Text),
    Column("appareil_id", _uuid(), ForeignKey("appareil.id", name="fk_session_appareil")),
    Column("ip_creation", INET),
    _empreinte("empreinte", "session"),
    CheckConstraint("etat IN ('pre_totp', 'active')", name="ck_session_etat"),
    CheckConstraint("essais_totp >= 0", name="ck_session_essais_totp"),
    CheckConstraint(
        "motif_revocation IS NULL OR motif_revocation IN ("
        + ", ".join(f"'{m}'" for m in MOTIFS_REVOCATION)
        + ")",
        name="ck_session_motif_revocation",
    ),
    CheckConstraint("(revoquee_le IS NULL) = (motif_revocation IS NULL)", name="ck_session_revocation"),
)
Index(
    "ix_session_utilisateur_active",
    SESSION.c.utilisateur_id,
    postgresql_where=SESSION.c.revoquee_le.is_(None),
)

CODE_SECOURS = Table(
    "code_secours",
    METADATA,
    Column("id", _uuid(), primary_key=True),
    Column(
        "utilisateur_id",
        _uuid(),
        ForeignKey("utilisateur.id", name="fk_code_secours_utilisateur"),
        nullable=False,
    ),
    Column("empreinte", Text, nullable=False),
    Column("genere_le", TZ, nullable=False, server_default=func.now()),
    Column("utilise_le", TZ),
    Column("invalide_le", TZ),
)
Index(
    "ix_code_secours_disponibles",
    CODE_SECOURS.c.utilisateur_id,
    postgresql_where=text("utilise_le IS NULL AND invalide_le IS NULL"),
)


def _lien(nom: str, *colonnes: Column[Any] | CheckConstraint) -> Table:
    table = Table(
        nom,
        METADATA,
        Column("id", _uuid(), primary_key=True),
        Column(
            "utilisateur_id",
            _uuid(),
            ForeignKey("utilisateur.id", name=f"fk_{nom}_utilisateur"),
            nullable=False,
        ),
        Column("empreinte", BYTEA, nullable=False, unique=True),
        Column("cree_le", TZ, nullable=False, server_default=func.now()),
        Column("expire_le", TZ, nullable=False),
        Column("utilisee_le", TZ),
        Column("invalidee_le", TZ),
        *colonnes,
        _empreinte("empreinte", nom),
    )
    # un seul lien actif par utilisateur : un renvoi ou une nouvelle demande invalide le précédent
    Index(
        f"uq_{nom}_actif",
        table.c.utilisateur_id,
        unique=True,
        postgresql_where=text("utilisee_le IS NULL AND invalidee_le IS NULL"),
    )
    return table


INVITATION = _lien(
    "invitation",
    Column("par_utilisateur_id", _uuid(), ForeignKey("utilisateur.id", name="fk_invitation_par_utilisateur")),
)
REINITIALISATION = _lien(
    "reinitialisation",
    # 5 codes faux (TOTP ou secours) invalident le lien (0004)
    Column("essais_code", SmallInteger, nullable=False, server_default="0"),
    CheckConstraint("essais_code >= 0", name="ck_reinitialisation_essais_code"),
)
# au plus 3 demandes par heure et par compte
Index(
    "ix_reinitialisation_utilisateur_cree_le", REINITIALISATION.c.utilisateur_id, REINITIALISATION.c.cree_le
)

TENTATIVE_CONNEXION = Table(
    "tentative_connexion",
    METADATA,
    Column("id", _uuid(), primary_key=True),
    Column("cree_le", TZ, nullable=False, server_default=func.now()),
    Column("cle_compte", BYTEA, nullable=False),
    Column(
        "utilisateur_id", _uuid(), ForeignKey("utilisateur.id", name="fk_tentative_connexion_utilisateur")
    ),
    Column("ip", INET, nullable=False),
    Column("etape", Text, nullable=False),
    Column("reussie", Boolean, nullable=False),
    _empreinte("cle_compte", "tentative_connexion"),
    CheckConstraint("etape IN ('mot_de_passe', 'totp', 'secours')", name="ck_tentative_connexion_etape"),
)
# verrou par couple (compte, IP) ; seuil d'alerte par compte
Index(
    "ix_tentative_connexion_compte_ip",
    TENTATIVE_CONNEXION.c.cle_compte,
    TENTATIVE_CONNEXION.c.ip,
    TENTATIVE_CONNEXION.c.cree_le,
)
Index("ix_tentative_connexion_compte", TENTATIVE_CONNEXION.c.cle_compte, TENTATIVE_CONNEXION.c.cree_le)
