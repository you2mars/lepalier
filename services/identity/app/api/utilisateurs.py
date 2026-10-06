"""Routes /utilisateurs* (gérant seul, clé d'idempotence exigée sur les écritures, ADR 0006) et /moi."""

from __future__ import annotations

from dataclasses import asdict
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.auth import ip_de
from app.api.saisie import email_saisi, nom_affiche_saisi
from app.services import utilisateurs
from commun.identite import Identite, Role, exiger_role, identite_courante

routeur = APIRouter(prefix="/utilisateurs")
routeur_moi = APIRouter()
Gerant = Annotated[Identite, Depends(exiger_role("gerant"))]


class NouvelleInvitation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(max_length=1024)
    nom_affiche: str = Field(max_length=1024)
    role: Role

    _email = field_validator("email")(email_saisi)
    _nom = field_validator("nom_affiche")(nom_affiche_saisi)


@routeur.post("/inviter", status_code=201)
def inviter(corps: NouvelleInvitation, gerant: Gerant, request: Request) -> dict[str, Any]:
    invite = utilisateurs.inviter(
        request.app.state.fabrique, gerant.user_id, corps.email, corps.nom_affiche, corps.role, ip_de(request)
    )
    return {**asdict(invite), "id": str(invite.id)}


@routeur.post("/{utilisateur_id}/renvoyer-invitation", status_code=202)
def renvoyer_invitation(utilisateur_id: UUID, gerant: Gerant, request: Request) -> Response:
    utilisateurs.renvoyer_invitation(
        request.app.state.fabrique, gerant.user_id, utilisateur_id, ip_de(request)
    )
    return Response(status_code=202)


class Modification(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Role | None = None
    statut: Literal["actif", "suspendu"] | None = None


@routeur.get("")
def lister(_: Gerant, request: Request) -> dict[str, Any]:
    return {"utilisateurs": utilisateurs.lister(request.app.state.fabrique)}


@routeur.patch("/{utilisateur_id}")
def modifier(utilisateur_id: UUID, corps: Modification, gerant: Gerant, request: Request) -> dict[str, Any]:
    """Rôle, suspension ou réactivation ; au moins un des deux champs."""
    if corps.role is None and corps.statut is None:
        raise RequestValidationError([{"type": "missing", "loc": ("body", "role"), "msg": "", "input": None}])
    return utilisateurs.modifier(
        request.app.state.fabrique, gerant.user_id, utilisateur_id, corps.role, corps.statut, ip_de(request)
    )


@routeur.post("/{utilisateur_id}/reinitialiser-acces", status_code=202)
def reinitialiser_acces(utilisateur_id: UUID, gerant: Gerant, request: Request) -> Response:
    utilisateurs.reinitialiser_acces(
        request.app.state.fabrique, gerant.user_id, utilisateur_id, ip_de(request)
    )
    return Response(status_code=202)


@routeur_moi.get("/moi")
def moi(identite: Annotated[Identite, Depends(identite_courante)], request: Request) -> dict[str, Any]:
    """Tous les rôles : nom affiché, rôle et adresse du compte connecté, jamais ceux des autres."""
    return utilisateurs.moi(request.app.state.fabrique, identite.user_id)
