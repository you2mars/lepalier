# Lexique métier et libellés d'interface

Nom de l'application : **LePalier** (un seul mot, majuscules à L et P, à l'écran, dans les e-mails et sur les PDF ; identifiant technique `lepalier` pour les noms de dépôt, de projet Compose et de domaine ; jamais « Palier » seul ni « LP »). Slogan interdit : l'app n'en a pas.

Règle : un seul mot par concept, le même partout (écran, PDF, e-mail, code). Le terme « interface » est celui que voient les utilisateurs ; le terme « code » est celui des tables, événements et routes.

| Interface (ce que l'utilisateur lit) | Code | Ne pas utiliser |
| --- | --- | --- |
| Appartement | `lot` | lot (à l'écran), unité, bien |
| Locataire | `locataire` | tenant, occupant |
| Bail | `location` (le contrat en cours) | contrat de location (sauf titre du PDF), lease |
| Loyer du mois | `echeance` | échéance (à l'écran), facture, appel |
| Avis de loyer | `avis_echeance` | avis d'échéance (à l'écran), appel de loyer |
| Paiement reçu | `paiement` | règlement, encaissement |
| Quittance | `quittance` | reçu (réservé au paiement partiel) |
| Reçu de paiement partiel | `recu` | acompte |
| Reste à payer | `reste_du` | solde, impayé (sauf statut « En retard ») |
| Charges (provision mensuelle) | `charges_mensuelles` / `provision` | avance, acompte de charges |
| Régularisation des charges | `regularisation` | décompte (réservé au PDF), apurement |
| Relevé d'eau | `releve_eau` | index (le chiffre lu s'appelle « index du compteur ») |
| Dépôt de garantie | `depot_garantie` | caution (réservé au garant) |
| Garant | `garant` | caution solidaire (titre de l'acte seulement) |
| Révision du loyer | `revision` | indexation, augmentation |
| Attestation d'assurance | `attestation_assurance` | justificatif |
| À faire | `tache` | todo, action, alerte (réservé à la veille et à la conso d'eau) |
| Alerte | `alerte` | notification, warning |
| Envoi | `envoi` | courrier (réservé au canal papier), mail |
| Courrier papier | canal `papier` | lettre |
| Lettre recommandée avec accusé de réception | niveau `lrar` | LRAR (à l'écran, écrire en toutes lettres la première fois) |
| Associé | rôle `associe` | actionnaire, partenaire |
| Gérant | rôle `gerant` | administrateur, admin |
| Opérateur | rôle `operateur` | saisisseur, assistant |
| Enregistrer | bouton principal des formulaires | Valider, Soumettre, OK, Submit |
| Annuler (ne rien changer) | bouton secondaire | Retour, Fermer |
| Marquer comme payé | action sur un loyer du mois | Valider le paiement |

Statuts affichés d'un loyer du mois : « À venir », « Avis envoyé », « Payé en partie », « Payé », « En retard », « Quittance envoyée », « Annulé ».

Formats : montants `1 234,56 €` (espace insécable, virgule) ; dates longues « lundi 3 novembre 2026 » dans les textes, `03/11/2026` dans les tableaux ; périodes « novembre 2026 ».
