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
