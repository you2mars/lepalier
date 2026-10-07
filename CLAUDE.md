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

## Décisions figées (ne pas rouvrir sans demander)
- Architecture : microservices (8 services, une base PostgreSQL par service, copies locales ref_*), ADR 0001.
- Bus : NATS JetStream, outbox/inbox. Pas de RabbitMQ, Kafka ni Redis.
- Passerelle et frontal Internet : nginx (auth_request vers identity, TLS Let's Encrypt, limites de débit, en-têtes de sécurité), ADR 0003. Pas de Traefik, Caddy ni Kong.
- Hébergement : VPS Hetzner CPX32 dédié, données sur volume LUKS à déverrouillage manuel via WireGuard, ADR 0002. Pas de Tang/Clevis.
- Livraison : GitHub privé, images dans GHCR, runner auto-hébergé sur le VPS en mode pull, jamais de SSH entrant depuis la CI, ADR 0004.
- Front : Next.js 15 en BFF. Services : Python 3.12, FastAPI, SQLAlchemy 2, Alembic.
- Second facteur : TOTP en v1.
- Décisions encore ouvertes (poser la question à Youssef, ne pas trancher seul) : bannissement (CrowdSec ou fail2ban), WAF, certificats DNS-01 ou HTTP-01, seconde cible de sauvegarde, collecteur PISTE, résumé de veille par modèle local, offre La Poste v2, environnement de préproduction (second VPS Hetzner temporaire ou VM Proxmox, décision n° 15 de SPEC_TECHNIQUE § 14, à trancher avant le lot 2).
- Toute proposition qui contredit une décision figée passe par une question à Youssef puis un nouvel ADR dans docs/ADR/, jamais par un choix silencieux.

## Règles absolues
1. Jamais de secret dans le dépôt (.env, clés, mots de passe) ; ne lis pas les fichiers `.env*`.
2. Ne jamais contourner la machine à états des échéances : `payee` n'existe que dans la saisie de paiement.
3. Un contrat d'événement se modifie en ajoutant une version, jamais en place.
4. Pas de migration destructive dans la même livraison (expansion puis contraction).
5. Toute fonctionnalité visible = passage par la charte UX + ligne de recette manuelle + test automatisé.
6. Demande avant toute commande destructive (`docker compose down -v`, `git push --force`, suppression de données) ; aucune suppression de fichier ou de dossier hors de /tmp sans mon accord, quel que soit l'outil (rm, shutil, find -delete, git clean…).
7. Interface, messages, documents et erreurs en français clair, sans jargon technique (voir UX_CHARTE § 3).
8. Le dépôt fait foi pour les textes validés (libellés, e-mails, messages, vérifiés mot pour mot par les tests) ; en cas de doute, demande à Youssef, ne relis jamais les transcriptions de session.
9. Jamais de push sur main ni de fusion sans CI verte (la protection de branche de GitHub n'est pas disponible : hook `pre-push` installé par `make hooks`).
10. Échanges avec Youssef en français, tous les messages, y compris les messages intermédiaires, les bilans, les résumés et après un compactage de la conversation.

## Processus d'un lot (voir docs/PLAN_DE_DEV.md)
1. `/lot N` : lire le lot, proposer l'ordre des tâches, créer la branche.
2. Pour chaque fonctionnalité : contrat → migration → moteur + tests → consommateurs/jobs → routes → écran (après revue UX de la maquette) → test de chorégraphie. Les maquettes textuelles d'un lot sont dans docs/MAQUETTES/lot-N.md (jamais seulement dans /tmp, effacé au redémarrage de la VM) ; elles y sont tenues à jour à chaque décision.
3. `/recette N` : compléter docs/RECETTE/lot-N.md (cas manuels, données de test) ; Youssef valide chaque ligne. Les lignes de recette d'un écran sont écrites dès qu'il est terminé, diff montré à Youssef avant le commit.
4. `/revue-ux <écran>` sur chaque écran livré ; corriger avant de passer au suivant.
5. `/dod N` : vérifier la Definition of Done, mettre à jour docs et CHANGELOG, taguer.

## Quand tu hésites
- Une règle métier ambiguë → cite la spec (APP-… / TEC-…) et pose la question avant de coder.
- Un choix d'interface → applique la charte ; si elle ne tranche pas, propose deux maquettes textuelles.
- Une donnée manquante pour un consommateur → report + quarantaine, jamais une valeur inventée.
