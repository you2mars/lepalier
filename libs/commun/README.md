# commun

Ce qui y entre : enveloppe d'événement (TEC-JOB-08), publication outbox et relais NATS, consommation inbox idempotente, middleware d'identité (vérification HMAC des en-têtes `X-User-Id`/`X-Role`/`X-Auth-Exp`/`X-Auth-Sig`, `require_role`), utilitaires `Decimal` (arrondi, plus fort reste), client HTTP interne avec propagation du `trace_id`, format d'erreur commun.

Ce qui n'y entre jamais : une règle métier, un modèle de table métier, un gabarit.

## Modules
| Module | Contenu | Exigences |
| --- | --- | --- |
| `ids` | `uuid7()` | TEC-DAT-01 |
| `decimales` | `vers_decimal`, `arrondir` (ROUND_HALF_UP), `en_chaine`, `repartir_plus_fort_reste`, type Pydantic `Montant` | TEC-STK-03 |
| `enveloppe` | `Enveloppe`, `nouvelle_enveloppe` (trace et causalité héritées de l'événement cause), sujet `evt.<service>.<type>.v<n>` | TEC-JOB-08 |
| `outbox` | `table_outbox`, `Outbox.ajouter` (dans la transaction métier), `Outbox.relayer` (ordre des id, `SKIP LOCKED`, `Nats-Msg-Id`), `assurer_flux` | TEC-DAT-04 |
| `inbox` | `table_inbox`, `Inbox.traiter`, `consommer_message` (accusé après commit, quarantaine après 5 livraisons) | TEC-DAT-04 |
| `identite` | `signer`/`verifier` (rotation de clé), `IdentiteMiddleware`, `identite_courante`, `exiger_role` | TEC-SEC-03, TEC-API-01 |
| `erreurs` | `ErreurApi`, `installer_gestionnaires` : `{code, message, details, trace_id}` en français | TEC-API-03, UX-5 |
| `origine` | `OrigineMiddleware` : refus des écritures d'une autre origine | TEC-SEC-07 |
| `trace` | `TraceMiddleware` (`X-Request-Id` et `X-Trace-Id` sur chaque réponse), `trace_id_courant` (OpenTelemetry, sinon requête en cours) | TEC-API-06 |
| `journal` | `table_journal`, `Journal.ecrire` (dans la transaction métier ; montants en chaîne, IP, `trace_id`) | APP-NF-05, TEC-SEC-10 |
| `jobs` | `table_job`, `table_planificateur`, `Jobs.planifier` (idempotent), `prendre` (`SKIP LOCKED`, verrou 15 min), `executer_un` (3 tentatives à 1, 10, 60 min ; `ErreurReseau` non comptée), `tick` (jours manqués, 04:00 Europe/Paris) | TEC-JOB-01, 02, 06, 07 |
| `secrets` | `lire_secret` (refus d'un secret absent, vide ou accessible au groupe ou aux autres), `lire_cles_hmac`, `lire_jeton`, `lire_empreintes` | ADR 0007 |
| `interne` | `ServiceInterneMiddleware`, `service_appelant`, `exiger_service` (jeton de service vérifié sur empreinte SHA-256) ; `ClientInterne` / `ClientInterneAsync` (`/internal/*` seulement, délai 5 s, une nouvelle tentative sur les lectures, aucune sur les écritures) | TEC-API-05, TEC-SEC-04 |

Ordre des middlewares dans un service (du plus externe au plus interne) : `TraceMiddleware`, `OrigineMiddleware`, `ServiceInterneMiddleware`, `IdentiteMiddleware`. Avec Starlette, `add_middleware` place le dernier ajouté à l'extérieur : les ajouter dans l'ordre inverse.

## Tests
`make test` (ou `cd libs/commun && uv run pytest`) ; les tests marqués `integration` démarrent PostgreSQL 16 et NATS par Testcontainers (Docker requis).
