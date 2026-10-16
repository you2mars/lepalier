SHELL := /bin/bash
.DEFAULT_GOAL := help
SERVICES := identity referentiel facturation charges-eau documents envois veille reporting
DEV_CERTS ?= deploy/nginx/certs
# .env (ignoré par git, sans secret) : adresse de la VM écrite par make dev-certs, lue par Docker Compose pour
# toute commande ; ENV_FICHIER ne sert qu'aux tests (fichier temporaire)
ENV_FICHIER ?= .env
# dépôt où make hooks installe le hook Git ; un autre dossier ne sert qu'aux tests
DEPOT_GIT ?= .
COMPOSE_DEV := docker compose -f compose.dev.yml
# Toutes les cibles sont des commandes : sans .PHONY, `make contracts` ne fait rien car le dossier contracts/ existe
.PHONY: help doctor dev-up dev-down dev-reinitialiser dev-certs dev-secrets logs test lint typecheck contracts docs-check migrate new-service test-gabarit test-plateforme images audit hooks recette recette-essais-echoues tick ci

help: ## Liste des cibles
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-16s\033[0m %s\n",$$1,$$2}'

doctor: ## Vérifie l'outillage local (docker, uv, node, gh, claude, jq) et installe les dépendances des scripts
	@for t in docker uv node npm gh claude jq; do command -v $$t >/dev/null && echo "ok   $$t" || echo "MANQUE $$t"; done
	@python3 -c "import jsonschema, yaml" 2>/dev/null && echo "ok   jsonschema + pyyaml" || echo "MANQUE python3-jsonschema python3-yaml (sudo apt install -y python3-jsonschema python3-yaml)"
	@docker compose version
	@$(MAKE) --no-print-directory hooks

hooks: ## Installe le hook Git qui refuse tout push direct sur main (règle 9 de CLAUDE.md)
	@cible="$(CURDIR)/scripts/git-hooks/pre-push"; hooks="$$(git -C $(DEPOT_GIT) rev-parse --absolute-git-dir)/hooks"; lien="$$hooks/pre-push"; \
	if [ -L "$$lien" ] && [ "$$(readlink -f "$$lien")" = "$$(readlink -f "$$cible")" ]; then echo "Hook pre-push déjà installé."; exit 0; fi; \
	if [ -e "$$lien" ] || [ -L "$$lien" ]; then echo "Un hook pre-push existe déjà ($$lien) : rien n'a été remplacé. Retirez-le ou reprenez-le à la main, puis relancez make hooks."; exit 1; fi; \
	mkdir -p "$$hooks" && ln -s "$$(realpath --relative-to="$$hooks" "$$cible")" "$$lien" && \
	echo "Hook pre-push installé : aucun push direct sur main (règle 9 de CLAUDE.md)."

dev-up: images ## Démarre la plateforme de développement (images locales) et attend qu'elle soit en bonne santé
	$(COMPOSE_DEV) up -d --wait --wait-timeout 240
dev-down: ## Arrête la plateforme (volumes conservés)
	$(COMPOSE_DEV) down
dev-reinitialiser: ## Efface les données de dev (base, flux NATS, Mailpit) et redémarre à vide : make dev-reinitialiser CONFIRMER=oui
	@test "$(CONFIRMER)" = oui || { echo "Rien n'a été effacé. Cette commande supprime les comptes, les événements et les e-mails de la plateforme de dev ; pour confirmer : make dev-reinitialiser CONFIRMER=oui"; exit 1; }
	$(COMPOSE_DEV) down --volumes --remove-orphans
	$(MAKE) dev-up
dev-certs: ## Certificat HTTPS auto-signé de la VM de dev et son adresse dans .env : make dev-certs [IP=192.168.1.20] [FORCE=1]
	@ip="$(IP)"; [ -n "$$ip" ] || ip=$$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<NF;i++) if($$i=="src") print $$(i+1)}'); \
	echo "$$ip" | grep -Eq '^([0-9]{1,3}\.){3}[0-9]{1,3}$$' || { echo "Adresse IP de la VM introuvable ou invalide : make dev-certs IP=…"; exit 1; }; \
	if [ -f $(DEV_CERTS)/dev.crt ] && [ -z "$(FORCE)" ]; then \
	  echo "Certificat déjà présent ($(DEV_CERTS)/dev.crt) ; FORCE=1 pour le régénérer."; \
	else \
	  mkdir -p $(DEV_CERTS) && (umask 077 && openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -nodes -days 365 \
	    -keyout $(DEV_CERTS)/dev.key -out $(DEV_CERTS)/dev.crt -subj "/CN=LePalier dev" \
	    -addext "subjectAltName=IP:$$ip,IP:127.0.0.1,DNS:localhost" \
	    -addext "basicConstraints=critical,CA:FALSE" -addext "extendedKeyUsage=serverAuth" 2>/dev/null) && \
	  chmod 644 $(DEV_CERTS)/dev.crt && \
	  echo "Certificat créé pour https://$$ip/ (valable 365 jours) dans $(DEV_CERTS)/" && \
	  openssl x509 -in $(DEV_CERTS)/dev.crt -noout -fingerprint -sha256 || exit 1; \
	fi; \
	adresse=$$(openssl x509 -in $(DEV_CERTS)/dev.crt -noout -ext subjectAltName | grep -oE 'IP Address:[0-9.]+' | head -1 | cut -d: -f2); \
	tmp=$$(mktemp); touch $(ENV_FICHIER); \
	{ grep -v '^LEPALIER_URL_PUBLIQUE=' $(ENV_FICHIER) || true; echo "LEPALIER_URL_PUBLIQUE=https://$$adresse"; } > "$$tmp" && \
	cat "$$tmp" > $(ENV_FICHIER) && rm -f "$$tmp" && \
	echo "Adresse de la VM pour les liens des e-mails : https://$$adresse (écrite dans $(ENV_FICHIER), lue par Docker Compose)."
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
	@for s in $(SERVICES) ; do if [ -d services/$$s ]; then (cd services/$$s && uv run ruff check . && uv run ruff format --check .) || exit 1; fi; done
	@if [ -f front/package.json ]; then cd front && npm run lint; fi

