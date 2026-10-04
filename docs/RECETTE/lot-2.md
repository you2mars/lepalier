# Recette du lot 2 — facturation + envois (jalon « premier cycle mensuel »)

Jeu de données : `make recette LOT=2` ajoute 20 baux en cours (dont une entrée le 15 du mois, un locataire sans e-mail, un avec accord de quittance dématérialisée), échéances du mois en cours, Mailpit vidé.

## Cas fonctionnels
| ID | Pré-requis | Étapes | Résultat attendu | Validé le / par | Commentaire |
| --- | --- | --- | --- | --- | --- |
| R2-01 | Date simulée = J-10 | Lancer le planificateur (`make tick`) | 20 avis générés ; e-mails dans Mailpit pour les locataires e-mail ; lot d'impression contient les autres ; statut « Avis envoyé » (APP-ECH-01/02) | | |
| R2-02 | Locataire entré le 15 | Ouvrir son loyer du mois | Montant proratisé au jour sur le mois réel, détail affiché (TEC-CAL-02) | | |
| R2-03 | Opérateur, mobile | Loyers du mois → appartement 5 → « Enregistrer un paiement » : 730,00, virement, date du jour | Message « Paiement de 730,00 € enregistré… », statut « Payé », puis « Quittance envoyée » en moins d'une minute, e-mail reçu (APP-ECH-05) | | |
| R2-04 | Opérateur | Appartement 6 : paiement 300,00 sur 730,00 | Statut « Payé en partie », reçu partiel généré, reste à payer 430,00 (APP-ECH-06) | | |
| R2-05 | R2-04 | Second paiement 430,00 | Statut « Payé » puis quittance unique pour le mois (TEC-CAL-05) | | |
| R2-06 | Opérateur | Appartement 7 : paiement 800,00 sur 730,00 | Proposition de ventiler les 70,00 sur le mois suivant ; acceptation crée deux paiements liés (TEC-CAL-06) | | |
| R2-07 | Date simulée = J+10 | `make tick` | Appartements non payés passent « En retard », apparaissent dans « À faire » avec le nombre de jours (APP-ECH-07) | | |
| R2-08 | Gérant | Appartement en retard → « Envoyer une relance » | Lettre générée, envoi selon canal ; rien d'automatique (APP-ECH-07) | | |
| R2-09 | Gérant | « Mise en demeure » pour le même | Lettre + envoi niveau « recommandé », statut « Préparé », dans le lot d'impression (APP § 8.1) | | |
| R2-10 | R2-09 | Envois → marquer « Déposé » avec n° de recommandé `1A…`, joindre la preuve de dépôt (photo) | Registre à jour, preuve stockée, tâche fermée (APP-ENV-03) | | |
| R2-11 | Locataire sans accord démat. | Marquer payé | La quittance part en papier (lot d'impression), pas par e-mail (APP-ECH-05) | | |
| R2-12 | Gérant | Annuler une quittance émise par erreur | Quittance corrective référençant l'originale ; l'originale reste lisible avec bandeau « annulé » (APP-ECH-08, TEC-DOC-10) | | |
| R2-13 | Gérant | Télécharger le lot d'impression du jour | Un PDF, page de garde avec destinataires et niveaux, adresses dans la fenêtre DL (TEC-DOC-08) | | |
| R2-14 | — | Tableau de bord mensuel | Appelé, reçu, reste, statut par appartement, totaux ; export CSV (APP-ECH-09) | | |
| R2-15 | Gérant | « Attestation de loyer » pour un locataire sur 6 mois | PDF correct (APP-ECH-10) | | |

## Infrastructure et production
| ID | Pré-requis | Étapes | Résultat attendu | Validé le / par | Commentaire |
| --- | --- | --- | --- | --- | --- |
| R2-40 | VPS Hetzner livré | `scripts/bootstrap-vps.sh` | LUKS monté après saisie de la passphrase via WireGuard, Docker, nginx, certificat Let's Encrypt valide, `testssl.sh` note A (TEC-WEB-01/02) | | |
| R2-41 | Prod déployée | Redémarrer le VPS | Alerte « volume non monté » reçue ; déverrouillage manuel ; pile redémarre seule après montage (§ 11.2) | | |
| R2-42 | Prod | Sauvegarde nocturne puis restauration sur un VPS temporaire | Restauration < 2 h, `sante` vert, documents lisibles (TEC-OPS-03/04) | | |
| R2-43 | Prod | Balayage externe `nmap` | Seuls 443, 80, 51820/udp ouverts (TEC-WEB-09) | | |
| R2-44 | CI | Fusionner une PR puis approuver l'environnement prod | Le runner tire les images et redéploie sans SSH entrant ; version visible dans `/sante` (TEC-QA-05) | | |

## Cas négatifs et droits
| ID | Pré-requis | Étapes | Résultat attendu | Validé le / par | Commentaire |
| --- | --- | --- | --- | --- | --- |
| R2-20 | Opérateur | Tenter de déposer un recommandé | Refus : réservé au gérant (TEC-ENV-05) | | |
| R2-21 | Opérateur | Paiement de montant négatif ou à 0 | Refus avec message clair (TEC-CAL-05) | | |
| R2-22 | Service `documents` arrêté 10 min | Marquer payé | Paiement acquis ; « Quittance en attente » puis tâche ; quittance émise au redémarrage sans doublon (§ 5.6) | | |
| R2-23 | SMTP coupé | Marquer payé (locataire e-mail) | Envoi reste en file, retenté, aucun échec métier (TEC-ENV-10) | | |
| R2-24 | — | Rejouer deux fois `echeance.payee` (outil `make replay`) | Une seule quittance (inbox) | | |

## Ergonomie et accessibilité
| ID | Pré-requis | Étapes | Résultat attendu | Validé le / par | Commentaire |
| --- | --- | --- | --- | --- | --- |
| R2-30 | Mobile | Enregistrer 3 paiements d'affilée | Moins de 30 s chacun, clavier décimal, montant par défaut = reste à payer, confirmation lisible (UX-7, UX-18, UX-24) | | |
| R2-31 | Associé | « Qui n'a pas payé ce mois-ci ? » | Lisible en un coup d'œil, statuts en mots, pas de couleur seule (UX-14, UX-25) | | |
| R2-32 | — | Quittance PDF et e-mail | Conformes UX-16 et UX-31…34, nom de fichier lisible | | |
| R2-33 | — | Confirmation avant « Envoyer la mise en demeure » | Récapitulatif destinataire, montant, mode d'envoi (UX-3) | | |

## Test utilisateur
Tâches : (1) [opérateur] enregistrer un paiement sur mobile, (2) [associé] dire quels appartements sont en retard et depuis combien de jours, (3) [associé] retrouver la quittance d'octobre de l'appartement 8. Participants : — · Résultats : — · SUS : — · Constats : — · Décisions : —

## Décision de clôture
Date : — · Signature : — · Réserves : —
