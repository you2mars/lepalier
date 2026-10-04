# Service identity

## Responsabilité
(À compléter depuis SPEC_TECHNIQUE § 2 : ce que le service possède, publie, consomme.)

## Arborescence
- `app/api/` routes FastAPI (`/api/identity/…` côté nginx, `/internal/…` réseau interne)
- `app/engines/` fonctions pures (mypy strict, hypothesis)
- `app/services/` services applicatifs transactionnels (journal + outbox)
- `app/consumers/` consommateurs NATS (inbox)
- `app/jobs/` jobs planifiés (table `job`, clé d'idempotence)
- `app/models/` SQLAlchemy ; `migrations/` Alembic ; `tests/`

## Socle fourni par le gabarit (ne pas réécrire)
- `app/main.py` : `creer_app` câble, du plus externe au plus interne, `TraceMiddleware`, `OrigineMiddleware`, `ServiceInterneMiddleware`, `IdentiteMiddleware`, puis le format d'erreur commun. Une route s'ajoute sur l'app retournée ; droits par `exiger_role(...)`, appels internes par `exiger_service(...)`.
- Secrets (ADR 0007) : lus dans `/run/secrets` par `application()` ; un secret absent ou accessible au groupe ou aux autres arrête le démarrage. Ce service reçoit `cle_hmac_identite`, `mdp_base`, ses `empreinte_<appelant>_vers_identity` et ses `jeton_identity_vers_<appelé>` (couples déclarés dans `deploy/appels-internes.txt`).
- `app/models/socle.py` : `OUTBOX_SVC`, `INBOX_SVC`, `JOURNAL_SVC`, `JOBS` ; toute écriture métier fait donnée + `JOURNAL_SVC.ecrire` + `OUTBOX_SVC.ajouter` dans la même transaction.
- `app/worker.py` : relais outbox, jobs dus, planificateur (04:00 Europe/Paris), battement lu par `/internal/healthz`. Les jobs du service s'ajoutent dans `GESTIONNAIRES` et `planifier_jour`.

## Migrations
Exécutées avec le rôle propriétaire (`APP_MIGRATION_DATABASE_URL`, `make migrate SVC=identity`), jamais avec le rôle applicatif. Toute nouvelle table reçoit ses droits dans la migration qui la crée : `accorder([...], "lecture_ecriture")` ou `accorder([...], "ajout_seul")` pour une table immuable. Le DDL est écrit à la main ; `tests/test_migrations.py` vérifie qu'il correspond aux tables déclarées.

## Tables maîtres / copies locales
(§ 4.1) — Événements publiés / consommés (§ 2) — Jobs (§ 6.1) — Routes (§ 10.1)

## Commandes
`make test SVC=identity` · `make migrate SVC=identity` · `make logs SVC=identity`
