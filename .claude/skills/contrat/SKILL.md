---
description: Crée ou fait évoluer un contrat d'événement (schéma JSON, exemple, changelog, tests de contrat) avant tout code producteur ou consommateur
argument-hint: <service producteur> <agrégat.fait> [v<n>]
---

Arguments : $ARGUMENTS

1. Lis `contracts/README.md`, `contracts/enveloppe.schema.json` et `.claude/rules/contracts.md`.
2. Détermine si la demande est additive (même version) ou incompatible (nouvelle version). En cas de doute, choisis la nouvelle version et explique.
3. Écris le schéma `contracts/events/<agrégat>/<fait>.v<n>.json` : `$id`, `title`, `description`, `additionalProperties: false`, montants en chaîne décimale (`pattern` `^-?\d+\.\d{2}$`), dates ISO, identifiants UUID, et un exemple valide dans `examples`.
4. Mets à jour `contracts/CHANGELOG.md` (producteur, consommateurs attendus, motif, date, retrait prévu de l'ancienne version).
5. Ajoute le test de contrat : l'exemple valide le schéma, l'ancienne version reste valide, le graphe producteur → consommateur reste sans cycle (`make contracts`).
6. Ne touche pas au code des services dans cette étape ; indique les consommateurs à modifier ensuite.
