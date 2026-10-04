# Recette du lot 4 — reporting complet (jalon « clôture d'exercice »)

Jeu de données : `make recette LOT=4` charge 3 exercices d'historique (occupation variable, retards, régularisations, révisions, frais postaux).

## Cas fonctionnels
| ID | Pré-requis | Étapes | Résultat attendu | Validé le / par | Commentaire |
| --- | --- | --- | --- | --- | --- |
| R4-01 | Gérant | Tableau de bord global, période « année civile » | Occupation, encaissements, eau, charges, résultat, conformité ; chaque indicateur a sa définition au survol (APP-TB-03, § 10.2) | | |
| R4-02 | — | Comparer « taux de recouvrement à J+30 » avec le calcul manuel du jeu de données | Identique au centime / au dixième de % (§ 10.4) | | |
| R4-03 | — | Cliquer un indicateur | Liste des éléments qui le composent (APP-TB-03) | | |
| R4-04 | Associé | Tableau de bord d'un locataire | Solde, ponctualité, révisions, charges, frise ; aucune action possible (§ 10.3) | | |
| R4-05 | Gérant | Exports → « État 2072 » de l'exercice | Fichier avec rubriques officielles, quotes-parts par associé selon les parts, total = résultat (APP-SCI-04) | | |
| R4-06 | — | Vérifier une quote-part à la main | Exacte (APP-SCI-04) | | |
| R4-07 | — | `make rebuild SVC=reporting` | Projections reconstruites, chiffres identiques (TEC-OPS-05) | | |
| R4-08 | Associé | S'abonner aux notifications hebdomadaires | E-mail récapitulatif reçu (APP-USR-04) | | |
| R4-09 | Associé | Commenter un bail | Commentaire horodaté, non modifiable après 15 min, invisible du locataire (APP-USR-06) | | |
| R4-10 | — | Rapprochement quotidien (`make tick`) après avoir supprimé une quittance en base de test | Tâche d'écart créée (TEC-CAL-19) | | |

## Cas négatifs et droits
| ID | Pré-requis | Étapes | Résultat attendu | Validé le / par | Commentaire |
| --- | --- | --- | --- | --- | --- |
| R4-20 | Opérateur | Tableau de bord global | Visible sans les quotes-parts (APP-TB-05) | | |
| R4-21 | — | Indicateur avec moins de 3 mois d'historique | « Non calculable » avec raison (APP-TB-07) | | |

## Ergonomie et accessibilité
| ID | Pré-requis | Étapes | Résultat attendu | Validé le / par | Commentaire |
| --- | --- | --- | --- | --- | --- |
| R4-30 | Associé | Lire les graphes | Titres-conclusions, légendes en mots, table de données accessible (UX-28) | | |
| R4-31 | Tablette | Tableau de bord | Lisible, blocs empilés, pas de défilement horizontal | | |
| R4-32 | — | Export PDF du tableau | Daté, lisible imprimé | | |

## Test utilisateur
Tâches : (1) [associé] « combien l'immeuble a-t-il rapporté cette année et quelle est ma part ? », (2) [associé] « quel appartement paie le plus souvent en retard ? », (3) [gérant] préparer la déclaration 2072. Participants : — · Résultats : — · SUS : — · Constats : — · Décisions : —

## Décision de clôture
Date : — · Signature : — · Réserves : —
