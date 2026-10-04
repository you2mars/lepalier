---
paths:
  - "contracts/**"
---
# Règles des contrats d'événements

- Un événement = `contracts/events/<agrégat>/<fait>.v<n>.json` (JSON Schema draft 2020-12), `additionalProperties: false`, montants en `string` avec `pattern` décimal, dates en `date`/`date-time`.
- L'enveloppe commune est `contracts/enveloppe.schema.json` ; le `payload` porte les montants figés, jamais seulement des identifiants.
- Changement additif (champ optionnel) : même version. Tout autre changement : nouvelle version `v<n+1>`, l'ancienne reste consommée jusqu'au retrait inscrit dans `contracts/CHANGELOG.md`.
- Chaque entrée du CHANGELOG indique : producteur, consommateurs, date, motif, date de retrait prévue de l'ancienne version.
- `make contracts` doit passer : schémas valides, exemples valides, graphe `consumers` sans cycle entre facturation, charges-eau, documents, envois ; les arêtes `ack` (retour qui clôt un état amont sans rien publier, ex. `document.emis` → facturation passe `quittancee`) sont déclarées à part dans `contracts/consumers.yaml` et vérifiées en revue.
