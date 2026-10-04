---
description: Vérifie la Definition of Done d'un lot, produit le rapport de clôture et prépare le tag
disable-model-invocation: true
argument-hint: <numéro de lot>
---

Lot : $ARGUMENTS

1. Parcours `docs/DEFINITION_OF_DONE.md` point par point et vérifie chacun avec des preuves (commande exécutée, fichier, ligne de recette signée) ; délègue aux sous-agents `auditeur-tests` et `gardien-contrats` les vérifications automatisables.
2. Vérifie que `docs/RECETTE/lot-$ARGUMENTS.md` n'a aucune ligne non validée par Youssef et que les tests utilisateurs prévus ont un compte rendu.
3. Liste les écarts restants ; si un point bloquant manque, ne clôture pas.
4. Mets à jour `CHANGELOG.md` (racine) et la section « Journal du lot » du plan.
5. Propose le message de PR vers `main` et le tag `lot-$ARGUMENTS` ; ne pousse pas toi-même.
