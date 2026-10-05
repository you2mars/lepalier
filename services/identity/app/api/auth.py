"""Routes /auth/* : publiques derrière nginx, sans identité utilisateur ni clé d'idempotence (ADR 0006)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.saisie import nom_affiche_saisi
from app.engines import durees
from app.libelles import message
from app.services import activation, connexion, reinitialisation

COOKIE_PRE = "lp_pre"
COOKIE_SESSION = "lp_session"
COOKIE_APPAREIL = "lp_appareil"
# adresse notée quand ni nginx ni la connexion n'en fournissent (jamais une adresse d'écoute)
IP_INCONNUE = "0.0.0.0"  # noqa: S104

routeur = APIRouter(prefix="/auth")


class Identifiants(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(max_length=254)
    mot_de_passe: str = Field(max_length=1024)


class Code(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(max_length=64)


class Lien(BaseModel):
    model_config = ConfigDict(extra="forbid")
    jeton: str = Field(max_length=64)


class Demande(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(max_length=1024)


class FinReinitialisation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    jeton: str = Field(max_length=64)
    mot_de_passe: str = Field(max_length=1024)
    code: str = Field(max_length=64)


class FinActivation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    jeton: str = Field(max_length=64)
    mot_de_passe: str = Field(max_length=1024)
    code: str = Field(max_length=64)
    nom_affiche: str | None = Field(default=None, max_length=1024)

    _nom = field_validator("nom_affiche")(lambda nom: None if nom is None else nom_affiche_saisi(nom))


def ip_de(request: Request) -> str:
    """Adresse posée par nginx (X-Real-IP) ; à défaut, celle de la connexion."""
    return request.headers.get("x-real-ip") or (request.client.host if request.client else IP_INCONNUE)


def _poser(reponse: Response, nom: str, valeur: str, duree_secondes: int) -> None:
    reponse.set_cookie(
        nom, valeur, max_age=duree_secondes, httponly=True, secure=True, samesite="strict", path="/"
    )


def _effacer(reponse: Response, nom: str) -> None:
    reponse.delete_cookie(nom, httponly=True, secure=True, samesite="strict", path="/")


@routeur.post("/connexion")
def connexion_(corps: Identifiants, request: Request, response: Response) -> dict[str, str]:
    jeton = connexion.connecter(
        request.app.state.fabrique, corps.email, corps.mot_de_passe, ip_de(request), request.app.state.cles
    )
    _poser(response, COOKIE_PRE, jeton, int(durees.DUREE_PRE_SESSION.total_seconds()))
    return {"etape": "code"}


@routeur.post("/code")
def code(corps: Code, request: Request, response: Response) -> dict[str, Any]:
    ouverte = connexion.valider_code(
        request.app.state.fabrique,
        request.cookies.get(COOKIE_PRE),
        corps.code,
        ip_de(request),
        request.cookies.get(COOKIE_APPAREIL),
        request.app.state.cles,
    )
    _effacer(response, COOKIE_PRE)
    _poser(response, COOKIE_SESSION, ouverte.jeton_session, int(durees.DUREE_MAX_SESSION.total_seconds()))
    if ouverte.jeton_appareil is not None:
        _poser(response, COOKIE_APPAREIL, ouverte.jeton_appareil, int(durees.DUREE_APPAREIL.total_seconds()))
    return {"nom_affiche": ouverte.nom_affiche, "role": ouverte.role}


@routeur.post("/deconnexion", status_code=204)
def deconnexion(request: Request) -> Response:
    connexion.deconnecter(request.app.state.fabrique, request.cookies.get(COOKIE_SESSION), ip_de(request))
    reponse = Response(status_code=204)
    _effacer(reponse, COOKIE_SESSION)
    return reponse


@routeur.get("/verify")
def verify(request: Request) -> Response:
    """Appelé par nginx (auth_request) : 200 et en-têtes signés, ou 401 sans corps (TEC-WEB-03)."""
    entetes = connexion.verifier_session(
        request.app.state.fabrique, request.cookies.get(COOKIE_SESSION), request.app.state.cles
    )
    if entetes is None:
        return Response(status_code=401)
    return Response(status_code=200, headers=entetes)


# --- activation depuis le lien d'invitation (ADR 0006) ---------------------------------------------------


@routeur.post("/activation/debut")
def activation_debut(corps: Lien, request: Request) -> dict[str, str]:
    return activation.debut(request.app.state.fabrique, corps.jeton, request.app.state.cles)


@routeur.post("/activation/fin")
def activation_fin(corps: FinActivation, request: Request, response: Response) -> dict[str, Any]:
    """Compte actif et session complète ouverte ; le front affiche les codes de secours avant l'accueil."""
    active = activation.fin(
        request.app.state.fabrique,
        corps.jeton,
        corps.mot_de_passe,
        corps.code,
        corps.nom_affiche,
        ip_de(request),
        request.cookies.get(COOKIE_APPAREIL),
        request.app.state.cles,
    )
    _poser(response, COOKIE_SESSION, active.jeton_session, int(durees.DUREE_MAX_SESSION.total_seconds()))
    if active.jeton_appareil is not None:
        _poser(response, COOKIE_APPAREIL, active.jeton_appareil, int(durees.DUREE_APPAREIL.total_seconds()))
    return {
        "etape": "confirmation_codes",
        "codes_secours": active.codes_secours,
        "nom_affiche": active.nom_affiche,
        "role": active.role,
    }


# --- mot de passe oublié (ADR 0006) ---------------------------------------------------------------------


@routeur.post("/reinitialisation/demande", status_code=202)
def reinitialisation_demande(corps: Demande, request: Request) -> dict[str, str]:
    """Même réponse pour tout compte, existant ou non (ADR 0006)."""
    reinitialisation.demander(request.app.state.fabrique, corps.email, ip_de(request))
    return {"message": message("reinitialisation.demande_envoyee")}


@routeur.post("/reinitialisation/fin", status_code=204)
def reinitialisation_fin(corps: FinReinitialisation, request: Request) -> Response:
    reinitialisation.terminer(
        request.app.state.fabrique,
        corps.jeton,
        corps.mot_de_passe,
        corps.code,
        ip_de(request),
        request.app.state.cles,
    )
    return Response(status_code=204)
