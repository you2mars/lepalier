---
description: Prépare ou complète la recette manuelle d'un lot (cas de test manuels, données de test, script de préparation) que Youssef valide ligne à ligne
argument-hint: <numéro de lot>
---

Lot : $ARGUMENTS

1. Lis `docs/RECETTE/lot-$ARGUMENTS.md` et les fonctionnalités réellement livrées sur la branche (git log, diff avec main).
2. Pour chaque fonctionnalité livrée, assure-toi qu'il existe au moins une ligne de recette avec : identifiant `R$ARGUMENTS-nn`, pré-requis, étapes précises (clics, valeurs saisies), résultat attendu observable (écran, PDF, e-mail Mailpit, ligne de journal), colonne « Validé le / par », colonne « Commentaire ».
3. Ajoute les cas d'ergonomie (section « Ergonomie et accessibilité ») : tâche réalisée par un associé sans aide, lisibilité des messages, mobile, clavier, impression.
4. Ajoute les cas négatifs (données invalides, service arrêté, double soumission, droits insuffisants).
5. Génère ou mets à jour `scripts/recette/lot-$ARGUMENTS.py` qui charge un jeu de données reproductible (immeuble, lots, locataires, échéances) sur la plateforme de preprod, idempotent.
6. Ne coche jamais une ligne toi-même : seul Youssef remplit « Validé le / par ».
