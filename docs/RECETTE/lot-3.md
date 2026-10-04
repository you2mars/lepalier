# Recette du lot 3 — charges-eau + veille IRL (jalon « première régularisation »)

Jeu de données : `make recette LOT=3` ajoute 14 mois de relevés, 4 factures d'eau (une à cheval sur deux exercices), charges de l'exercice par nature, table IRL jusqu'au dernier trimestre publié, un bail en forfait meublé désactivé.

## Cas fonctionnels
| ID | Pré-requis | Étapes | Résultat attendu | Validé le / par | Commentaire |
| --- | --- | --- | --- | --- | --- |
| R3-01 | Opérateur, mobile | Eau → « Enregistrer un relevé » : index 12 345,678, photo | Enregistré, consommation depuis le dernier relevé affichée en m³ et m³/jour (APP-EAU-01) | | |
| R3-02 | R3-01 | Saisir un index inférieur au précédent sans motif « remplacement » | Refus expliqué (§ 6.1) | | |
| R3-03 | Gérant | Relevé avec motif « remplacement de compteur », index déposé et index de pose | Consommation calculée sur les deux segments (TEC-CAL-08) | | |
| R3-04 | Gérant | Enregistrer une facture d'eau avec 5 % d'écart vs relevés | Alerte d'écart affichée, enregistrement possible (§ 6.1) | | |
| R3-05 | Gérant | Relevé donnant +40 % de consommation journalière | Alerte « consommation anormale » dans « À faire » (APP-EAU-01) | | |
| R3-06 | Gérant | Charges → saisir TEOM, entretien, électricité communs avec justificatifs | Lignes par nature, totaux (APP-CHG-01) | | |
| R3-07 | Gérant | Régularisation → « Simuler » l'exercice | Tableau par appartement : provisions, réel par nature, solde ; somme des parts = coût total au centime ; vacance imputée à la SCI (TEC-CAL-10/11/13, APP-CHG-06) | | |
| R3-08 | R3-07 | Ouvrir le détail de l'appartement entré le 15 | Prorata au jour visible et expliqué (UX-28) | | |
| R3-09 | R3-07 | « Émettre » | Lettres générées (décompte par nature, mode de répartition, mention 6 mois), rappels ou avoirs sur le loyer du mois suivant, nouvelle provision proposée (APP-CHG-02/03/05) | | |
| R3-10 | Bail forfait (meublé activé en test) | Simuler | Exclu du décompte, écart affiché pour information (APP-CHG-07) | | |
| R3-11 | — | Veille → IRL | Dernier trimestre présent avec date de parution ; valeur identique service-public (TEC-VJ-06) | | |
| R3-12 | Date simulée = révision d'un bail | `make tick` | Révision préparée avec les deux indices et le nouveau loyer ; tâche « à valider » (TEC-CAL-16) | | |
| R3-13 | R3-12 | Valider et envoyer | Lettre partie ; loyer appliqué à l'échéance suivante ; version de bail créée (chorégraphie § 5.6) | | |
| R3-14 | Bail dont la révision date de plus d'un an | `make tick` | Révision marquée « perdue », aucun rattrapage (TEC-CAL-17) | | |
| R3-15 | Date simulée = anniversaire d'un bail | `make tick` | Demande d'attestation d'assurance envoyée ; +30 j sans réponse = relance (§ 7) | | |

## Cas négatifs et droits
| ID | Pré-requis | Étapes | Résultat attendu | Validé le / par | Commentaire |
| --- | --- | --- | --- | --- | --- |
| R3-20 | IRL du trimestre absent | Forcer la révision | Refus : indice non publié, job repassera (TEC-CAL-17) | | |
| R3-21 | Associé | Tenter d'émettre une régularisation | Refus | | |
| R3-22 | — | Rejouer `regularisation.emise` deux fois | Un seul rappel (inbox) | | |

## Ergonomie et accessibilité
| ID | Pré-requis | Étapes | Résultat attendu | Validé le / par | Commentaire |
| --- | --- | --- | --- | --- | --- |
| R3-30 | Associé | Lire le décompte de régularisation d'un appartement | Chaque ligne expliquée (d'où vient le chiffre), solde en gras, phrase de conclusion (UX-6, UX-28) | | |
| R3-31 | Mobile | Saisie du relevé | Clavier décimal, photo en un geste, confirmation avec la consommation calculée (UX-7, UX-24) | | |
| R3-32 | — | Lettre de régularisation PDF | Décompte lisible, total en toutes lettres, texte légal après (UX-31…34) | | |

## Test utilisateur
Tâches : (1) [associé] expliquer pourquoi l'appartement 4 doit 85,30 € de régularisation, (2) [opérateur] saisir un relevé sur mobile, (3) [associé] dire de combien le loyer de l'appartement 9 a été révisé. Participants : — · Résultats : — · SUS : — · Constats : — · Décisions : —

## Décision de clôture
Date : — · Signature : — · Réserves : —
