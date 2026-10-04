---
paths:
  - "front/**"
---
# Règles front (Next.js 15, TypeScript)

- App Router, composants serveur pour la lecture, composants client seulement pour formulaires et graphes ; aucune donnée métier dans `localStorage`.
- Le BFF appelle `/api/<service>` en relayant le cookie ; il compose la page avec dégradation par bloc (un service en panne = bloc « indisponible », pas page blanche).
- Charte UX obligatoire (docs/UX_CHARTE.md) : un écran = une tâche, libellés du LEXIQUE, un seul bouton primaire par écran, messages d'erreur « quoi / pourquoi / que faire », confirmation récapitulative avant tout irréversible, formulaires en une colonne avec libellés au-dessus, validation inline, police ≥ 16 px, cibles ≥ 44 px, contraste AA, navigation clavier, focus visible.
- Mobile d'abord pour les écrans de saisie (relevé, paiement, état des lieux) ; photos via `<input capture>` compressées côté client.
- Nombres et dates au format français (`Intl.NumberFormat('fr-FR')`, dates en toutes lettres quand c'est lu par un humain).
- CSP stricte : nonce lu dans l'en-tête `X-Nonce`, pas de style ou script inline sans nonce.
- Chaque écran a un test Playwright de parcours et une entrée dans la recette manuelle du lot.
