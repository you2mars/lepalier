"""Migration 0003_identity : contraintes et droits du rôle applicatif svc_identity (schéma du 4 octobre 2026).

Écrits en SQL brut, indépendamment des modèles, pour vérifier ce que la base garantit elle-même.
"""

from __future__ import annotations

import os
import uuid
from typing import Any

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import DBAPIError, IntegrityError, ProgrammingError
from sqlalchemy.orm import Session, sessionmaker

from commun.ids import uuid7

from .conftest import BaseEssai

pytestmark = pytest.mark.integration

TABLES_IDENTITY = {
    "utilisateur",
    "session",
    "appareil",
    "code_secours",
    "invitation",
    "reinitialisation",
    "tentative_connexion",
}
EMPREINTE = b"\x01" * 32
# version de clé (1) + nonce (12) + secret TOTP de 20 octets chiffré + étiquette GCM (16)
SECRET_TOTP = b"\x01" + os.urandom(12 + 20 + 16)
MDP = "$argon2id$v=19$m=19456,t=2,p=1$c2VsLWRlLXRlc3Q$ZW1wcmVpbnRlLWRlLXRlc3QtcG91ci1sZXMtdGVzdHM"


def _inserer(s: Session, table: str, **valeurs: Any) -> None:
    colonnes = ", ".join(valeurs)
    parametres = ", ".join(f":{c}" for c in valeurs)
    s.execute(text(f"INSERT INTO {table} ({colonnes}) VALUES ({parametres})"), valeurs)


def _utilisateur(s: Session, **valeurs: Any) -> uuid.UUID:
    ligne: dict[str, Any] = {
        "id": uuid7(),
        "email": f"{uuid7().hex}@essai.local",
        "nom_affiche": "Mme Durand",
        "role": "associe",
        "origine": "commande_locale",
    }
    ligne.update(valeurs)
    _inserer(s, "utilisateur", **ligne)
    return ligne["id"]  # type: ignore[no-any-return]


def _ecrire(fabrique: sessionmaker[Session], fonction: Any) -> None:
    with fabrique() as s, s.begin():
        fonction(s)


def _refuse(fabrique: sessionmaker[Session], fonction: Any, erreur: type[Exception] = IntegrityError) -> None:
    with pytest.raises(erreur):
        _ecrire(fabrique, fonction)


def test_migration_identity__tables_creees(base: BaseEssai) -> None:
    moteur = create_engine(base.url_proprietaire)
    assert TABLES_IDENTITY <= set(inspect(moteur).get_table_names())
    moteur.dispose()


# --- utilisateur ----------------------------------------------------------------------------------


def test_utilisateur__email_unique_insensible_a_la_casse(fabrique: sessionmaker[Session]) -> None:
    _ecrire(fabrique, lambda s: _utilisateur(s, email="Associe@Essai.local"))
    _refuse(fabrique, lambda s: _utilisateur(s, email="associe@essai.LOCAL"))


@pytest.mark.parametrize("nom", ["", "   ", "\t", "jean@exemple.fr", "x" * 61])
def test_utilisateur__nom_affiche_invalide__refuse_par_la_base(
    fabrique: sessionmaker[Session], nom: str
) -> None:
    _refuse(fabrique, lambda s: _utilisateur(s, nom_affiche=nom))


@pytest.mark.parametrize("valeurs", [{"role": "admin"}, {"statut": "supprime"}, {"origine": "import"}])
def test_utilisateur__valeur_hors_liste__refusee(
    fabrique: sessionmaker[Session], valeurs: dict[str, str]
) -> None:
    _refuse(fabrique, lambda s: _utilisateur(s, **valeurs))


def test_utilisateur__statut_invite_par_defaut(fabrique: sessionmaker[Session]) -> None:
    def creer(s: Session) -> None:
        uid = _utilisateur(s)
        assert s.scalar(text("SELECT statut FROM utilisateur WHERE id = :id"), {"id": uid}) == "invite"

    _ecrire(fabrique, creer)


