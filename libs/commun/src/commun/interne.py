"""Appels HTTP entre services (TEC-API-05, TEC-SEC-04).

Uniquement vers `/internal/*` (réseau Docker `backend`, nginx y répond 404), avec un jeton de service par
couple appelant → appelé, un délai de 5 s et aucune nouvelle tentative sur les écritures ; une lecture est
retentée une fois si l'appelé est injoignable. Le `trace_id` est propagé (`X-Request-Id`, `traceparent`).

L'appelé ne connaît que l'empreinte SHA-256 des jetons qu'il accepte ; leur provenance (fichier de secret,
base chiffrée) est l'affaire du service.
"""

from __future__ import annotations

import hashlib
import hmac
from collections.abc import Callable, Collection, Mapping
from typing import Any

import httpx
from fastapi import Request
from opentelemetry import propagate
from pydantic_core import to_json
from starlette.types import ASGIApp, Receive, Scope, Send

from commun.erreurs import ErreurApi, reponse_erreur
from commun.trace import trace_id_courant

DELAI_SECONDES = 5.0
PREFIXE = "/internal/"
ENTETE_APPELANT = "X-Service-Appelant"
INDISPONIBLE = frozenset({502, 503, 504})
MESSAGE_NON_AUTHENTIFIE = "Appel interne refusé : service appelant non reconnu."
MESSAGE_NON_AUTORISE = "Appel interne refusé : ce service n'a pas accès à cette ressource."


def empreinte_jeton(jeton: str) -> bytes:
    return hashlib.sha256(jeton.encode()).digest()


# --- côté appelé ------------------------------------------------------------------------------------


class ServiceInterneMiddleware:
    """Refuse (401) un appel `/internal/*` sans jeton valide pour le service annoncé, hors chemins libres."""

    def __init__(
        self,
        app: ASGIApp,
        empreintes: Mapping[str, bytes],
        chemins_libres: Collection[str] = ("/internal/healthz",),
    ) -> None:
        self.app = app
        self.empreintes = dict(empreintes)
        self.chemins_libres = frozenset(chemins_libres)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        chemin = scope.get("path", "")
        if scope["type"] != "http" or not chemin.startswith(PREFIXE) or chemin in self.chemins_libres:
            await self.app(scope, receive, send)
            return
        appelant = self._appelant_authentifie(scope)
        if appelant is None:
            await reponse_erreur(scope, 401, "service_non_authentifie", MESSAGE_NON_AUTHENTIFIE)(
                scope, receive, send
            )
            return
        scope.setdefault("state", {})["service_appelant"] = appelant
        await self.app(scope, receive, send)

    def _appelant_authentifie(self, scope: Scope) -> str | None:
        entetes = {n: v.decode("latin-1") for n, v in scope["headers"]}
        appelant = entetes.get(ENTETE_APPELANT.lower().encode(), "")
        schema, _, jeton = entetes.get(b"authorization", "").partition(" ")
        attendue = self.empreintes.get(appelant)
        if attendue is None or schema != "Bearer" or not jeton:
            return None
        return appelant if hmac.compare_digest(empreinte_jeton(jeton), attendue) else None


def service_appelant(request: Request) -> str:
    """Dépendance FastAPI : service appelant authentifié ; refus par défaut si le middleware manque."""
    appelant = request.scope.get("state", {}).get("service_appelant")
    if not isinstance(appelant, str):
        raise ErreurApi(401, "service_non_authentifie", MESSAGE_NON_AUTHENTIFIE)
    return appelant


def exiger_service(*services: str) -> Callable[[Request], str]:
    """Dépendance FastAPI : limite une route interne à certains appelants (403 sinon)."""

    def dependance(request: Request) -> str:
        appelant = service_appelant(request)
        if appelant not in services:
            raise ErreurApi(403, "service_non_autorise", MESSAGE_NON_AUTORISE)
        return appelant

    return dependance


# --- côté appelant ----------------------------------------------------------------------------------


class ErreurServiceInterne(Exception):
    """Réponse d'erreur d'un autre service (format commun) ; le message n'est pas destiné à l'utilisateur."""

    def __init__(self, statut: int, code: str, message: str) -> None:
        super().__init__(f"{statut} {code} : {message}")
        self.statut = statut
        self.code = code
        self.message = message


class ServiceIndisponible(ErreurServiceInterne):
    """Service injoignable, délai dépassé ou passerelle en erreur : « momentanément indisponible »."""

    def __init__(self, detail: str) -> None:
        super().__init__(503, "service_indisponible", detail)


