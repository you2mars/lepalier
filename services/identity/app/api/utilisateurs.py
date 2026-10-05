"""Routes /utilisateurs* : réservées au gérant ; clé d'idempotence exigée sur les écritures (ADR 0006)."""

from __future__ import annotations

from dataclasses import asdict
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.auth import ip_de
from app.api.saisie import email_saisi, nom_affiche_saisi
from app.services import utilisateurs
from commun.identite import Identite, Role, exiger_role

routeur = APIRouter(prefix="/utilisateurs")
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
