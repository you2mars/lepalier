# syntax=docker/dockerfile:1.7
# Disposition du dépôt reproduite sous /srv : le chemin ../../libs/commun de pyproject.toml et le dossier
# contracts/libelles (chemin par défaut d'APP_LIBELLES_DIR) restent valables dans l'image.
FROM ghcr.io/you2mars/app-base:latest
RUN mkdir -p /srv/services/identity
WORKDIR /srv/services/identity
COPY --chown=app:app libs/commun /srv/libs/commun
COPY --chown=app:app contracts/libelles /srv/contracts/libelles
COPY --chown=app:app services/identity/pyproject.toml services/identity/uv.lock ./
# dépendances seules d'abord (couche réutilisée tant que le verrou ne change pas) ; --frozen : uv.lock fait foi
RUN uv sync --frozen --no-dev --no-install-project
COPY --chown=app:app services/identity/ ./
RUN uv sync --frozen --no-dev
ENV SERVICE_NAME=identity PATH=/srv/services/identity/.venv/bin:$PATH
EXPOSE 8000
# API + worker dans le même conteneur (décision n°3) ; supervisord lance les deux processus
CMD ["supervisord", "-c", "/srv/services/identity/supervisord.conf"]
