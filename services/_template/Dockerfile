# syntax=docker/dockerfile:1.7
FROM ghcr.io/__GHCR_OWNER__/app-base:latest AS base
WORKDIR /srv/app
COPY libs/commun /srv/libs/commun
COPY services/__SERVICE__/pyproject.toml ./
RUN uv sync --no-dev --frozen || uv sync --no-dev
COPY services/__SERVICE__/ ./
ENV SERVICE_NAME=__SERVICE__
EXPOSE 8000
# API + worker dans le même conteneur (décision n°3) ; supervisord lance les deux processus
CMD ["supervisord", "-c", "/srv/app/supervisord.conf"]