@pytest.mark.parametrize(
    "valeurs",
    [{}, {"mot_de_passe_hache": MDP}, {"totp_secret_chiffre": SECRET_TOTP}],
)
def test_utilisateur__actif_sans_mot_de_passe_ou_totp__refuse(
    fabrique: sessionmaker[Session], valeurs: dict[str, Any]
) -> None:
    _refuse(fabrique, lambda s: _utilisateur(s, statut="actif", **valeurs))


def test_utilisateur__actif_avec_mot_de_passe_et_totp__accepte(fabrique: sessionmaker[Session]) -> None:
    _ecrire(
        fabrique,
        lambda s: _utilisateur(s, statut="actif", mot_de_passe_hache=MDP, totp_secret_chiffre=SECRET_TOTP),
    )


@pytest.mark.parametrize("secret", [b"\x01" * 10, b"\x00" + os.urandom(48)])
def test_utilisateur__secret_totp_trop_court_ou_sans_version__refuse(
    fabrique: sessionmaker[Session], secret: bytes
) -> None:
    _refuse(fabrique, lambda s: _utilisateur(s, totp_secret_chiffre=secret))


def test_utilisateur__origine_invitation_sans_invitant__refusee(fabrique: sessionmaker[Session]) -> None:
    _refuse(fabrique, lambda s: _utilisateur(s, origine="invitation"))


def test_utilisateur__origine_invitation_avec_invitant__acceptee(fabrique: sessionmaker[Session]) -> None:
    def creer(s: Session) -> None:
        gerant = _utilisateur(s, role="gerant")
        _utilisateur(s, origine="invitation", invite_par=gerant)

    _ecrire(fabrique, creer)


def test_utilisateur__invitant_inconnu__refuse(fabrique: sessionmaker[Session]) -> None:
    _refuse(fabrique, lambda s: _utilisateur(s, origine="invitation", invite_par=uuid7()))


# --- liens, sessions, appareils, tentatives -------------------------------------------------------


@pytest.mark.parametrize("table", ["invitation", "reinitialisation"])
def test_lien__un_seul_actif_par_utilisateur(fabrique: sessionmaker[Session], table: str) -> None:
    ids: dict[str, uuid.UUID] = {}

    def preparer(s: Session) -> None:
        ids["u"] = _utilisateur(s)
        _inserer(
            s, table, id=uuid7(), utilisateur_id=ids["u"], empreinte=os.urandom(32), expire_le="2099-01-01"
        )

    _ecrire(fabrique, preparer)

    def second(s: Session) -> None:
        _inserer(
            s, table, id=uuid7(), utilisateur_id=ids["u"], empreinte=os.urandom(32), expire_le="2099-01-01"
        )

    _refuse(fabrique, second)
    _ecrire(fabrique, lambda s: s.execute(text(f"UPDATE {table} SET invalidee_le = now()")))
    _ecrire(fabrique, second)


@pytest.mark.parametrize("table", ["session", "appareil", "invitation", "reinitialisation"])
def test_empreinte__32_octets_et_unique(fabrique: sessionmaker[Session], table: str) -> None:
    ids: dict[str, uuid.UUID] = {}
    extra = {"etat": "active", "derniere_activite_le": "2026-10-04"} if table == "session" else {}

    def creer(s: Session, empreinte: bytes, nouvel_utilisateur: bool = True) -> None:
        if nouvel_utilisateur:
            ids["u"] = _utilisateur(s)
        _inserer(
            s,
            table,
            id=uuid7(),
            utilisateur_id=ids["u"],
            empreinte=empreinte,
            expire_le="2099-01-01",
            **extra,
        )

    _refuse(fabrique, lambda s: creer(s, b"court"))
    _ecrire(fabrique, lambda s: creer(s, EMPREINTE))
    _refuse(fabrique, lambda s: creer(s, EMPREINTE))


