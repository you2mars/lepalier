# Plan de développement

Conforme à `SPEC_TECHNIQUE.md` § 13.2 (huit lots). Chaque lot laisse une plateforme utilisable, se termine par une recette manuelle validée par Youssef, une revue UX et un test utilisateur avec un associé, puis un tag.

## 0. Comment travailler avec ce plan
- Un lot = une branche `lot/N-nom`, démarrée par `/lot N`, close par `/dod N`, fusionnée par PR sur `main`, taguée `lot-N`.
- Ordre de construction à l'intérieur d'un lot, pour chaque fonctionnalité : **contrat d'événement → migration → moteur + tests → consommateurs et jobs → routes → écran (après revue UX de la maquette textuelle) → test de chorégraphie → ligne de recette**.
- Trois boucles de validation à chaque lot, dans cet ordre : tests automatisés verts (CI) → recette manuelle (Youssef, `docs/RECETTE/lot-N.md`) → test utilisateur (associé, protocole `UX_CHARTE.md` § 7). Un KO renvoie au développement avec un test de non-régression.
- Les estimations sont des ordres de grandeur en journées de travail effectif avec Claude Code, hors attente de recette ; elles seront recalées après le lot 1.
- Toute question sur une règle métier se règle en citant APP-/TEC- ; toute décision nouvelle donne un ADR.

## 1. Préparation (avant le lot 0)
| Étape | Détail | Preuve |
| --- | --- | --- |
| P1 VM de développement | Debian 13, `scripts/bootstrap-vm-dev.sh` (Docker, uv, Node 22, gh, Claude Code), 4 vCPU / 8 Go / 60 Go conseillés | `make doctor` vert |
| P2 Dépôt GitHub | Dépôt privé, 2FA avec clé matérielle, branche `main` protégée (PR + CI), `gh auth login` | Première PR fusionnée (ce squelette) |
| P3 Specs dans le dépôt | Export Markdown des deux Claude Docs dans `docs/` (voir `docs/README.md`) | `make docs-check` vert |
| P4 Comptes externes | Nom de domaine (sous-domaine dédié, CAA), hébergeur DNS avec API (DNS-01), compte Hetzner (commande du CPX32 au lot 2), stockage objet pour la seconde sauvegarde | Décisions § 14 à jour |
| P5 Lecture | `CLAUDE.md`, `SYNTHESE_SPECS.md`, `UX_CHARTE.md`, `LEXIQUE.md` lus par Youssef ; questions ouvertes consignées | Issue « questions ouvertes » |

## 2. Lots

