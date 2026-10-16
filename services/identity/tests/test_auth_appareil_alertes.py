"""Section B : nouvel appareil et alertes (liste validée le 4 octobre 2026)."""

from __future__ import annotations

import threading
from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, insert, select, update
from sqlalchemy.orm import Session, sessionmaker

from app.courriels.textes import alerte_compte_suspendu, alerte_echecs, nouvel_appareil
from app.engines.chiffrement import pseudonymiser
from app.models import APPAREIL, JOB, TENTATIVE_CONNEXION, UTILISATEUR
from commun.ids import uuid7

from .aides import (
    CLES,
    MOT_DE_PASSE,
    Compte,
    ExpediteurMemoire,
    client,
    creer_compte,
    executer_jobs,
    lignes,
    valeur,
)

pytestmark = pytest.mark.integration


def _jobs(fabrique: sessionmaker[Session], type_: str) -> list[dict[str, object]]:
    return lignes(fabrique, JOB, JOB.c.type == type_)


def _connexion_complete(c: TestClient, compte: Compte, decalage: int = 0) -> Any:
    assert (
        c.post("/auth/connexion", json={"email": compte.email, "mot_de_passe": MOT_DE_PASSE}).status_code
        == 200
    )
    return c.post("/auth/code", json={"code": compte.code_totp(decalage)})


# --- nouvel appareil (TEC-SEC-19) -----------------------------------------------------------------


def test_appareil__connexion_complete_sans_cookie__email_info_et_cookie_1_an(
    fabrique: sessionmaker[Session],
) -> None:
    compte = creer_compte(fabrique)
    c = client(fabrique)
    assert _connexion_complete(c, compte).status_code == 200
    (appareil,) = lignes(fabrique, APPAREIL, APPAREIL.c.utilisateur_id == compte.id)
    assert appareil["expire_le"] - appareil["cree_le"] == timedelta(days=365)  # type: ignore[operator]
    (job,) = _jobs(fabrique, "courriel.nouvel_appareil")
    assert job["payload"] == {"utilisateur_id": str(compte.id), "appareil_id": str(appareil["id"])}
    expediteur = ExpediteurMemoire()
    assert executer_jobs(fabrique, expediteur) == ["termine"]
    assert expediteur.envoyes == [
        (compte.email, nouvel_appareil("Mme Durand", appareil["cree_le"], "associe"))
    ]  # type: ignore[arg-type]


@pytest.mark.parametrize(("role", "nom"), [("gerant", "M. Martin"), ("operateur", "Mme Durand")])
def test_appareil__email_selon_le_role__prevenir_le_gerant_sauf_s_il_est_le_destinataire(
    fabrique: sessionmaker[Session], role: str, nom: str
) -> None:
    compte = creer_compte(fabrique, role=role, nom_affiche=nom)
    assert _connexion_complete(client(fabrique), compte).status_code == 200
    expediteur = ExpediteurMemoire()
    executer_jobs(fabrique, expediteur)
    ((_, courriel),) = expediteur.envoyes
    (appareil,) = lignes(fabrique, APPAREIL, APPAREIL.c.utilisateur_id == compte.id)
    assert courriel == nouvel_appareil(nom, appareil["cree_le"], role)  # type: ignore[arg-type]
    assert courriel.corps.endswith(
        "sur la page de connexion."
        if role == "gerant"
        else "sur la page de connexion, puis prévenez le gérant."
    )


def test_appareil__cookie_valide__pas_d_email_vu_le_mis_a_jour(fabrique: sessionmaker[Session]) -> None:
    compte = creer_compte(fabrique)
    c = client(fabrique)
    _connexion_complete(c, compte)
    c.post("/auth/deconnexion")
    (avant,) = lignes(fabrique, APPAREIL)
    assert _connexion_complete(c, compte, decalage=30).status_code == 200
    (apres,) = lignes(fabrique, APPAREIL)
    assert apres["vu_le"] > avant["vu_le"]  # type: ignore[operator]
    assert len(_jobs(fabrique, "courriel.nouvel_appareil")) == 1
    assert "lp_appareil" in c.cookies


