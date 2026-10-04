# Contrats d'événements

- `enveloppe.schema.json` : enveloppe commune à tous les événements (TEC-JOB-08).
- `events/<agrégat>/<fait>.v<n>.json` : schéma du `payload` d'un événement, avec `examples`.
- `enums.json` : ENUM métier partagés (statuts d'échéance, natures de charges, types de documents…), générés dans chaque service.
- `CHANGELOG.md` : historique des versions (producteur, consommateurs, motif, retrait prévu).
- `consumers.yaml` : déclaration producteur → consommateurs, utilisée pour vérifier l'absence de cycle.

Validation : `make contracts` (`scripts/check_contracts.py`) — schémas valides (draft 2020-12), exemples valides, montants en chaîne décimale, graphe sans cycle entre facturation, charges-eau, documents, envois.

Sujet NATS : `evt.<service>.<type>.v<n>` ; un flux JetStream par service producteur.