### Lot 0 — Plateforme et identity (≈ 6–8 j)
**Objectif** : socle technique sur lequel tous les services s'appuient, et connexion sécurisée.
**Périmètre** : monorepo, image `app-base`, lib `commun` (enveloppe TEC-JOB-08, outbox/inbox TEC-DAT-04, middleware d'identité TEC-SEC-03, décimales TEC-STK-03), Compose dev (postgres, nats, mailpit), `contracts/` (enveloppe, enums, validation `make contracts`), CI (lint, typage, tests, contrats, build), service `identity` complet (TEC-SEC-01/02, APP-USR-01/05), nginx dev avec `auth_request`, front Next.js minimal (connexion, TOTP, accueil « À faire » vide), observabilité en dev (Grafana optionnel).
**Tâches** : 1 lib commun + tests ; 2 gabarit de service et `make new-service` ; 3 contrats de base ; 4 identity (modèle, Argon2id, sessions, TOTP, codes de secours, invitations, rôles, journal) ; 5 nginx dev + BFF ; 6 CI GitHub ; 7 écrans connexion / TOTP / invitation / mot de passe (revue UX) ; 8 recette.
**Tests automatisés** : commun (enveloppe, outbox relayée, inbox idempotente, HMAC), identity (verrouillage, rotation de session, TOTP fenêtre ±1, codes de secours à usage unique), nginx (en-têtes forgés refusés, 401 sans cookie), Playwright connexion.
**Recette manuelle** : `RECETTE/lot-0.md`. **Test utilisateur** : un associé s'invite, active son compte et son TOTP sur son téléphone, se connecte, se déconnecte.
**Sortie** : un associé se connecte à LePalier sur la VM de dev (HTTPS auto-signé, réseau local) ; traces visibles ; `make test` vert.

### Lot 1 — referentiel + documents (≈ 10–12 j) — jalon « bail imprimé »
**Périmètre** : `referentiel` (SCI, associés, immeuble, lots, DPE/diagnostics, locations + versions, locataires, garants, clé de répartition ; APP-REF-01…07, APP-SCI-01…04, événements `location.*`, `lot.*`, `cle.changee`, `locataire.modifie`), `documents` (registre de gabarits, WeasyPrint PDF/A, stockage par empreinte, bail vide + annexes, notice, EDL entrée/sortie, caution, grille de vétusté, attestation de dépôt, accord quittance démat., publipostage ; APP-DOC-01…08, TEC-DOC-01…10, TEC-FIL-01…04), écrans : immeuble et appartements, fiche bail, fiche locataire, génération guidée d'un document, visionneuse PDF, état des lieux mobile.
**Tâches** : contrats `location.*` → migrations → services applicatifs → routes → écrans (maquettes textuelles validées en revue UX avant codage) → gabarits PDF (relus avec UX-31…34) → chorégraphie `location.demarree` → `document.emis` → `ref_document`.
**Tests** : droits (gérant/associé/opérateur), exclusion de chevauchement de locations, contrôles APP-REF-02 (DPE, dépôt ≤ plafond, inventaire si meublé), rendu de chaque gabarit avec contexte de référence, PDF/A, Playwright « créer un bail et imprimer ».
**Recette** : `RECETTE/lot-1.md`. **Test utilisateur** : un associé retrouve le bail et le locataire de l'appartement 12 et ouvre le PDF ; Youssef crée un bail complet sur mobile et ordinateur.
**Sortie** : un bail vide complet et ses annexes imprimés depuis l'app pour un vrai appartement (données réelles saisies en preprod puis migrées en prod au lot 2).

### Lot 2 — facturation + envois (≈ 12–15 j) — jalon « premier cycle mensuel réel »
**Périmètre** : `facturation` (échéances, prorata, machine à états, paiements, reçus, retards, rappels ; APP-ECH-01…10, TEC-CAL-01…07), `envois` (file, routage, SMTP, lot d'impression DL, registre, recommandés manuels, `ManualPostal`, `FakePostal` ; APP-ENV-01…07, TEC-ENV-01…10), `documents` (avis, quittance, reçu, attestation de loyer, relances, mise en demeure), `reporting` minimal (tâches « À faire », rapprochement TEC-CAL-19), chorégraphies cycle mensuel et paiement → quittance (§ 5.6), écrans : loyers du mois (saisie rapide de paiement mobile), fiche loyer, envois et lot d'impression, registre.
**Infrastructure** : commande du VPS Hetzner, `scripts/bootstrap-vps.sh` (Debian, LUKS, Docker, WireGuard, nftables, nginx, certbot, CrowdSec/fail2ban, runner GitHub), `compose.prod.yml`, sauvegardes (TEC-OPS-03), première restauration testée, DNS. **Mise en production** à la fin du lot avec les données réelles.
**Tests** : propriétés et cas figés des moteurs (février bissextile, entrée le 31, surplus, annulation), idempotence des jobs, chorégraphies avec `documents` arrêté puis redémarré, routage par type et accord démat., SMTP Mailpit, droits (recommandé réservé au gérant), Playwright « marquer payé → quittance reçue ».
**Recette** : `RECETTE/lot-2.md`. **Test utilisateur** : l'opérateur enregistre trois paiements sur mobile ; un associé lit « qui n'a pas payé » ; Youssef imprime le lot papier du mois et poste un recommandé en saisissant le numéro.
**Recette reportée du lot 0** : accès depuis Internet et R0-09.
**Sortie** : les avis de loyer partent automatiquement, les quittances suivent la validation manuelle, les locataires reçoivent e-mail ou papier ; prod en service.

### Lot 3 — charges-eau + veille (IRL) (≈ 10–12 j) — jalon « première régularisation »
**Périmètre** : `charges-eau` (relevés avec photo, factures d'eau, charges par nature, clé, répartition TEC-CAL-08…12, régularisation TEC-CAL-13…15, forfait meublé, alerte fuite ; APP-EAU-01…05, APP-CHG-01…07), `veille` partie IRL (collecteur INSEE + contrôle service-public, table `irl`, `irl.publie` ; TEC-VJ-06), `facturation` révision IRL (TEC-CAL-16…18, APP-AUT-02), `referentiel` jobs assurance / congé / diagnostics (APP-AUT-01, § 7), `documents` lettres de révision, régularisation, demandes d'attestation, écrans : relevé d'eau mobile, eau et charges, simulation de régularisation (UX-28 : la simulation explique chaque ligne), révision à valider.
**Tests** : propriétés de répartition (somme exacte, plus fort reste), ventilation de facture sur 3 périodes, remplacement de compteur, régularisation avec et sans forfait, IRL manquant, révision perdue après un an, chorégraphie régularisation → rappel → lettre.
**Recette** : `RECETTE/lot-3.md`. **Test utilisateur** : un associé comprend le décompte de régularisation d'un appartement sans aide ; l'opérateur saisit un relevé avec photo sur mobile.
**Sortie** : régularisation annuelle émise pour tous les appartements à provisions, révisions IRL appliquées.

### Lot 4 — reporting complet (≈ 8–10 j) — jalon « clôture d'exercice »
**Périmètre** : projections et vues matérialisées (TEC-DAT-06), tableau de bord global et par locataire (APP-TB-01…07, § 10.2–10.4 ; graphes ECharts avec titres-conclusions UX-28), exports CSV et état 2072 avec quotes-parts (APP-SCI-04, APP-NF-09), rapprochement quotidien complet, journal consolidé, commentaires internes (APP-USR-06), notifications aux associés (APP-USR-04).
**Tests** : formules § 10.4 contre jeux figés, rejeu complet de `reporting` depuis la séquence 1, droits (opérateur sans quotes-parts), Playwright dashboards, export 2072 ligne à ligne contre un cas calculé à la main.
**Recette** : `RECETTE/lot-4.md`. **Test utilisateur** : deux associés répondent à « combien a rapporté l'immeuble cette année et quelle est ma part ? » en moins de 2 minutes sans aide.
**Sortie** : état 2072 reportable sans comptable ; tableaux de bord utilisés par les associés.

### Lot 5 — veille complète + option meublée (≈ 6–8 j)
**Périmètre** : collecteurs RSS/JO (PISTE si décidé), scoring, qualification, alertes vers « À faire », résumé LLM local optionnel (TEC-VJ-01…07) ; gabarits meublé, inventaire, forfait, garde-fou fiscal APP-SCI-05 avec avertissement bloquant ; écrans veille et activation du meublé.
**Tests** : déduplication, scoring, quarantaine source en échec, part meublée et alerte, inventaire obligatoire. **Recette** : `RECETTE/lot-5.md`. **Test utilisateur** : Youssef qualifie trois alertes ; un associé comprend l'avertissement fiscal.

### Lot 6 — résilience et exploitation (≈ 5–7 j)
**Périmètre** : procédures `rebuild <svc>`, restauration cohérente scriptée sur VPS neuf (TEC-OPS-04/05), alertes Prometheus complètes (TEC-OPS-06), quarantaine et rejeu, second canal d'alerte, revue sécurité externe (TEC-WEB-11), `testssl.sh`, documentation d'exploitation (`docs/EXPLOITATION.md` : redémarrage et déverrouillage LUKS, mise à jour, restauration, rotation des secrets).
**Tests** : exercice de restauration chronométré (< 2 h), coupure de NATS pendant une chorégraphie, perte d'un service 24 h puis rattrapage. **Recette** : `RECETTE/lot-6.md` (exercices d'exploitation signés).

### Lot 7 — v2 postale (≈ 5–8 j, après contrat La Poste)
**Périmètre** : `LaPostePostal` (quote, deposit, track, fetch_proofs), webhook `/hooks/laposte`, correspondance des statuts, coûts, écran envois enrichi. **Tests** : contrat d'adaptateur contre `FakePostal` et bac à sable La Poste, reprise en mode manuel. **Recette** : `RECETTE/lot-7.md`.

## 3. Rituels
- **Début de lot** (`/lot N`) : relecture des exigences, questions ouvertes posées avant de coder, maquettes textuelles des écrans soumises à revue UX.
- **Pendant le lot** : une PR par fonctionnalité ou groupe cohérent ; CI verte avant revue ; `/revue-ux` sur chaque écran ; `/recette N` tenu à jour au fil de l'eau, pas à la fin.
- **Recette manuelle** : Youssef déroule `docs/RECETTE/lot-N.md` sur la preprod chargée par `make recette LOT=N`, remplit « Validé le / par » ou « KO + commentaire » ; un KO ouvre une issue `recette` et donne un test de non-régression avant correction.
- **Test utilisateur** : protocole UX § 7, compte rendu dans la recette ; les mots employés par les participants enrichissent le LEXIQUE.
- **Fin de lot** (`/dod N`) : DoD vérifiée avec preuves, CHANGELOG, tag, déploiement preprod puis prod (à partir du lot 2) avec restauration de sauvegarde testée.
- **Mensuel en exploitation** : vérifier les alertes, la sauvegarde, les mises à jour de sécurité, les tâches en quarantaine.

## 4. Gestion des écarts
- Bug trouvé en recette ou en prod : issue GitHub (`bug`, lot concerné), test qui échoue, correctif, mention dans le CHANGELOG.
- Changement de règle métier : mise à jour de la spec (Claude Doc puis export), ADR si c'est une décision, puis code.
- Dette assumée : section « Dette » du journal du lot, avec le lot prévu pour la résorber.

## 5. Jalons
| Jalon | Lot | Ce que l'on peut faire |
| --- | --- | --- |
| J0 Connexion | 0 | Un associé se connecte à LePalier sur la VM de dev (HTTPS auto-signé, réseau local) |
| J1 Bail imprimé | 1 | Rédiger et imprimer un bail et ses annexes |
| J2 Cycle mensuel en prod | 2 | Avis, paiements validés, quittances, envois papier et e-mail, sauvegardes |
| J3 Régularisation | 3 | Relevés d'eau, charges, régularisation, révisions IRL |
| J4 Clôture | 4 | Tableaux de bord, export 2072, quotes-parts |
| J5 Veille et meublé | 5 | Alertes qualifiées, option meublée sécurisée |
| J6 Exploitation sereine | 6 | Restauration testée, alertes, revue sécurité |
| J7 Recommandés en ligne | 7 | API La Poste |

## 6. Journal des lots
_(tenu par Claude Code via `/lot` et `/dod` : date, plan, décisions, dette, résultats de recette et de test utilisateur)_

### Lot 0
- Démarré le : 4 octobre 2026, branche `lot/0-plateforme`
- Plan (ordre « contrat → migration → moteur → consommateurs/jobs → routes → écran → chorégraphie ») :
  1. `libs/commun` : enveloppe (TEC-JOB-08), décimales (TEC-STK-03), outbox + relais et inbox (TEC-DAT-04), middleware d'identité HMAC + `require_role` (TEC-SEC-03, TEC-API-01), format d'erreur commun (TEC-API-03), contrôle `Origin` (TEC-SEC-07).
  2. Gabarit de service complété (`journal`, `outbox`, `inbox`, `job`, healthz interne) + `make new-service`.
  3. Contrats `utilisateur.*` (v1) + `make contracts` étendu (exemples validés, graphe sans cycle).
  4. `identity` : migration (`utilisateur`, `session`, `code_secours`, `invitation`, `tentative_connexion`, `journal`, `outbox`) → moteurs purs (verrouillage, TOTP ±1, codes de secours, durée de session) + tests hypothesis → routes `/auth/*`, `/auth/verify`, `/users/*` → matrice des droits.
  5. Compose dev (postgres, nats, mailpit, identity, front, nginx) ; passerelle nginx (ADR 0003) en complétant `deploy/nginx/nginx.dev.conf` : démarrage sans les services absents (résolveur Docker + upstreams en variables), `/api/identity/auth/verify` fermé au public (404), en-têtes d'identité vidés aussi vers le front, cache `auth_request` 10 s par cookie (TEC-WEB-03), `/ops` réservé aux adresses WireGuard (TEC-SEC-18), tests d'en-têtes forgés (TEC-WEB-04) ; `X-Real-IP` toujours écrasé par l'adresse réelle du client, y compris sur `/api/identity/auth/*` (test et recette R0-15 : sinon le verrou par couple compte-IP de l'ADR 0006 se contourne en changeant d'en-tête).
  6. CI GitHub Actions (lint, typage, tests, contrats, build `app-base`).
  7. Front : maquettes textuelles (revue UX) puis écrans Se connecter, Code de vérification, Activer mon compte, Codes de secours, Accueil « À faire » vide, Administration → Utilisateurs, page « réservée au gérant ».
  8. Observabilité dev (OTel → Tempo/Loki/Grafana `/ops`), Playwright, recette (`scripts/recette/lot-0.py`).
- Décisions (4 octobre 2026) : recette en local sur la VM de dev, accès Internet et R0-09 reportés au lot 2 ; e-mails de compte envoyés par identity, réinitialisation, verrouillage (compte, IP) et cache nginx 10 s consignés dans l'ADR 0006 ; contrats `utilisateur.cree`, `role_change`, `suspendu`, `reactive` (id, rôle, `associe_id`, nom affiché, jamais d'e-mail ni de secret) ; `associe_id` nullable sans clé étrangère, relié au lot 1.
- Décisions étape 1 `commun` (4 octobre 2026) : accès base synchrones (SQLAlchemy `Session`), appelés par `asyncio.to_thread` depuis les callbacks NATS et le relais outbox ; validité des en-têtes d'identité signés fixée à 60 s dans identity (bien au-delà du cache nginx de 10 s) ; écritures sans en-tête `Origin` acceptées (BFF, ligne de commande), écritures inter-sites refusées.
- Décisions étape 2 gabarit (4 octobre 2026) : secrets en fichiers montés (ADR 0007, `make dev-secrets`) ; chaque base appartient au rôle d'administration qui exécute les migrations, le rôle `svc_<service>` n'a que les droits accordés table par table (journal en ajout seul, TEC-DAT-03) ; jobs et planificateur dans `commun` (TEC-JOB-01, 02, 06, 07) ; `/internal/healthz` signale base, worker, jobs en échec et événements en attente ; le gabarit est testé sur un service généré dans un dossier temporaire (`make test-gabarit`).
- Dette :
  - Images de service : le Dockerfile du gabarit (et donc `services/identity/Dockerfile`) contient encore `__GHCR_OWNER__` (propriétaire : you2mars) et la CI ne construit pas l'image `app-base` ; en dev, construire `app-base` localement depuis `deploy/docker/app-base.Dockerfile` ; `scripts/new-service.sh` doit refuser toute marque `__…__` restante, pas seulement `__SERVICE__` ; l'image d'identity doit contenir `contracts/libelles/` (lu par `APP_LIBELLES_DIR`), que le front lit aussi. **Avant d'ajouter identity dans `compose.dev.yml`.**
  - Quarantaine minimale des événements (table `quarantaine` + tâche « À faire » au gérant) : aujourd'hui `term` + journal d'erreur, message conservé dans le flux. Même échéance pour la tâche « À faire » d'un job en `echec` (TEC-JOB-02), visible aujourd'hui seulement dans `/internal/healthz`. **À livrer avant le lot 2.**
  - Données personnelles dans les flux JetStream à rétention illimitée (`nom_affiche` des événements `utilisateur.*`, noms des locataires dans `location.demarree`) : incompatible en l'état avec la purge RGPD (TEC-SEC-14). Options à étudier : (A) identifiants seuls dans les événements ; (B) sujet NATS purgeable par personne ; (C) chiffrement par personne avec destruction de la clé ; (D) événements métier avec identifiants seuls (montants et dates figés conservés), données personnelles dans des événements « fiche » (ex. `locataire.fiche_changee`) sur un sujet par personne (`evt.referentiel.locataire.<id>`) purgeables par sujet, documents figeant le nom dans leur contexte à l'émission depuis `ref_*`, registre des purges (identifiants seuls) réappliqué après toute restauration, pour les bases comme pour le flux. Quelle que soit l'option, les sauvegardes des bases posent le même problème que le flux. Décision par ADR **avant le lot 1**.
  - SMTP de production d'identity : STARTTLS obligatoire (refus d'envoyer sinon), authentification (APP-NF-06), identifiant SMTP en secret monté (ADR 0007), domaine expéditeur avec SPF, DKIM et DMARC. **Avant la mise en production du lot 2.**
  - Stockage des secrets de service (ADR 0007) : fichiers montés par Compose, 10001:10001 en 0400. **Avant la mise en production du lot 2**, décider entre les fichiers sur volume LUKS comme solution définitive (avec mise à jour de TEC-SEC-04 et TEC-SEC-08) et le coffre chiffré en base (TEC-SEC-08).
  - ~~Client HTTP interne `/internal/*` avec jeton de service (TEC-API-05, TEC-SEC-04) et en-têtes `X-Request-Id` / `trace_id` sur chaque réponse (TEC-API-06)~~ : soldée à l'étape 2 (4 octobre 2026, `libs/commun` : `interne`, `TraceMiddleware`).
- Clos le : — (recette signée le —, test utilisateur le —)
