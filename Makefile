SHELL := /bin/bash
.DEFAULT_GOAL := help
SERVICES := identity referentiel facturation charges-eau documents envois veille reporting
COMPOSE_DEV := docker compose -f compose.dev.yml
DEV_CERTS ?= deploy/nginx/certs
# Toutes les cibles sont des commandes : sans .PHONY, `make contracts` ne fait rien car le dossier contracts/ existe
.PHONY: help doctor dev-up dev-down dev-certs dev-secrets logs test lint typecheck contracts docs-check migrate new-service test-gabarit recette tick ci

help: ## Liste des cibles
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-16s\033[0m %s\n",$$1,$$2}'

doctor: ## Vérifie l'outillage local (docker, uv, node, gh, claude, jq) et installe les dépendances des scripts
	@for t in docker uv node npm gh claude jq; do command -v $$t >/dev/null && echo "ok   $$t" || echo "MANQUE $$t"; done
	@python3 -c "import jsonschema, yaml" 2>/dev/null && echo "ok   jsonschema + pyyaml" || echo "MANQUE python3-jsonschema python3-yaml (sudo apt install -y python3-jsonschema python3-yaml)"
	@docker compose version

dev-up: ## Démarre la plateforme de développement
	$(COMPOSE_DEV) up -d --build
dev-down: ## Arrête la plateforme (volumes conservés)
	$(COMPOSE_DEV) down
dev-certs: ## Certificat HTTPS auto-signé de la VM de dev : make dev-certs [IP=192.168.1.20] [FORCE=1]
	@ip="$(IP)"; [ -n "$$ip" ] || ip=$$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<NF;i++) if($$i=="src") print $$(i+1)}'); \
	echo "$$ip" | grep -Eq '^([0-9]{1,3}\.){3}[0-9]{1,3}$$' || { echo "Adresse IP de la VM introuvable ou invalide : make dev-certs IP=…"; exit 1; }; \
	if [ -f $(DEV_CERTS)/dev.crt ] && [ -z "$(FORCE)" ]; then echo "Certificat déjà présent ($(DEV_CERTS)/dev.crt) ; FORCE=1 pour le régénérer."; exit 0; fi; \
	mkdir -p $(DEV_CERTS) && (umask 077 && openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -nodes -days 365 \
	  -keyout $(DEV_CERTS)/dev.key -out $(DEV_CERTS)/dev.crt -subj "/CN=LePalier dev" \
	  -addext "subjectAltName=IP:$$ip,IP:127.0.0.1,DNS:localhost" \
	  -addext "basicConstraints=critical,CA:FALSE" -addext "extendedKeyUsage=serverAuth" 2>/dev/null) && \
	chmod 644 $(DEV_CERTS)/dev.crt && \
	echo "Certificat créé pour https://$$ip/ (valable 365 jours) dans $(DEV_CERTS)/" && \
	openssl x509 -in $(DEV_CERTS)/dev.crt -noout -fingerprint -sha256
dev-secrets: ## Secrets de dev dans deploy/secrets/ (ADR 0007), jamais affichés : make dev-secrets [FORCE=1]
	FORCE=$(FORCE) bash scripts/dev-secrets.sh
logs: ## Logs d'un service : make logs SVC=identity
	$(COMPOSE_DEV) logs -f $(SVC)

test: ## Tests : make test [SVC=nom]
ifdef SVC
	cd services/$(SVC) && uv run pytest
else
	@set -e; for s in $(SERVICES); do if [ -d services/$$s ]; then (cd services/$$s && uv run pytest); fi; done
	cd libs/commun && uv run pytest
	uv run --project libs/commun pytest -q -p no:cacheprovider scripts/tests
endif

lint: ## ruff + eslint
	cd libs/commun && uv run ruff check . && uv run ruff format --check .
	@for s in $(SERVICES) ; do [ -d services/$$s ] && (cd services/$$s && uv run ruff check . && uv run ruff format --check .) || true; done
	@[ -f front/package.json ] && (cd front && npm run lint) || true

typecheck: ## mypy strict sur commun et les moteurs, tsc sur le front
	cd libs/commun && uv run mypy src/commun tests
	@for s in $(SERVICES) ; do [ -d services/$$s/app/engines ] && (cd services/$$s && uv run mypy --strict app/engines) || true; done
	@[ -f front/package.json ] && (cd front && npx tsc --noEmit) || true

contracts: ## Valide les contrats d'événements (environnement de libs/commun : jsonschema, pyyaml, rfc3339-validator)
	uv run --project libs/commun python scripts/check_contracts.py

docs-check: ## Vérifie la présence des specs exportées et les identifiants cités
	python3 scripts/docs_check.py

migrate: ## Migrations d'un service avec le rôle propriétaire des tables (TEC-DAT-03) : make migrate SVC=nom
	@# en dev, rôle admin de compose.dev.yml ; ailleurs, fournir APP_MIGRATION_DATABASE_URL
	cd services/$(SVC) && APP_MIGRATION_DATABASE_URL="$${APP_MIGRATION_DATABASE_URL:-postgresql+psycopg://admin:admin@localhost:5432/$(subst -,_,$(SVC))}" uv run alembic upgrade head

new-service: ## Crée un service : make new-service NAME=nom
	bash scripts/new-service.sh $(NAME)

recette: ## Charge le jeu de données de recette d'un lot : make recette LOT=N
	@[ -f scripts/recette/lot-$(LOT).py ] && uv run python scripts/recette/lot-$(LOT).py || echo "scripts/recette/lot-$(LOT).py à générer avec /recette $(LOT)"
	@echo "Checklist : docs/RECETTE/lot-$(LOT).md"

tick: ## Déclenche le planificateur quotidien de tous les services (recette)
	@for s in $(SERVICES); do $(COMPOSE_DEV) exec -T $$s uv run python -m app.scheduler tick 2>/dev/null || true; done

test-gabarit: ## Lint du gabarit, puis typage et tests d'un service généré dans un dossier temporaire
	@set -e; dossier="$$(mktemp -d)/veille"; \
	DESTINATION="$$dossier" bash scripts/new-service.sh veille >/dev/null; \
	echo "Service d'essai généré dans $$dossier"; \
	(cd "$$dossier" && uv sync -q --all-extras); \
	uv run --project "$$dossier" ruff check services/_template; \
	uv run --project "$$dossier" ruff format --check services/_template; \
	cd "$$dossier" && uv run mypy app migrations tests && uv run pytest -p no:cacheprovider --cov-fail-under=80

ci: lint typecheck contracts test ## Ce que la CI exécute
