from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from commun.ids import uuid7
from commun.journal import Journal

from .conftest import JOURNAL

pytestmark = pytest.mark.integration

JOURNAL_SVC = Journal(JOURNAL)


def test_ecrire__ligne_complete_avec_montants_en_chaine(fabrique: sessionmaker[Session]) -> None:
    utilisateur, enregistrement = uuid7(), uuid7()
    with fabrique() as s, s.begin():
        JOURNAL_SVC.ecrire(
            s,
            action="paiement.saisi",
            table_cible="paiement",
            enregistrement_id=enregistrement,
            utilisateur_id=utilisateur,
            avant=None,
            apres={"montant": Decimal("650.00"), "le": "2026-11-03"},
            ip="192.168.1.20",
        )
    with fabrique() as s:
        ligne = s.execute(select(JOURNAL)).mappings().one()
    assert ligne["id"].version == 7
    assert ligne["utilisateur_id"] == utilisateur
    assert (ligne["action"], ligne["table_cible"], ligne["enregistrement_id"]) == (
        "paiement.saisi",
        "paiement",
        enregistrement,
    )
    assert ligne["avant"] is None
    assert ligne["apres"] == {"montant": "650.00", "le": "2026-11-03"}
    assert str(ligne["ip"]) == "192.168.1.20"
    assert len(ligne["trace_id"]) == 32
    assert ligne["horodatage"].tzinfo is not None


def test_ecrire__action_systeme_sans_utilisateur(fabrique: sessionmaker[Session]) -> None:
    with fabrique() as s, s.begin():
        JOURNAL_SVC.ecrire(s, action="job.echec", table_cible="job", enregistrement_id=uuid7())
    with fabrique() as s:
        assert s.execute(select(JOURNAL.c.utilisateur_id)).scalar_one() is None


def test_ecrire__dans_une_transaction_annulee__rien(fabrique: sessionmaker[Session]) -> None:
    with pytest.raises(RuntimeError), fabrique() as s, s.begin():
        JOURNAL_SVC.ecrire(s, action="x.y", table_cible="x", enregistrement_id=uuid7())
        raise RuntimeError("annulation")
    with fabrique() as s:
        assert s.execute(select(JOURNAL)).first() is None


def test_ecrire__flottant_refuse(fabrique: sessionmaker[Session]) -> None:
    with pytest.raises(ValueError, match="flottant"), fabrique() as s, s.begin():
        JOURNAL_SVC.ecrire(
            s, action="x.y", table_cible="x", enregistrement_id=uuid7(), apres={"montant": 1.5}
        )
