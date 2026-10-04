---
description: Audite un écran, un formulaire, un message ou un document PDF contre la charte UX et produit des constats hiérarchisés avec correctifs
argument-hint: <chemin du composant, de la page ou du gabarit>
---

Cible : $ARGUMENTS

Délègue au sous-agent `ux-reviewer` l'audit de la cible contre `docs/UX_CHARTE.md` et `docs/LEXIQUE.md`, puis :
1. Présente les constats par sévérité : bloquant (empêche un utilisateur non technique de finir la tâche), majeur (erreur probable ou confusion), mineur (polissage).
2. Pour chaque constat : la règle de la charte enfreinte (numéro), ce que voit l'utilisateur, le correctif concret (libellé exact, composant, comportement).
3. Vérifie la checklist de sortie de la charte (§ 8) et liste les points non vérifiables sans test utilisateur.
4. Propose, si l'écran est nouveau, le scénario de test utilisateur à 3 tâches à faire passer à un associé.
5. Applique les correctifs bloquants et majeurs avant de rendre la main ; les mineurs sont listés dans le journal du lot.