def test_appareil__cookie_d_un_autre_utilisateur__traite_comme_nouveau(
    fabrique: sessionmaker[Session],
) -> None:
    premier, second = creer_compte(fabrique), creer_compte(fabrique, nom_affiche="M. Martin")
    c = client(fabrique)
    _connexion_complete(c, premier)
    c.post("/auth/deconnexion")
    assert _connexion_complete(c, second).status_code == 200
    utilisateurs = {j["payload"]["utilisateur_id"] for j in _jobs(fabrique, "courriel.nouvel_appareil")}  # type: ignore[index]
    assert utilisateurs == {str(premier.id), str(second.id)}


def test_appareil__pre_session_seule__aucun_email(fabrique: sessionmaker[Session]) -> None:
    compte = creer_compte(fabrique)
    client(fabrique).post("/auth/connexion", json={"email": compte.email, "mot_de_passe": MOT_DE_PASSE})
    assert _jobs(fabrique, "courriel.nouvel_appareil") == []
    assert lignes(fabrique, APPAREIL) == []


@pytest.mark.parametrize("champ", ["revoque_le", "expire_le"])
def test_appareil__revoque_ou_expire__email_de_nouveau(fabrique: sessionmaker[Session], champ: str) -> None:
    """La révocation par réinitialisation, suspension ou accès réinitialisé est testée en sections E et F."""
    compte = creer_compte(fabrique)
    c = client(fabrique)
    _connexion_complete(c, compte)
    c.post("/auth/deconnexion")
    with fabrique() as s, s.begin():
        s.execute(update(APPAREIL).values({champ: func.now() - timedelta(seconds=1)}))
    assert _connexion_complete(c, compte, decalage=30).status_code == 200
    assert len(_jobs(fabrique, "courriel.nouvel_appareil")) == 2


# --- alerte d'échecs (ADR 0006) ----------------------------------------------------------------------


def _gerants(fabrique: sessionmaker[Session]) -> list[Compte]:
    return [
        creer_compte(fabrique, role="gerant", nom_affiche="M. Martin"),
        creer_compte(fabrique, role="gerant", nom_affiche="Mme Leroy"),
        creer_compte(fabrique, role="gerant", nom_affiche="M. Absent", statut="suspendu"),
    ]


def _echecs(fabrique: sessionmaker[Session], email: str, nombre: int) -> None:
    """Échecs répartis sur plusieurs adresses IP, 4 par adresse : le verrou par couple ne se déclenche pas."""
    for i in range(nombre):
        c = client(fabrique, ip=f"10.0.{i // 4}.1")
        r = c.post("/auth/connexion", json={"email": email, "mot_de_passe": "un autre mot de passe"})
        assert r.status_code == 401


def test_alerte__20_echecs_dans_l_heure__email_aux_gerants_une_fois(fabrique: sessionmaker[Session]) -> None:
    martin, leroy, _ = _gerants(fabrique)
    compte = creer_compte(fabrique)
    _echecs(fabrique, compte.email, 21)
    (job,) = _jobs(fabrique, "courriel.alerte_echecs")
    assert job["payload"]["utilisateur_id"] == str(compte.id)  # type: ignore[index]
    assert set(job["payload"]) == {"utilisateur_id", "debut", "instant"}  # type: ignore[call-overload]
    expediteur = ExpediteurMemoire()
    executer_jobs(fabrique, expediteur)
    instant = valeur(
        fabrique, select(UTILISATEUR.c.derniere_alerte_echecs_le).where(UTILISATEUR.c.id == compte.id)
    )
    # début de l'intervalle : premier échec compté, inscrit au registre des tentatives
    debut = valeur(
        fabrique,
        select(func.min(TENTATIVE_CONNEXION.c.cree_le)).where(TENTATIVE_CONNEXION.c.reussie.is_(False)),
    )
    assert debut < instant  # type: ignore[operator]
    assert sorted(expediteur.envoyes, key=lambda e: e[0]) == sorted(
        [
            (martin.email, alerte_echecs("M. Martin", "Mme Durand", debut, instant)),  # type: ignore[arg-type]
            (leroy.email, alerte_echecs("Mme Leroy", "Mme Durand", debut, instant)),  # type: ignore[arg-type]
        ],
        key=lambda e: e[0],
    )


def test_alerte__19_echecs__aucune(fabrique: sessionmaker[Session]) -> None:
    _gerants(fabrique)
    compte = creer_compte(fabrique)
    _echecs(fabrique, compte.email, 19)
    assert _jobs(fabrique, "courriel.alerte_echecs") == []


