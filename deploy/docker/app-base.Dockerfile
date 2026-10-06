# Image commune aux huit services (TEC-OPS topologie) : Python 3.12 + dépendances WeasyPrint + uv + supervisord.
# Images de départ épinglées par digest ; uv dans la version qui produit les uv.lock du dépôt.
# Construite en local par `make images` (ghcr.io/you2mars/app-base:latest), publiée par la CI sur main.
FROM python:3.12-slim-bookworm@sha256:7753c33391fc9f01d1984375bf375eb6686d52ba10db6043a86634a5ccf90dcf
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never TZ=UTC
RUN apt-get update && apt-get install -y --no-install-recommends \
      libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libffi8 libcairo2 libgdk-pixbuf-2.0-0 \
      fonts-dejavu-core shared-mime-info supervisor curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.12.23@sha256:61d393e44e249f2e4b526b6c7ddcecce245946826e608e11c93ad4f5bba55b21 /uv /usr/local/bin/uv
# /srv appartient à l'utilisateur des services (uid 10001, propriétaire des secrets montés, ADR 0007)
RUN useradd --create-home --uid 10001 app && install -d -o app -g app /srv
USER app
WORKDIR /srv
