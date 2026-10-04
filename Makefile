SHELL := /bin/bash
.DEFAULT_GOAL := help
SERVICES := identity referentiel facturation charges-eau documents envois veille reporting
COMPOSE_DEV := docker compose -f compose.dev.yml
DEV_CERTS ?= deploy/nginx/certs
# Toutes les cibles sont des commandes : sans .PHONY, `make contracts` ne fait rien car le dossier contracts/ existe
.PHONY: help doctor dev-up dev-down dev-certs logs test lint typecheck contracts docs-check migrate new-service recette tick ci

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
logs: ## Logs d'un service : make logs SVC=identity
	$(COMPOSE_DEV) logs -f $(SVC)

test: ## Tests : make test [SVC=nom]
ifdef SVC
	cd services/$(SVC) && uv run pytest
else
	@for s in $(SERVICES); do [ -d services/$$s ] && (cd services/$$s && uv run pytest) || true; done
	@[ -d libs/commun/tests ] && (cd libs/commun && uv run pytest) || true
endif

lint: ## ruff + eslint
	@for s in $(SERVICES) ; do [ -d services/$$s ] && (cd services/$$s && uv run ruff check . && uv run ruff format --check .) || true; done
	@[ -f front/package.json ] && (cd front && npm run lint) || true

typecheck: ## mypy strict sur les moteurs, tsc sur le front
	@for s in $(SERVICES) ; do [ -d services/$$s/app/engines ] && (cd services/$$s && uv run mypy --strict app/engines) || true; done
	@[ -f front/package.json ] && (cd front && npx tsc --noEmit) || true

contracts: ## Valide les contrats d'événements
	python3 scripts/check_contracts.py

docs-check: ## Vérifie la présence des specs exportées et les identifiants cités
	python3 scripts/docs_check.py

migrate: ## Migrations d'un service : make migrate SVC=nom
	cd services/$(SVC) && uv run alembic upgrade head

new-service: ## Crée un service : make new-service NAME=nom
	bash scripts/new-service.sh $(NAME)

recette: ## Charge le jeu de données de recette d'un lot : make recette LOT=N
	@[ -f scripts/recette/lot-$(LOT).py ] && uv run python scripts/recette/lot-$(LOT).py || echo "scripts/recette/lot-$(LOT).py à générer avec /recette $(LOT)"
	@echo "Checklist : docs/RECETTE/lot-$(LOT).md"

tick: ## Déclenche le planificateur quotidien de tous les services (recette)
	@for s in $(SERVICES); do $(COMPOSE_DEV) exec -T $$s uv run python -m app.scheduler tick 2>/dev/null || true; done

ci: lint typecheck contracts test ## Ce que la CI exécute
