# Recette du lot 1 — referentiel + documents (jalon « bail imprimé »)

Jeu de données : `make recette LOT=1` crée la SCI de test (familiale : oui), l'immeuble « 12 rue des Tests », 20 appartements (tantièmes, surfaces, DPE C à E), 3 locataires en place, 1 garant.

## Cas fonctionnels
| ID | Pré-requis | Étapes | Résultat attendu | Validé le / par | Commentaire |
| --- | --- | --- | --- | --- | --- |
| R1-01 | Gérant | Immeuble → « Ajouter un appartement » : n° 21, 3e étage, 45,50 m², 2 pièces, 50 tantièmes | Appartement créé ; total des tantièmes mis à jour ; journal (APP-REF-01) | | |
| R1-02 | R1-01 | Modifier les tantièmes à 55 | Enregistré, historique visible (APP-REF-05) | | |
| R1-03 | Gérant | Appartement 21 → « Nouveau bail » : vide, 1er du mois prochain, loyer 650,00, provision 80,00, dépôt 650,00, locataire nouveau « Martin Léa », e-mail test | Bail créé, durée 3 ans (SCI familiale) proposée et affichée en toutes lettres, échéance visible (APP-REF-02, APP-SCI-01) | | |
| R1-04 | R1-03 | Saisir un dépôt de garantie de 1 300,00 | Refus avec message : le dépôt ne peut dépasser un mois de loyer hors charges (650,00 €) (APP-REF-02, UX-5) | | |
| R1-05 | Gérant | Appartement avec DPE G → « Nouveau bail » | Blocage expliqué : interdit à la location depuis le 1er janvier 2025 (APP-REF-02) | | |
| R1-06 | Bail de R1-03 | « Générer le bail » | PDF bail vide + notice + annexes (DPE, diagnostics valides) ; identifiant `BAI-2026-0001` imprimé ; téléchargeable ; version de gabarit dans les propriétés du PDF (TEC-DOC-02) | | |
| R1-07 | Bail de R1-03 | Retirer un diagnostic obligatoire puis « Générer le bail » | Blocage : diagnostic manquant nommé (APP-DOC-03) | | |
| R1-08 | Bail de R1-03 | « Ajouter un avenant » : loyer 660,00 au 1er du mois suivant | Nouvelle version datée ; l'ancienne reste visible ; PDF d'avenant (APP-REF-04) | | |
| R1-09 | Mobile | « État des lieux d'entrée » : 3 pièces, 2 éléments chacune, 1 photo par pièce | Saisie à une main, photos compressées, PDF < 25 Mo avec photos (APP-DOC-04, TEC-DOC-09) | | |
| R1-10 | R1-09 | « État des lieux de sortie » | Pré-rempli depuis l'entrée, écarts mis en évidence (APP-DOC-04) | | |
| R1-11 | Gérant | « Générer » un acte de caution pour le garant | PDF avec montant et durée ; signature manuscrite non apposée (document bilatéral, APP-DOC-07) | | |
| R1-12 | Gérant | Terminer le bail de l'appartement 3 à une date | Statut « Terminé », appartement libre, documents conservés (APP-REF-03) | | |
| R1-13 | Gérant | Fiche SCI : ajouter un associé avec 30 parts alors que le total ferait 110 % | Refus expliqué (APP-SCI-02) | | |

## Cas négatifs et droits
| ID | Pré-requis | Étapes | Résultat attendu | Validé le / par | Commentaire |
| --- | --- | --- | --- | --- | --- |
| R1-20 | Associé | Tenter de modifier un loyer | Lecture seule, bouton absent, API 403 | | |
| R1-21 | Opérateur | Tenter de créer un bail | Refus (APP § 3.2) | | |
| R1-22 | Gérant | Créer un second bail en cours sur l'appartement 21 | Refus : chevauchement (TEC-DAT exclusion) | | |
| R1-23 | Gérant | Double-cliquer sur « Enregistrer » d'un formulaire | Un seul enregistrement (UX-22, TEC-API-02) | | |
| R1-24 | Service `documents` arrêté | « Générer le bail » | Message « Information momentanément indisponible », rien de perdu, génération reprend au redémarrage (UX-30) | | |

## Ergonomie et accessibilité
| ID | Pré-requis | Étapes | Résultat attendu | Validé le / par | Commentaire |
| --- | --- | --- | --- | --- | --- |
| R1-30 | — | Lire le PDF du bail imprimé | Hiérarchie claire, montants alignés, aucune mention technique, texte légal après l'utile (UX-31…34) | | |
| R1-31 | — | Formulaire « Nouveau bail » | Une colonne, libellés au-dessus, valeurs par défaut sensées, aide sous les champs (UX-17, UX-18, UX-15) | | |
| R1-32 | — | Vocabulaire des écrans | Conforme au LEXIQUE (Appartement, Bail, Locataire…) | | |
| R1-33 | Mobile | Fiche appartement | 3 informations par ligne, reste au dépliage (UX-26) | | |

## Test utilisateur
Tâches : (1) retrouver le bail de l'appartement 12 et ouvrir le PDF, (2) dire quand ce bail se termine, (3) [opérateur] saisir un état des lieux d'une pièce sur mobile. Participants : — · Résultats : — · SUS : — · Constats : — · Décisions : —

## Décision de clôture
Date : — · Signature : — · Réserves : —
