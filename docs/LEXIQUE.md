# Lexique métier et libellés d'interface

Nom de l'application : **LePalier** (un seul mot, majuscules à L et P, à l'écran, dans les e-mails et sur les PDF ; identifiant technique `lepalier` pour les noms de dépôt, de projet Compose et de domaine ; jamais « Palier » seul ni « LP »). Slogan interdit : l'app n'en a pas.

Règle : un seul mot par concept, le même partout (écran, PDF, e-mail, code). Le terme « interface » est celui que voient les utilisateurs ; le terme « code » est celui des tables, événements et routes.

À l'écran, le contenu vient de la spec, les mots viennent du lexique.

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
| Compte | `utilisateur` (la personne enregistrée : adresse, nom affiché, rôle) | profil, membre |
| Accès | statut d'un compte (`actif`, `suspendu`) et ses réinitialisations : le droit de se connecter | autorisation, droits (à l'écran) |
| Utilisateurs | liste des comptes (`/utilisateurs`) | membres, comptes (titre de page) |
| Nom affiché | `nom_affiche` | pseudo, identifiant |
| Invitation | `invitation` (lien envoyé par e-mail, 7 jours) | enrôlement, convocation |
| Application d'authentification | second facteur TOTP | authentificateur, appli 2FA, TOTP (à l'écran) |
| Code de vérification | code TOTP à 6 chiffres | OTP, code 2FA, jeton |
| Code de secours | `code_secours` | code de récupération, code de sauvegarde |
| Administration | menu du gérant (`/administration`) | admin, paramètres, réglages |
| Se déconnecter | bouton (`/auth/deconnexion`) | Déconnexion (sur un bouton), Quitter, Logout |
| Gérer l'accès | lien vers la fiche d'une personne | Éditer, Modifier l'utilisateur |
| Enregistrer | bouton principal des formulaires | Valider, Soumettre, OK, Submit |
| Annuler (ne rien changer) | bouton secondaire | Retour, Fermer |
| Marquer comme payé | action sur un loyer du mois | Valider le paiement |

Statuts affichés d'un loyer du mois : « À venir », « Avis envoyé », « Payé en partie », « Payé », « En retard », « Quittance envoyée », « Annulé ».

Compte ou accès : on active un compte ; on suspend, réactive ou réinitialise un accès ; on invite une personne et on annule une invitation.

Statuts affichés d'un compte utilisateur (`contracts/libelles/identity.json`, groupe `statut`) : « Invitation envoyée » (statut `invite`, lien valable ou e-mail d'invitation en attente d'envoi), « Invitation expirée » (statut `invite` sans lien valable), « Accès actif » (`actif`), « Accès suspendu » (`suspendu`). Une invitation annulée (`annule`) n'est jamais affichée : la personne disparaît de la liste.

Formats : montants `1 234,56 €` (espace insécable, virgule) ; dates longues « lundi 3 novembre 2026 » dans les textes, `03/11/2026` dans les tableaux ; périodes « novembre 2026 ».

Messages partagés : les textes affichés qui viennent d'un service (par exemple les refus de mot de passe) sont écrits une seule fois dans `contracts/libelles/<service>.json`, sous une clé stable (`mot_de_passe.trop_court`) ; le service et le front les lisent là, sans les recopier.