def test_alerte__une_heure_apres_la_precedente__nouvelle_alerte(fabrique: sessionmaker[Session]) -> None:
    _gerants(fabrique)
    compte = creer_compte(fabrique)
    _echecs(fabrique, compte.email, 20)
    with fabrique() as s, s.begin():
        s.execute(
            update(UTILISATEUR)
            .where(UTILISATEUR.c.id == compte.id)
            .values(derniere_alerte_echecs_le=func.now() - timedelta(hours=1, seconds=1))
        )
    _echecs(fabrique, compte.email, 1)
    assert len(_jobs(fabrique, "courriel.alerte_echecs")) == 2


def test_alerte__deux_requetes_simultanees_au_seuil__une_seule_alerte(
    fabrique: sessionmaker[Session],
) -> None:
    _gerants(fabrique)
    compte = creer_compte(fabrique)
    cle = pseudonymiser(compte.email, CLES.pseudonymisation)
    with fabrique() as s, s.begin():
        for i in range(19):
            s.execute(
                insert(TENTATIVE_CONNEXION).values(
                    id=uuid7(),
                    cle_compte=cle,
                    utilisateur_id=compte.id,
                    ip=f"10.1.{i}.1",
                    etape="mot_de_passe",
                    reussie=False,
                )
            )
    clients = [client(fabrique, ip="10.2.0.1"), client(fabrique, ip="10.2.0.2")]
    fils = [
        threading.Thread(
            target=lambda c=c: c.post(
                "/auth/connexion", json={"email": compte.email, "mot_de_passe": "faux faux faux"}
            )
        )
        for c in clients
    ]
    for f in fils:
        f.start()
    for f in fils:
        f.join()
    assert len(_jobs(fabrique, "courriel.alerte_echecs")) == 1


def test_alerte__compte_inconnu__jamais(fabrique: sessionmaker[Session]) -> None:
    _gerants(fabrique)
    _echecs(fabrique, "personne@essai.local", 25)
    assert _jobs(fabrique, "courriel.alerte_echecs") == []


# --- alerte « compte suspendu » (TEC-SEC-19, ADR 0006) ----------------------------------------------


def test_alerte_compte_suspendu__une_par_compte_et_par_heure(fabrique: sessionmaker[Session]) -> None:
    martin, leroy, _ = _gerants(fabrique)
    compte = creer_compte(fabrique, statut="suspendu")
    assert _connexion_complete(client(fabrique), compte).status_code == 403
    assert _connexion_complete(client(fabrique), compte, decalage=30).status_code == 403
    assert len(_jobs(fabrique, "courriel.alerte_compte_suspendu")) == 1
    with fabrique() as s, s.begin():
        s.execute(
            update(UTILISATEUR)
            .where(UTILISATEUR.c.id == compte.id)
            .values(derniere_alerte_suspension_le=func.now() - timedelta(hours=1, seconds=1))
        )
    secours = client(fabrique)
    secours.post("/auth/connexion", json={"email": compte.email, "mot_de_passe": MOT_DE_PASSE})
    assert secours.post("/auth/code", json={"code": compte.codes[0]}).status_code == 403
    jobs = _jobs(fabrique, "courriel.alerte_compte_suspendu")
    assert len(jobs) == 2
    expediteur = ExpediteurMemoire()
    executer_jobs(fabrique, expediteur)
    assert sorted(dest for dest, _ in expediteur.envoyes) == sorted([martin.email, leroy.email] * 2)
    assert all(
        courriel.objet == alerte_compte_suspendu("x", "y", jobs[0]["cree_le"]).objet  # type: ignore[arg-type]
        for _, courriel in expediteur.envoyes
    )


# --- envoi par job ------------------------------------------------------------------------------------


def test_job_courriel__smtp_injoignable__reporte_sans_perdre_le_courriel(
    fabrique: sessionmaker[Session],
) -> None:
    compte = creer_compte(fabrique)
    _connexion_complete(client(fabrique), compte)
    assert executer_jobs(fabrique, ExpediteurMemoire(en_panne=True)) == ["reporte"]
    (job,) = _jobs(fabrique, "courriel.nouvel_appareil")
    assert (job["statut"], job["tentatives"]) == ("planifie", 0)
