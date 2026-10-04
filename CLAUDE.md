# LePalier — instructions projet pour Claude Code

Application de gestion locative d'un immeuble d'environ 20 lots détenu par une SCI à l'IR,
en microservices (8 services Python/FastAPI, bus NATS JetStream, PostgreSQL une base par service,
front Next.js 15 en BFF, nginx en frontal), hébergée sur un VPS Hetzner. Utilisateurs : gérant,
associés, opérateur — dont des personnes peu à l'aise avec l'informatique.

## Documents de référence (à lire avant toute tâche non triviale)
- @docs/SYNTHESE_SPECS.md — résumé des specs (contexte, architecture, règles clés, décisions)
- @docs/UX_CHARTE.md — ergonomie : obligatoire pour tout écran, formulaire, message, document
- docs/PLAN_DE_DEV.md — lots, ordre de construction, critères de sortie (lu par `/lot`)
- docs/DEFINITION_OF_DONE.md — ce qui rend un lot « terminé » (lu par `/dod`)
- docs/SPEC_FONCTIONNELLE.md et docs/SPEC_TECHNIQUE.md — specs complètes (exportées des Claude Docs ; lis la section concernée, pas tout)
- docs/LEXIQUE.md — vocabulaire métier et libellés d'interface imposés
- docs/RECETTE/lot-N.md — recette manuelle validée par Youssef à chaque lot

## Commandes
- `make help` liste toutes les cibles et leurs paramètres (`SVC=`, `LOT=`, `NAME=`).

## Conventions
- `libs/commun/` (enveloppe, outbox/inbox, middleware d'identité, décimales) : aucune logique métier.
- Vocabulaire métier en français (tables, événements, routes, libellés) ; technique en anglais (variables de bas niveau, bibliothèques). Référence : docs/LEXIQUE.md.
- Montants : `Decimal` / `NUMERIC(12,2)` partout, sérialisés en chaîne dans le JSON ; jamais `float`.
- Dates civiles en `date`, horodatages `TIMESTAMPTZ` UTC ; décisions calendaires en Europe/Paris depuis `now()` de la base.
- Identifiants UUID v7 générés par le service propriétaire ; suppression logique uniquement.
- Un service ne lit jamais la base d'un autre : copies locales `ref_*` alimentées par événements.
- Toute écriture passe par un service applicatif qui journalise et écrit l'outbox dans la même transaction.
- Événements : nommage `<agrégat>.<fait>` au passé, schéma JSON versionné dans `contracts/` AVANT le code, changement additif seulement.
- Python : ruff (format + lint), mypy strict sur `app/engines`, pytest + hypothesis pour les moteurs.
- Commits : Conventional Commits en français (`feat(facturation): …`), un lot = une branche `lot/N-nom`.

## Règles absolues
1. Jamais de secret dans le dépôt (.env, clés, mots de passe) ; ne lis pas les fichiers `.env*`.
2. Ne jamais contourner la machine à états des échéances : `payee` n'existe que dans la saisie de paiement.
3. Un contrat d'événement se modifie en ajoutant une version, jamais en place.
4. Pas de migration destructive dans la même livraison (expansion puis contraction).
5. Toute fonctionnalité visible = passage par la charte UX + ligne de recette manuelle + test automatisé.
6. Demande avant toute commande destructive (`docker compose down -v`, `git push --force`, suppression de données).
7. Interface, messages, documents et erreurs en français clair, sans jargon technique (voir UX_CHARTE § 3).

## Processus d'un lot (voir docs/PLAN_DE_DEV.md)
1. `/lot N` : lire le lot, proposer l'ordre des tâches, créer la branche.
2. Pour chaque fonctionnalité : contrat → migration → moteur + tests → consommateurs/jobs → routes → écran (après revue UX de la maquette) → test de chorégraphie.
3. `/recette N` : compléter docs/RECETTE/lot-N.md (cas manuels, données de test) ; Youssef valide chaque ligne.
4. `/revue-ux <écran>` sur chaque écran livré ; corriger avant de passer au suivant.
5. `/dod N` : vérifier la Definition of Done, mettre à jour docs et CHANGELOG, taguer.

## Quand tu hésites
- Une règle métier ambiguë → cite la spec (APP-… / TEC-…) et pose la question avant de coder.
- Un choix d'interface → applique la charte ; si elle ne tranche pas, propose deux maquettes textuelles.
- Une donnée manquante pour un consommateur → report + quarantaine, jamais une valeur inventée.
