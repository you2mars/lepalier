---
description: Crée un nouveau microservice à partir du gabarit services/_template, avec sa base, son rôle PostgreSQL, son entrée Compose, sa CI et son CLAUDE.md
disable-model-invocation: true
argument-hint: <nom-du-service>
---

Service : $ARGUMENTS

1. Vérifie que le nom figure dans la liste des huit services de `docs/SYNTHESE_SPECS.md` ; sinon demande confirmation.
2. Exécute `make new-service NAME=$ARGUMENTS` (copie du gabarit, remplacement du nom, création de la base et du rôle dans `deploy/postgres/init-databases.sh`, ajout dans `compose.dev.yml`, `compose.prod.yml` et `.github/workflows/ci.yml`).
3. Complète `services/$ARGUMENTS/CLAUDE.md` : responsabilité, tables maîtres et copies locales (§ 4.1 spec technique), événements publiés et consommés (§ 2), jobs (§ 6.1), routes (§ 10.1).
4. Lance `make test SVC=$ARGUMENTS` : le test `/internal/healthz` doit passer avant tout autre code.
5. Commit `chore($ARGUMENTS): squelette du service`.
