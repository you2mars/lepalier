# commun

Ce qui y entre : enveloppe d'événement (TEC-JOB-08), publication outbox et relais NATS, consommation inbox idempotente, middleware d'identité (vérification HMAC des en-têtes `X-User-Id`/`X-Role`/`X-Auth-Exp`/`X-Auth-Sig`, `require_role`), utilitaires `Decimal` (arrondi, plus fort reste), client HTTP interne avec propagation du `trace_id`, format d'erreur commun.

Ce qui n'y entre jamais : une règle métier, un modèle de table métier, un gabarit.
