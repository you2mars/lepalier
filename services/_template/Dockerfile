# syntax=docker/dockerfile:1.7
# Disposition du dépôt reproduite sous /srv : le chemin ../../libs/commun de pyproject.toml et le dossier
# contracts/libelles (chemin par défaut d'APP_LIBELLES_DIR) restent valables dans l'image.
FROM ghcr.io/you2mars/app-base:latest
RUN mkdir -p /srv/services/__SERVICE__
WORKDIR /srv/services/__SERVICE__
COPY --chown=app:app libs/commun /srv/libs/commun
COPY --chown=app:app contracts/libelles /srv/contracts/libelles
COPY --chown=app:app services/__SERVICE__/pyproject.toml services/__SERVICE__/uv.lock ./
# dépendances seules d'abord (couche réutilisée tant que le verrou ne change pas) ; --frozen : uv.lock fait foi
RUN uv sync --frozen --no-dev --no-install-project
COPY --chown=app:app services/__SERVICE__/ ./
RUN uv sync --frozen --no-dev
ENV SERVICE_NAME=__SERVICE__ PATH=/srv/services/__SERVICE__/.venv/bin:$PATH
EXPOSE 8000
# API + worker dans le même conteneur (décision n°3) ; supervisord lance les deux processus
CMD ["supervisord", "-c", "/srv/services/__SERVICE__/supervisord.conf"]
