---
paths:
  - "services/**/*.py"
  - "libs/**/*.py"
---
# Règles Python (services et lib commun)

- Python 3.12, `from __future__ import annotations`, typage complet ; `mypy --strict` passe sur `app/engines/**`.
- Les moteurs (`app/engines/`) sont des fonctions pures sur `Decimal` et `date` : aucun accès base, réseau ou horloge ; l'heure et les données sont passées en paramètres.
- Arrondis : `ROUND_HALF_UP` à 2 décimales, répartition « au centime, somme exacte » (méthode du plus fort reste), jamais de `float`.
- Les services applicatifs (`app/services/`) ouvrent une transaction, écrivent la donnée, le `journal` et l'`outbox` ensemble, puis commit.
- Consommateurs (`app/consumers/`) : vérifier `inbox` avant tout effet, accuser après commit, lever pour relivrer, quarantaine après 5 essais.
- Jobs (`app/jobs/`) : clé d'idempotence obligatoire, `SKIP LOCKED`, verrou 15 min, journal du résultat (créé / ignoré / échec).
- Routes (`app/api/`) : Pydantic `extra='forbid'`, montants en chaîne décimale, `require_role`, `Idempotency-Key` sur les écritures, erreurs `{code, message, details, trace_id}`.
- Aucune requête SQL concaténée ; SQLAlchemy 2 paramétré ; migrations Alembic une par changement, réversibles, non destructives.
- Logs structurés sans donnée personnelle (identifiants seulement).
