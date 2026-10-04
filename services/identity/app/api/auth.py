"""Routes /auth/* : publiques derrière nginx, sans identité utilisateur ni clé d'idempotence (ADR 0006)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from app.engines import durees
from app.services import connexion

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


def _ip(request: Request) -> str:
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
        request.app.state.fabrique, corps.email, corps.mot_de_passe, _ip(request), request.app.state.cles
    )
    _poser(response, COOKIE_PRE, jeton, int(durees.DUREE_PRE_SESSION.total_seconds()))
    return {"etape": "code"}


@routeur.post("/code")
def code(corps: Code, request: Request, response: Response) -> dict[str, Any]:
    ouverte = connexion.valider_code(
        request.app.state.fabrique,
        request.cookies.get(COOKIE_PRE),
        corps.code,
        _ip(request),
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
    connexion.deconnecter(request.app.state.fabrique, request.cookies.get(COOKIE_SESSION), _ip(request))
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
