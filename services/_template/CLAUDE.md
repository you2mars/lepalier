# Service __SERVICE__

## Responsabilité
(À compléter depuis SPEC_TECHNIQUE § 2 : ce que le service possède, publie, consomme.)

## Arborescence
- `app/api/` routes FastAPI (`/api/__SERVICE__/…` côté nginx, `/internal/…` réseau interne)
- `app/engines/` fonctions pures (mypy strict, hypothesis)
- `app/services/` services applicatifs transactionnels (journal + outbox)
- `app/consumers/` consommateurs NATS (inbox)
- `app/jobs/` jobs planifiés (table `job`, clé d'idempotence)
- `app/models/` SQLAlchemy ; `migrations/` Alembic ; `tests/`

## Tables maîtres / copies locales
(§ 4.1) — Événements publiés / consommés (§ 2) — Jobs (§ 6.1) — Routes (§ 10.1)

## Commandes
`make test SVC=__SERVICE__` · `make migrate SVC=__SERVICE__` · `make logs SVC=__SERVICE__`
