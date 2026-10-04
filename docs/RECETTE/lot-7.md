# Recette du lot 7 — v2 postale (API La Poste)

| ID | Pré-requis | Étapes | Résultat attendu | Validé le / par | Commentaire |
| --- | --- | --- | --- | --- | --- |
| R7-01 | Bac à sable La Poste | Déposer une mise en demeure en « recommandé » | Identifiant et n° de suivi retournés, statut « Déposé », coût estimé puis réel (TEC-ENV-04/07) | | |
| R7-02 | R7-01 | Suivi quotidien | Statuts normalisés mis à jour ; preuves de dépôt et AR archivées sous le document (TEC-ENV-06) | | |
| R7-03 | API indisponible (simulée) | Déposer | Pli reste « Préparé », bascule manuelle possible, aucune perte (TEC-POST-03) | | |
| R7-04 | Webhook | Envoyer un webhook sans secret valide | Rejeté, journalisé (§ 11.1) | | |
| R7-05 | Opérateur | Tenter un dépôt par API | Refus : réservé au gérant (TEC-ENV-05) | | |
| R7-10 | Gérant | Écran envois enrichi | Statuts en mots, coût lisible, preuves accessibles (UX-14) | | |

## Décision de clôture
Date : — · Signature : — · Réserves : —
