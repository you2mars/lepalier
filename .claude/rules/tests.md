---
paths:
  - "**/tests/**"
  - "front/e2e/**"
---
# Règles de tests

- Moteurs : propriétés (hypothesis) + cas figés versionnés en JSON dans `tests/fixtures/` ; résultats attendus au centime, jamais recalculés par le test.
- Intégration : Testcontainers (PostgreSQL 16, NATS) ; deux livraisons du même événement = un seul effet ; crash simulé entre commit et accusé = pas de doublon.
- Droits : test paramétré sur (rôle × route × objet), refus par défaut, en-têtes d'identité forgés refusés.
- Documents : rendu de chaque gabarit actif avec un contexte de référence, texte extrait comparé, PDF/A vérifié si `verapdf` est disponible.
- Chorégraphies : scénarios § 5.6 de la spec technique sur la plateforme Compose, y compris avec un service arrêté puis redémarré.
- Nommage : `test_<fonction>__<cas>__<attendu>` ; un test = une assertion de comportement.
- Un bug remonté en recette manuelle donne d'abord un test qui échoue, puis le correctif.
