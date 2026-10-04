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
| `trace` | `trace_id_courant` (OpenTelemetry, sinon `X-Request-Id`) | TEC-API-06 |

Pas encore livré : client HTTP interne (`/internal/*`, jeton de service, TEC-API-05, TEC-SEC-04), prévu quand un service en aura besoin.

## Tests
`make test` (ou `cd libs/commun && uv run pytest`) ; les tests marqués `integration` démarrent PostgreSQL 16 et NATS par Testcontainers (Docker requis).
