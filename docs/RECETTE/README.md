# Recettes manuelles

Chaque lot a sa recette. Youssef déroule les cas sur la **preprod** chargée par `make recette LOT=N` (jeu de données reproductible, aucune donnée réelle) et remplit les deux dernières colonnes. Seul un humain remplit « Validé le / par ».

Format d'un cas :

| ID | Pré-requis | Étapes | Résultat attendu | Validé le / par | Commentaire |
| --- | --- | --- | --- | --- | --- |

Conventions : identifiant `RN-nn` ; étapes avec les valeurs exactes à saisir ; résultat observable (écran, PDF, e-mail dans Mailpit `http://preprod:8025`, ligne du journal, ligne de tableau de bord) ; référence APP-/TEC- en fin de résultat.

Sections obligatoires de chaque recette : **Cas fonctionnels**, **Cas négatifs et droits**, **Ergonomie et accessibilité**, **Test utilisateur** (compte rendu du protocole `UX_CHARTE.md` § 7), **Décision de clôture** (date, signature, réserves).

Un KO : issue GitHub `recette` + test de non-régression avant correctif ; la ligne est rejouée après livraison.