@pytest.mark.parametrize(
    "valeurs",
    [{"etat": "inconnu"}, {"etat": "active", "motif_revocation": "autre", "revoquee_le": "2026-10-04"}],
)
def test_session__etat_ou_motif_hors_liste__refuse(
    fabrique: sessionmaker[Session], valeurs: dict[str, str]
) -> None:
    def creer(s: Session) -> None:
        uid = _utilisateur(s)
        _inserer(
            s,
            "session",
            **{
                "id": uuid7(),
                "utilisateur_id": uid,
                "empreinte": os.urandom(32),
                "derniere_activite_le": "2026-10-04",
                "expire_le": "2099-01-01",
                **valeurs,
            },
        )

    _refuse(fabrique, creer)


def test_session__utilisateur_inconnu__refuse(fabrique: sessionmaker[Session]) -> None:
    _refuse(
        fabrique,
        lambda s: _inserer(
            s,
            "session",
            id=uuid7(),
            utilisateur_id=uuid7(),
            empreinte=os.urandom(32),
            etat="pre_totp",
            derniere_activite_le="2026-10-04",
            expire_le="2099-01-01",
        ),
    )


@pytest.mark.parametrize("valeurs", [{"etape": "sms"}, {"cle_compte": b"court"}])
def test_tentative_connexion__valeur_invalide__refusee(
    fabrique: sessionmaker[Session], valeurs: dict[str, Any]
) -> None:
    ligne = {
        "id": uuid7(),
        "cle_compte": EMPREINTE,
        "ip": "192.168.1.20",
        "etape": "mot_de_passe",
        "reussie": False,
    }
    _refuse(fabrique, lambda s: _inserer(s, "tentative_connexion", **{**ligne, **valeurs}))


# --- droits du rôle applicatif (TEC-DAT-02, TEC-DAT-03) --------------------------------------------


@pytest.mark.parametrize(
    "table", ["utilisateur", "code_secours", "invitation", "reinitialisation", "appareil"]
)
def test_droits__svc_identity__pas_de_delete(fabrique: sessionmaker[Session], table: str) -> None:
    _refuse(fabrique, lambda s: s.execute(text(f"DELETE FROM {table}")), ProgrammingError)


@pytest.mark.parametrize("table", ["session", "tentative_connexion", "idempotence"])
def test_droits__svc_identity__delete_permis_pour_les_purges(
    fabrique: sessionmaker[Session], table: str
) -> None:
    _ecrire(fabrique, lambda s: s.execute(text(f"DELETE FROM {table}")))


def test_droits__svc_identity__lecture_ecriture_sans_suppression_sur_les_codes(
    fabrique: sessionmaker[Session],
) -> None:
    def creer(s: Session) -> None:
        uid = _utilisateur(s)
        code = uuid7()
        _inserer(s, "code_secours", id=code, utilisateur_id=uid, empreinte=MDP)
        s.execute(text("UPDATE code_secours SET utilise_le = now() WHERE id = :id"), {"id": code})

    _ecrire(fabrique, creer)


# --- 0004 : compteur de codes sur les liens de réinitialisation, alerte « compte suspendu » -----------


def _reinitialisation(s: Session, **valeurs: Any) -> uuid.UUID:
    ligne: dict[str, Any] = {
        "id": uuid7(),
        "utilisateur_id": _utilisateur(s),
        "empreinte": os.urandom(32),
        "expire_le": "2099-01-01",
    }
    ligne.update(valeurs)
    _inserer(s, "reinitialisation", **ligne)
    return ligne["id"]  # type: ignore[no-any-return]


def test_reinitialisation__essais_code_zero_par_defaut(fabrique: sessionmaker[Session]) -> None:
    def creer(s: Session) -> None:
        lien = _reinitialisation(s)
        assert s.scalar(text("SELECT essais_code FROM reinitialisation WHERE id = :id"), {"id": lien}) == 0

    _ecrire(fabrique, creer)