typecheck: ## mypy strict sur commun et les moteurs, tsc sur le front
	cd libs/commun && uv run mypy src/commun tests
	@for s in $(SERVICES) ; do if [ -d services/$$s/app/engines ]; then (cd services/$$s && uv run mypy --strict app/engines) || exit 1; fi; done
	@if [ -f front/package.json ]; then cd front && npx tsc --noEmit; fi

verifier-avant-push: lint typecheck ## Vérifications rapides lancées par le hook pre-push : lint, typage, vitest du front
	@if [ -f front/package.json ]; then cd front && npx vitest run; fi

audit: ## Audit des dépendances (pip-audit, npm audit) : échec sur une vulnérabilité haute, critique ou de gravité inconnue
	uv run --project libs/commun --with pip-audit python scripts/audit_python.py libs/commun $(foreach s,$(SERVICES),$(wildcard services/$(s)))
	@if [ -f front/package-lock.json ]; then cd front && npm audit --audit-level=high; fi

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
	@if [ -f scripts/recette/lot-$(LOT).py ]; then uv run python scripts/recette/lot-$(LOT).py; else echo "scripts/recette/lot-$(LOT).py à générer avec /recette $(LOT)"; fi
	@echo "Checklist : docs/RECETTE/lot-$(LOT).md"

recette-essais-echoues: ## R0-49 : 20 essais de connexion échoués sur un compte : make recette-essais-echoues EMAIL=adresse
	@test -n "$(EMAIL)" || { echo "Indiquez l'adresse du compte : make recette-essais-echoues EMAIL=adresse"; exit 1; }
	@uv run python scripts/recette/lot-0.py essais-echoues "$(EMAIL)"

tick: ## Planificateur quotidien de tous les services démarrés (recette) : make tick [JOUR=AAAA-MM-JJ]
	@# seuls les services démarrés sont concernés ; une erreur d'un service démarré arrête la commande
	@for s in $(SERVICES); do if $(COMPOSE_DEV) ps --services --status running | grep -qx "$$s"; then $(COMPOSE_DEV) exec -T $$s python -m app.scheduler tick $(if $(JOUR),--jour $(JOUR)) || exit 1; fi; done

images: ## Construit en local app-base, l'image de chaque service présent et celle du front (ghcr.io/you2mars/<nom>:dev)
	docker build -t ghcr.io/you2mars/app-base:latest -f deploy/docker/app-base.Dockerfile .
	@for s in $(SERVICES); do if [ -d services/$$s ]; then docker build -t ghcr.io/you2mars/$$s:dev -f services/$$s/Dockerfile . || exit 1; fi; done
	@if [ -f front/package.json ]; then docker build -t ghcr.io/you2mars/front:dev -f front/Dockerfile .; fi

test-plateforme: images front/node_modules/.package-lock.json ## Essai réel des images, de Compose et de nginx (Docker requis ; plusieurs minutes)
	LEPALIER_PLATEFORME=1 uv run --project libs/commun pytest -p no:cacheprovider scripts/tests/test_plateforme.py

# dépendances du front pour Playwright : réinstallées si package-lock.json est plus récent que la dernière installation
front/node_modules/.package-lock.json: front/package-lock.json
	cd front && npm ci

test-gabarit: ## Lint du gabarit, puis typage et tests d'un service généré dans un dossier temporaire
	@# dossier temporaire supprimé à la fin, réussite ou échec (sinon environ 200 Mo restent dans /tmp à chaque essai)
	@set -e; racine="$$(mktemp -d)"; trap 'rm -rf "$$racine"' EXIT; dossier="$$racine/veille"; \
	DESTINATION="$$dossier" bash scripts/new-service.sh veille >/dev/null; \
	echo "Service d'essai généré dans $$dossier"; \
	(cd "$$dossier" && uv sync -q --all-extras); \
	uv run --project "$$dossier" ruff check services/_template; \
	uv run --project "$$dossier" ruff format --check services/_template; \
	cd "$$dossier" && uv run mypy app migrations tests && uv run pytest -p no:cacheprovider --cov-fail-under=80

ci: lint typecheck contracts test audit ## Ce que la CI exécute
