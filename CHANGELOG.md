# Changelog

## [Non publié] — lot 0 « Plateforme » (branche `lot/0-front`, PR n° 8)

### Ajouté
- Nom de l'application : LePalier (ADR 0005).
- Squelette du dépôt : instructions Claude Code, plan de développement, charte UX, recettes, contrats de base, gabarit de service, Compose dev, CI.
- Bibliothèque commune (`libs/commun`) : enveloppe d'événement, montants décimaux, outbox et inbox, identité signée (HMAC), format d'erreur commun, contrôle de l'origine des écritures, idempotence des écritures (TEC-API-02), journal d'audit, jobs et planificateur quotidien à 04:00 Europe/Paris, client HTTP interne, dates en toutes lettres à l'heure de Paris, libellé d'indisponibilité temporaire.
- Gabarit de service (`make new-service`) : socle câblé (middlewares, secrets lus dans `/run/secrets`, santé, worker, migrations avec le rôle propriétaire), `make test-gabarit`.
- Contrats : `utilisateur.cree`, `utilisateur.role_change`, `utilisateur.suspendu`, `utilisateur.reactive` (v1) ; libellés des refus de mot de passe partagés avec le front.
- Service identity : connexion en deux étapes (mot de passe puis code TOTP ou code de secours), sessions, nouvel appareil et alertes au gérant, invitation et activation, mot de passe oublié, administration des utilisateurs (invitation, rôle, suspension, réactivation, réinitialisation de l'accès), commande d'administration locale, purges, e-mails de compte ; moteurs purs (mot de passe, jetons, chiffrement, TOTP, codes de secours, verrouillage, durées).
- nginx en frontal : vérification d'identité (`auth_request`, cache de 10 s), limite de débit sur `/api/identity/auth/`, en-têtes de sécurité, réponses d'erreur au format commun (401, 404, 429, 503), page de maintenance quand le front est absent, écoute interne en lecture seule pour le BFF.
- Front (Next.js 15, BFF) : cadre commun, Se connecter, Code de vérification, Activer mon compte (trois étapes), Codes de secours, accueil « À faire », Administration › Utilisateurs (liste, fiche, inviter, gérer l'accès, changer le rôle), Mot de passe oublié, Choisir un nouveau mot de passe, page introuvable, page réservée au gérant.
- Outillage : `make dev-secrets`, `make dev-certs`, `make images`, `make test-plateforme` (essai réel des images, de Compose, de nginx et de Playwright), `make recette LOT=0`, `make tick`, hook `pre-push`.
- Chorégraphies d'identity sur la plateforme Compose : outbox → NATS JetStream, NATS, identity, PostgreSQL ou toute la plateforme arrêtés puis redémarrés, aucun événement perdu ni en double.
- CI : contrats, bibliothèque commune, services (couverture 80 % par service, 95 % sur les moteurs, bloquantes), front, essai réel de la plateforme ; traces Playwright gardées 7 jours en cas d'échec.

### Modifié
- Livraison des événements : chaque événement relayé est marqué dès sa publication confirmée ; fenêtre de dédoublonnage des flux d'une heure. Garantie : au moins une fois dans le flux, exactement une fois en effet chez le consommateur grâce à son inbox.
- E-mails de compte revus (16 octobre 2026) : fin du lien en date et heure de Paris, intervalle des essais de connexion, conseil « Mot de passe oublié » selon le rôle, rôle indiqué dans l'invitation ; rôles en mots partagés dans `contracts/libelles`.
- Navigations du front toujours complètes, par le navigateur (le routeur de Next perdait parfois une navigation sous charge).

### Corrigé
- Revue UX des écrans (8 octobre 2026) : bloquant B1, majeurs M1 à M6 ; constats (4) bouton désactivé sous le contraste AA, (5) page introuvable hors du cadre connecté, (14) « Retour à la connexion » absent de Choisir un nouveau mot de passe, (18) formulaire envoyé avant la prise en main de la page (téléphone lent).
- Vérification d'identité en échec (base arrêtée) : réponse JSON au format commun au lieu de la page HTML 500 de nginx.
- Les échecs de lint, de typage et de recette ne sont plus masqués par une commande en bout de chaîne.
