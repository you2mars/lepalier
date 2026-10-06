# Changelog des contrats

| Date | Événement | Version | Producteur | Consommateurs | Motif | Retrait prévu de l'ancienne version |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-10-03 | enveloppe | 1 | tous | tous | Création | — |
| 2026-10-03 | location.demarree | 1 | referentiel | facturation, charges-eau, documents, reporting | Création (lot 1) | — |
| 2026-10-03 | echeance.payee | 1 | facturation | documents, reporting | Création (lot 2) | — |
| 2026-10-04 | utilisateur.cree | 1 | identity | reporting (projection dès le lot 2, journal et notifications au lot 4) | Création (lot 0) : activation d'un compte invité ; ni e-mail ni secret (ADR 0006) | — |
| 2026-10-04 | utilisateur.role_change | 1 | identity | reporting (projection dès le lot 2, journal et notifications au lot 4) | Création (lot 0) : changement de rôle, avec l'ancien rôle | — |
| 2026-10-04 | utilisateur.suspendu | 1 | identity | reporting (projection dès le lot 2, journal et notifications au lot 4) | Création (lot 0) : suspension, sessions révoquées | — |
| 2026-10-04 | utilisateur.reactive | 1 | identity | reporting (projection dès le lot 2, journal et notifications au lot 4) | Création (lot 0) : réactivation, anciennes sessions toujours révoquées | — |
| 2026-10-04 | utilisateur.cree, role_change, suspendu, reactive | 1 | identity | reporting | Motif de `nom_affiche` resserré en place : refus des caractères de contrôle C0 et C1 (U+0000 à U+001F, U+007F à U+009F), des séparateurs de ligne et de paragraphe (U+2028, U+2029) et des marques de sens d'écriture (U+202A à U+202E, U+2066 à U+2069), pour qu'un nom ne puisse ni injecter de lignes dans les e-mails aux gérants ni en retourner l'affichage ; le motif se termine par `$(?!\n)` car, en Python, `$` accepte aussi la position avant un retour à la ligne final ; aucun événement n'a encore été publié, donc pas de v2 (exception à la règle 3, accordée le 4 octobre 2026) | — |