@pytest.mark.parametrize("valeur", [-1, None])
def test_reinitialisation__essais_code_negatif_ou_nul__refuse(
    fabrique: sessionmaker[Session], valeur: int | None
) -> None:
    _refuse(fabrique, lambda s: _reinitialisation(s, essais_code=valeur))


def test_utilisateur__derniere_alerte_suspension_nulle_par_defaut(fabrique: sessionmaker[Session]) -> None:
    def creer(s: Session) -> None:
        uid = _utilisateur(s)
        valeur = s.scalar(
            text("SELECT derniere_alerte_suspension_le FROM utilisateur WHERE id = :id"), {"id": uid}
        )
        assert valeur is None

    _ecrire(fabrique, creer)


def test_droits__svc_identity__ecrit_essais_code_et_derniere_alerte_suspension(
    fabrique: sessionmaker[Session],
) -> None:
    def ecrire(s: Session) -> None:
        lien = _reinitialisation(s)
        s.execute(
            text("UPDATE reinitialisation SET essais_code = essais_code + 1 WHERE id = :id"), {"id": lien}
        )
        s.execute(text("UPDATE utilisateur SET derniere_alerte_suspension_le = now()"))
        assert s.scalar(text("SELECT essais_code FROM reinitialisation WHERE id = :id"), {"id": lien}) == 1

    _ecrire(fabrique, ecrire)


# --- 0005 : nom affiché sans caractère de contrôle (injection de lignes dans les e-mails) -------------


@pytest.mark.parametrize(
    "nom",
    [
        "Mme Durand\nObjet : faux",
        "Mme\rDurand",
        "Mme\tDurand",
        "Mme\x1fDurand",
        "Mme\x7fDurand",
        "Mme\x80Durand",
        "Mme\x85Durand",
        "Mme\x9fDurand",
        "Mme\u2028Durand",
        "Mme\u2029Durand",
        "\u202aMme Durand",
        "Mme \u202eDurand",
        "\u2066Mme Durand",
        "Mme Durand\u2069",
    ],
)
def test_utilisateur__nom_affiche_avec_caractere_de_controle__refuse_par_la_base(
    fabrique: sessionmaker[Session], nom: str
) -> None:
    _refuse(fabrique, lambda s: _utilisateur(s, nom_affiche=nom))


def test_utilisateur__nom_affiche_avec_octet_nul__refuse_par_postgresql(
    fabrique: sessionmaker[Session],
) -> None:
    _refuse(fabrique, lambda s: _utilisateur(s, nom_affiche="Mme\x00Durand"), DBAPIError)


@pytest.mark.parametrize(
    "nom",
    [
        "Mme Durand",
        "Jean-Pierre O'Neil",
        "Élodie Gérante",
        "D'Aragon Ç",
        "Mme\xa0Durand",
        "Mme\u202fDurand",
        "Mme\u2070",
    ],
)
def test_utilisateur__nom_affiche_ordinaire__accepte(fabrique: sessionmaker[Session], nom: str) -> None:
    _ecrire(fabrique, lambda s: _utilisateur(s, nom_affiche=nom))


# --- 0006 : invitation annulée (statut annule, adresse réutilisable) ----------------------------------


def test_utilisateur__statut_annule_accepte(fabrique: sessionmaker[Session]) -> None:
    _ecrire(fabrique, lambda s: _utilisateur(s, statut="annule"))


def test_utilisateur__adresse_d_une_invitation_annulee_reutilisable(fabrique: sessionmaker[Session]) -> None:
    _ecrire(fabrique, lambda s: _utilisateur(s, email="durand@essai.local", statut="annule"))
    _ecrire(fabrique, lambda s: _utilisateur(s, email="Durand@essai.local", statut="annule"))
    _ecrire(fabrique, lambda s: _utilisateur(s, email="DURAND@essai.local"))
    _refuse(fabrique, lambda s: _utilisateur(s, email="durand@ESSAI.local"))
