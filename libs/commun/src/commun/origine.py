"""Contrôle de l'origine des écritures (TEC-SEC-07), en complément de SameSite=Strict."""

from __future__ import annotations

from collections.abc import Collection, Sequence

from starlette.types import ASGIApp, Receive, Scope, Send

from commun.erreurs import reponse_erreur

METHODES_SURES = frozenset({"GET", "HEAD", "OPTIONS"})
MESSAGE = "Cette demande ne vient pas de LePalier et a été refusée. Rechargez la page puis réessayez."


class OrigineMiddleware:
    """Refuse (403) une écriture dont `Origin` n'est pas autorisée ou que le navigateur signale inter-sites.

    Une requête sans `Origin` ni `Sec-Fetch-Site` (BFF, outil en ligne de commande) n'est pas concernée.
    """

    def __init__(
        self,
        app: ASGIApp,
        origines_autorisees: Collection[str],
        prefixes_exemptes: Sequence[str] = ("/internal/",),
    ) -> None:
        self.app = app
        self.origines = frozenset(o.rstrip("/") for o in origines_autorisees)
        self.prefixes_exemptes = tuple(prefixes_exemptes)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] == "http"
            and scope["method"] not in METHODES_SURES
            and not scope["path"].startswith(self.prefixes_exemptes)
            and not self._acceptable(scope)
        ):
            await reponse_erreur(scope, 403, "forbidden_origin", MESSAGE)(scope, receive, send)
            return
        await self.app(scope, receive, send)

    def _acceptable(self, scope: Scope) -> bool:
        entetes = {nom: valeur.decode("latin-1") for nom, valeur in scope["headers"]}
        origine = entetes.get(b"origin")
        site = entetes.get(b"sec-fetch-site")
        if origine is not None and origine.rstrip("/") not in self.origines:
            return False
        return site is None or site in ("same-origin", "none")
