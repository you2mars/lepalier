---
description: Démarre un lot du plan de développement : lit le lot, propose l'ordre des tâches, crée la branche et le suivi
disable-model-invocation: true
argument-hint: <numéro de lot>
---

Lot demandé : $ARGUMENTS

1. Lis `docs/PLAN_DE_DEV.md` (section « Lot $ARGUMENTS »), `docs/DEFINITION_OF_DONE.md` et la recette `docs/RECETTE/lot-$ARGUMENTS.md`.
2. Vérifie que le lot précédent est clos (tag `lot-<N-1>` présent, recette signée). Sinon, dis-le et arrête-toi.
3. Crée la branche `lot/$ARGUMENTS-<nom-court>` depuis `main`.
4. Produis un plan de travail ordonné selon la règle « contrat → migration → moteur + tests → consommateurs/jobs → routes → écran (après revue UX) → chorégraphie », avec pour chaque tâche : service concerné, exigences APP-/TEC- couvertes, tests automatisés prévus, ligne(s) de recette manuelle correspondantes, point UX à surveiller.
5. Liste les questions ouvertes (specs ambiguës, décisions § 14 non prises) AVANT de coder, et attends la réponse de Youssef.
6. Ouvre un suivi dans `docs/PLAN_DE_DEV.md` (section « Journal du lot ») avec la date et le plan.
