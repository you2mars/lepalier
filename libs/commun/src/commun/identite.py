"""Identité transmise par nginx et vérifiée par chaque service (TEC-SEC-03, TEC-API-01).

`identity` signe `X-User-Id`, `X-Role`, `X-Auth-Exp` par HMAC-SHA256 (`X-Auth-Sig`) ; nginx les réinjecte
après `auth_request` en écrasant toute valeur venue du client ; chaque service les vérifie, même sur le
réseau interne.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Literal, cast, get_args
from uuid import UUID

from fastapi import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from commun.erreurs import ErreurApi, reponse_erreur

Role = Literal["gerant", "associe", "operateur"]
ROLES: tuple[str, ...] = get_args(Role)
LIBELLES_ROLES: dict[str, str] = {
    "gerant": "au gérant",
    "associe": "à l'associé",
    "operateur": "à l'opérateur",
}
DUREE_MAX_SECONDES = 3600
MESSAGE_NON_AUTHENTIFIE = "Votre session a expiré ou n'est pas reconnue. Reconnectez-vous."


class IdentiteInvalide(Exception):
    """En-têtes d'identité absents, mal formés, expirés ou mal signés (raison technique, jamais affichée)."""


@dataclass(frozen=True)
class Identite:
    user_id: UUID
    role: Role
    exp: int


def _message(user_id: UUID | str, role: str, exp: int) -> bytes:
    return f"v1|{user_id}|{role}|{exp}".encode()


def signer(user_id: UUID | str, role: str, exp: int, cle: bytes) -> str:
    return hmac.new(cle, _message(user_id, role, exp), hashlib.sha256).hexdigest()


def entetes_signes(user_id: UUID, role: Role, exp: int, cle: bytes) -> dict[str, str]:
    """En-têtes produits par `identity` (réponse à `/auth/verify`) et repris par nginx."""
    return {
        "X-User-Id": str(user_id),
        "X-Role": role,
        "X-Auth-Exp": str(exp),
        "X-Auth-Sig": signer(user_id, role, exp, cle),
    }


def verifier(
    entetes: Mapping[str, str], cles: Sequence[bytes], maintenant: int, duree_max: int = DUREE_MAX_SECONDES
) -> Identite:
    """Vérifie la signature avec la clé courante ou la précédente (rotation mensuelle)."""
    valeurs = {nom.lower(): valeur for nom, valeur in entetes.items()}
    try:
        brut_uid, role, brut_exp, signature = (
            valeurs["x-user-id"],
            valeurs["x-role"],
            valeurs["x-auth-exp"],
            valeurs["x-auth-sig"],
        )
    except KeyError as exc:
        raise IdentiteInvalide(f"en-tête absent : {exc.args[0]}") from exc
    if not any(
        hmac.compare_digest(signer(brut_uid, role, _entier(brut_exp), cle), signature) for cle in cles
    ):
        raise IdentiteInvalide("signature invalide")
    exp = _entier(brut_exp)
    if not maintenant < exp <= maintenant + duree_max:
        raise IdentiteInvalide("expiration hors délai")
    if role not in ROLES:
        raise IdentiteInvalide("rôle inconnu")
    try:
        user_id = UUID(brut_uid)
    except ValueError as exc:
        raise IdentiteInvalide("identifiant mal formé") from exc
    return Identite(user_id=user_id, role=cast(Role, role), exp=exp)


def _entier(valeur: str) -> int:
    try:
        return int(valeur)
    except ValueError as exc:
        raise IdentiteInvalide("expiration mal formée") from exc


class IdentiteMiddleware:
    """Refuse (401) toute requête hors préfixes publics sans identité valide ; dépose l'identité vérifiée."""

    def __init__(
        self,
        app: ASGIApp,
        cles: Sequence[bytes],
        prefixes_publics: Sequence[str] = ("/internal/",),
        horloge: Callable[[], float] = time.time,
    ) -> None:
        self.app = app
        self.cles = list(cles)
        self.prefixes_publics = tuple(prefixes_publics)
        self.horloge = horloge

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"].startswith(self.prefixes_publics):
            await self.app(scope, receive, send)
            return
        entetes = {nom.decode("latin-1"): valeur.decode("latin-1") for nom, valeur in scope["headers"]}
        try:
            identite = verifier(entetes, self.cles, int(self.horloge()))
        except IdentiteInvalide:
            await reponse_erreur(scope, 401, "unauthenticated", MESSAGE_NON_AUTHENTIFIE)(scope, receive, send)
            return
        scope.setdefault("state", {})["identite"] = identite
        await self.app(scope, receive, send)


def identite_courante(request: Request) -> Identite:
    """Dépendance FastAPI : identité vérifiée par le middleware ; refus par défaut s'il n'est pas installé."""
    identite = request.scope.get("state", {}).get("identite")
    if not isinstance(identite, Identite):
        raise ErreurApi(401, "unauthenticated", MESSAGE_NON_AUTHENTIFIE)
    return identite


def exiger_role(*roles: Role) -> Callable[[Request], Identite]:
    """Dépendance FastAPI `require_role` : 403 avec un message qui nomme les rôles autorisés."""
    libelles = [LIBELLES_ROLES[r] for r in roles]
    reserve = libelles[0] if len(libelles) == 1 else ", ".join(libelles[:-1]) + " ou " + libelles[-1]
    message = f"Cette action est réservée {reserve}."

    def dependance(request: Request) -> Identite:
        identite = identite_courante(request)
        if identite.role not in roles:
            raise ErreurApi(403, "forbidden", message)
        return identite

    return dependance