class _Base:
    def __init__(self, appelant: str, jeton: str) -> None:
        self.appelant = appelant
        self.jeton = jeton

    def _entetes(self) -> dict[str, str]:
        entetes = {
            "Authorization": f"Bearer {self.jeton}",
            ENTETE_APPELANT: self.appelant,
            "X-Request-Id": trace_id_courant(),
        }
        propagate.inject(entetes)
        return entetes

    @staticmethod
    def _verifier_chemin(chemin: str) -> None:
        if not chemin.startswith(PREFIXE):
            raise ValueError(f"appel interne limité aux routes {PREFIXE}* : {chemin!r}")

    @staticmethod
    def _tentatives(methode: str) -> int:
        return 2 if methode == "GET" else 1

    @staticmethod
    def _corps(contenu: Any) -> bytes | None:
        return None if contenu is None else to_json(contenu)

    @staticmethod
    def _interpreter(reponse: httpx.Response) -> Any:
        if reponse.status_code in INDISPONIBLE:
            raise ServiceIndisponible(f"réponse {reponse.status_code} de {reponse.request.url.host}")
        if reponse.status_code >= 400:
            try:
                corps = reponse.json()
                code, message = str(corps["code"]), str(corps["message"])
            except (ValueError, KeyError, TypeError):
                code, message = "erreur_interne", reponse.text[:200]
            raise ErreurServiceInterne(reponse.status_code, code, message)
        return reponse.json() if reponse.content else None


class ClientInterne(_Base):
    """Client synchrone (routes FastAPI synchrones, jobs)."""

    def __init__(
        self, *, appelant: str, url_base: str, jeton: str, client: httpx.Client | None = None
    ) -> None:
        super().__init__(appelant, jeton)
        self.http = client or httpx.Client(base_url=url_base, timeout=DELAI_SECONDES)

    def get(self, chemin: str, params: Mapping[str, str] | None = None) -> Any:
        return self._requete("GET", chemin, params=params)

    def post(self, chemin: str, contenu: Any = None) -> Any:
        return self._requete("POST", chemin, contenu=contenu)

    def fermer(self) -> None:
        self.http.close()

    def _requete(
        self, methode: str, chemin: str, params: Mapping[str, str] | None = None, contenu: Any = None
    ) -> Any:
        self._verifier_chemin(chemin)
        entetes = {**self._entetes(), "Content-Type": "application/json"}
        for tentative in range(self._tentatives(methode)):
            try:
                reponse = self.http.request(
                    methode, chemin, params=params, content=self._corps(contenu), headers=entetes
                )
            except httpx.TransportError as exc:
                if tentative + 1 == self._tentatives(methode):
                    raise ServiceIndisponible(f"{methode} {chemin} : {type(exc).__name__}") from exc
                continue
            return self._interpreter(reponse)
        raise AssertionError("inatteignable")  # pragma: no cover


class ClientInterneAsync(_Base):
    """Client asynchrone (worker, consommateurs)."""

    def __init__(
        self, *, appelant: str, url_base: str, jeton: str, client: httpx.AsyncClient | None = None
    ) -> None:
        super().__init__(appelant, jeton)
        self.http = client or httpx.AsyncClient(base_url=url_base, timeout=DELAI_SECONDES)

    async def get(self, chemin: str, params: Mapping[str, str] | None = None) -> Any:
        return await self._requete("GET", chemin, params=params)

    async def post(self, chemin: str, contenu: Any = None) -> Any:
        return await self._requete("POST", chemin, contenu=contenu)

    async def fermer(self) -> None:
        await self.http.aclose()

    async def _requete(
        self, methode: str, chemin: str, params: Mapping[str, str] | None = None, contenu: Any = None
    ) -> Any:
        self._verifier_chemin(chemin)
        entetes = {**self._entetes(), "Content-Type": "application/json"}
        for tentative in range(self._tentatives(methode)):
            try:
                reponse = await self.http.request(
                    methode, chemin, params=params, content=self._corps(contenu), headers=entetes
                )
            except httpx.TransportError as exc:
                if tentative + 1 == self._tentatives(methode):
                    raise ServiceIndisponible(f"{methode} {chemin} : {type(exc).__name__}") from exc
                continue
            return self._interpreter(reponse)
        raise AssertionError("inatteignable")  # pragma: no cover
