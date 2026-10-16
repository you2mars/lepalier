# syntax=docker/dockerfile:1.7
# Front Next.js 15 (sortie standalone). Contexte de construction : la racine du dépôt (contracts/libelles est
# importé à la construction). Image de départ épinglée par digest ; dépendances de package-lock.json (npm ci).
FROM node:22-alpine@sha256:0a7108bf6c7bf5de370ffb1a3ed6be93d405b43ff159f681a8d18c0e2bc2e402 AS dependances
WORKDIR /srv/front
COPY front/package.json front/package-lock.json ./
RUN npm ci --no-audit --no-fund

FROM node:22-alpine@sha256:0a7108bf6c7bf5de370ffb1a3ed6be93d405b43ff159f681a8d18c0e2bc2e402 AS construction
WORKDIR /srv/front
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=dependances /srv/front/node_modules ./node_modules
COPY front/ ./
COPY contracts/libelles /srv/contracts/libelles
RUN npm run build

# Exécution : la sortie standalone seule (pas de node_modules de construction), utilisateur 10001
FROM node:22-alpine@sha256:0a7108bf6c7bf5de370ffb1a3ed6be93d405b43ff159f681a8d18c0e2bc2e402
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000 HOSTNAME=0.0.0.0
WORKDIR /srv/front
RUN addgroup -g 10001 app && adduser -D -H -u 10001 -G app app
COPY --from=construction --chown=app:app /srv/front/.next/standalone ./
COPY --from=construction --chown=app:app /srv/front/.next/static ./.next/static
USER app
EXPOSE 3000
CMD ["node", "server.js"]
