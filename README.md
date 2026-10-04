# LePalier — gestion locative de la SCI (monorepo)

Application de gestion locative d'un immeuble (~20 lots) détenu par une SCI : microservices Python/FastAPI, NATS JetStream, PostgreSQL, Next.js, nginx, hébergée sur un VPS Hetzner. Développée avec Claude Code.

## Démarrer
1. VM Debian 13 : `sudo bash scripts/bootstrap-vm-dev.sh $USER` puis nouvelle session shell.
2. `gh auth login`, cloner, `make doctor`.
3. Exporter les deux specs en Markdown dans `docs/` (voir `docs/README.md`), puis `make docs-check`.
4. `make dev-up` (postgres, nats, mailpit), `make contracts`.
5. `claude` à la racine, puis `/lot 0`.

## Repères
- `CLAUDE.md` : instructions pour Claude Code (lu à chaque session).
- `docs/PLAN_DE_DEV.md` : les 8 lots, rituels, jalons. `docs/RECETTE/` : recettes manuelles. `docs/UX_CHARTE.md` : ergonomie.
- `.claude/skills/` : `/lot`, `/recette`, `/revue-ux`, `/contrat`, `/nouveau-service`, `/dod`. `.claude/agents/` : `ux-reviewer`, `gardien-contrats`, `auditeur-tests`, `redacteur-recette`.
- `contracts/` : schémas d'événements (à écrire avant le code). `services/_template/` : gabarit de service.

## Secrets
Jamais dans le dépôt. Dev : `.env` local (ignoré) ; prod : `/run/secrets` et base chiffrée (TEC-SEC-08).
