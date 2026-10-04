# Recette du lot 0 — Plateforme et identity

Jeu de données : `make recette LOT=0` crée un gérant (`gerant@test.local`), un associé invité, un opérateur invité.

Environnement : VM de dev sur le réseau local, `https://<adresse IP de la VM de dev>/`, certificat auto-signé (accepter l'avertissement du navigateur une fois ; `curl -k` pour les cas en ligne de commande). Les cas qui exigent un accès depuis Internet sont reportés au lot 2 (préproduction non décidée).

## Cas fonctionnels
| ID | Pré-requis | Étapes | Résultat attendu | Validé le / par | Commentaire |
| --- | --- | --- | --- | --- | --- |
| R0-01 | VM de dev démarrée (`make dev-up`) | Ouvrir `https://<adresse IP de la VM de dev>/` | Page de connexion en français, titre « Se connecter », un seul bouton « Se connecter », aucun jargon (UX-1, UX-2) | | |
| R0-02 | Compte gérant | Saisir e-mail + mot de passe corrects | Écran « Code de vérification » demandant les 6 chiffres de l'application d'authentification | | |
| R0-03 | R0-02 | Saisir un code TOTP valide | Accueil « À faire » (vide : message explicatif UX-27), nom du compte visible, bouton « Se déconnecter » | | |
| R0-04 | Gérant connecté | Administration → Utilisateurs → « Inviter un associé » avec `associe@test.local` | Ligne « Invitation envoyée » ; e-mail reçu dans Mailpit avec lien ; journal : `utilisateur.invite` par gérant (APP-USR-01) | | |
| R0-05 | R0-04 | Ouvrir le lien d'invitation, définir un mot de passe, scanner le QR TOTP, saisir le code | Compte activé, 10 codes de secours affichés une seule fois avec consigne de conservation | | |
| R0-06 | Associé connecté | Tenter d'ouvrir Administration | Message « Cette page est réservée au gérant » et retour possible (pas de page blanche) ; API répond 403 (TEC-API-01) | | |
| R0-07 | Gérant | Suspendre l'associé, puis l'associé recharge une page | L'associé est déconnecté au plus 10 secondes après, avec le message « Votre accès a été suspendu. Contactez le gérant de la SCI. » ; la session est révoquée immédiatement côté identity (APP-USR-01, ADR 0006) | | |
| R0-08 | Gérant | Se déconnecter puis utiliser le bouton « Précédent » du navigateur | Aucune page protégée ne s'affiche ; retour à la connexion (TEC-SEC-02) | | |
| R0-09 | — | Vérifier Grafana `/ops` depuis WireGuard et depuis Internet | Accessible via WireGuard, 403 depuis Internet (TEC-SEC-18) | | Reporté au lot 2 (préproduction non décidée) |

## Cas négatifs et droits
| ID | Pré-requis | Étapes | Résultat attendu | Validé le / par | Commentaire |
| --- | --- | --- | --- | --- | --- |
| R0-10 | — | Depuis un même poste, 5 mots de passe faux de suite sur un compte existant, puis un 6e essai avec le bon mot de passe ; recommencer avec un e-mail inconnu | Message « Trop d'essais. Réessayez dans 15 minutes. » ; 6e essai refusé avec le même message ; message identique pour l'e-mail inconnu (TEC-SEC-01, ADR 0006) | | |
| R0-11 | — | Avec `curl`, appeler `/api/referentiel/lots` sans cookie | 401 JSON `{code: unauthenticated}` (TEC-WEB-03) | | |
| R0-12 | — | Avec `curl`, envoyer `X-User-Id` et `X-Role: gerant` forgés | 401/403 : les en-têtes sont écrasés par nginx (TEC-WEB-04) | | |
| R0-13 | — | Ouvrir `/internal/healthz` depuis un poste du réseau local (via nginx) | 404 (TEC-SEC-04) | | |
| R0-14 | Associé | Utiliser un code de secours deux fois | Première fois acceptée, seconde refusée (TEC-SEC-01) | | |

## Ergonomie et accessibilité
| ID | Pré-requis | Étapes | Résultat attendu | Validé le / par | Commentaire |
| --- | --- | --- | --- | --- | --- |
| R0-20 | Tablette ou mobile 360 px | Dérouler R0-02 à R0-05 | Tout est lisible sans zoom, cibles ≥ 44 px, clavier numérique pour le code (UX-7, UX-8, UX-21) | | |
| R0-21 | Ordinateur | Parcourir la connexion au clavier seul (Tab, Entrée) | Focus visible à chaque étape, aucun piège (UX-8) | | |
| R0-22 | Lecteur d'écran (NVDA ou VoiceOver) | Lire le formulaire de connexion | Chaque champ est annoncé avec son libellé, les erreurs sont lues (UX-8) | | |
| R0-23 | — | Zoom navigateur 200 % | Aucune perte de contenu ni défilement horizontal (UX-8) | | |
| R0-24 | — | Mot de passe faux une fois | Message sous le champ : quoi / pourquoi / que faire, sans code d'erreur (UX-5, UX-19) | | |
| R0-25 | Tablette sur le même réseau local que la VM de dev | Ouvrir `https://<adresse IP de la VM de dev>/`, accepter le certificat auto-signé, dérouler R0-01 à R0-03 puis se déconnecter | Page de connexion atteinte sans autre réglage ; tout est lisible sans zoom en portrait et en paysage, cibles ≥ 44 px, clavier numérique pour le code, aucun défilement horizontal (UX-7, UX-8, UX-21) | | |

## Test utilisateur
Participants : — · Date : — · Tâches : (1) activer son compte depuis l'e-mail d'invitation, (2) installer l'application d'authentification et se connecter, (3) se déconnecter. Résultats : — · SUS : — · Constats : — · Décisions : —

## Décision de clôture
Date : — · Signature : — · Réserves : —
