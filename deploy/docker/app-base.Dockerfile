# Image commune aux huit services (TEC-OPS topologie) : Python 3.12 + dépendances WeasyPrint + uv + supervisord
FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_LINK_MODE=copy TZ=UTC
RUN apt-get update && apt-get install -y --no-install-recommends \
      libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libffi8 libcairo2 libgdk-pixbuf-2.0-0 \
      fonts-dejavu-core shared-mime-info supervisor curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
RUN useradd --create-home --uid 10001 app
USER app
WORKDIR /srv/app
