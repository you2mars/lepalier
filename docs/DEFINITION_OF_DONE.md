# Definition of Done d'un lot

Un lot est terminé quand TOUS les points sont vérifiés avec une preuve (commande, fichier, signature).

## Code et tests automatisés
- [ ] Contrats d'événements du lot écrits avant le code, `make contracts` vert, CHANGELOG à jour.
- [ ] `make lint`, `make typecheck`, `make test` verts ; couverture ≥ 95 % sur `app/engines/**`, ≥ 80 % par service.
- [ ] Tests de propriétés et cas figés pour chaque moteur touché ; idempotence (événement et job rejoués) testée.
- [ ] Matrice des droits testée pour chaque route ajoutée ; en-têtes forgés refusés.
- [ ] Chorégraphies du lot testées sur Compose, y compris avec un service arrêté puis redémarré.
- [ ] Tests Playwright de parcours pour chaque écran.
- [ ] Migrations réversibles et non destructives ; `make migrate` testé sur une base vide ET sur une base restaurée du lot précédent.

## Recette manuelle (Youssef)
- [ ] `docs/RECETTE/lot-N.md` complet : chaque fonctionnalité a ses cas nominal, limite, erreur, droits, ergonomie.
- [ ] Jeu de données de recette chargé par `make recette LOT=N` sur la preprod.
- [ ] Toutes les lignes portent « Validé le / par » rempli par Youssef ; les KO ont une issue GitHub et un test de non-régression.

## Ergonomie
- [ ] `/revue-ux` passé sur chaque écran, gabarit PDF et e-mail du lot ; aucun constat bloquant ou majeur ouvert.
- [ ] Test utilisateur réalisé avec au moins un associé non technicien sur les tâches du lot (protocole UX_CHARTE § 7) : taux de réussite ≥ 90 % sans aide, SUS ≥ 70, compte rendu dans `docs/RECETTE/lot-N.md` section « Test utilisateur ».
- [ ] Libellés conformes au LEXIQUE ; nouveaux termes ajoutés au LEXIQUE.
- [ ] Vérification accessibilité : navigation clavier, lecteur d'écran sur un parcours, contraste, zoom 200 %, mobile.

## Documentation et exploitation
- [ ] `CLAUDE.md` du service, `docs/SYNTHESE_SPECS.md` et ADR mis à jour si une décision a changé.
- [ ] `CHANGELOG.md` racine renseigné ; journal du lot dans `PLAN_DE_DEV.md`.
- [ ] Déployé en preprod depuis les images CI ; `/api/reporting/sante` vert ; restauration de sauvegarde réussie (à partir du lot 2).
- [ ] Tag `lot-N` posé après fusion sur `main`.
