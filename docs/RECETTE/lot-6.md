# Recette du lot 6 — résilience et exploitation (exercices signés)

| ID | Exercice | Résultat attendu | Validé le / par | Commentaire |
| --- | --- | --- | --- | --- |
| R6-01 | Restauration complète sur un VPS temporaire depuis la sauvegarde de la nuit | < 2 h, `sante` vert, documents lisibles, rejeu des écarts de séquence (TEC-OPS-04) | | |
| R6-02 | `make rebuild SVC=facturation` en prod (fenêtre de maintenance) | Copies `ref_*` reconstruites, aucune échéance modifiée | | |
| R6-03 | Arrêt de NATS pendant une saisie de paiement puis redémarrage | Paiement acquis, quittance émise après reprise, pas de doublon | | |
| R6-04 | Service `envois` arrêté 24 h | Rattrapage complet au redémarrage, registre cohérent | | |
| R6-05 | Coupure du second canal d'alerte simulée | Alerte reçue par le canal restant (TEC-OPS-06) | | |
| R6-06 | Balayage externe et `testssl.sh` annuels | Surface conforme, note A, compte rendu archivé (TEC-WEB-02/11) | | |
| R6-07 | Rotation des secrets (HMAC, SMTP) | Aucune interruption visible | | |
| R6-08 | Lecture de `docs/EXPLOITATION.md` par un tiers technique | Il redémarre et déverrouille la plateforme sans aide | | |

## Décision de clôture
Date : — · Signature : — · Réserves : —
