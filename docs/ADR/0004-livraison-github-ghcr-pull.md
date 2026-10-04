# ADR 0004 — GitHub, GHCR et déploiement en mode pull (3 octobre 2026)

Statut : accepté. Décision : dépôt privé GitHub (2FA matérielle, branche main protégée, PR + CI obligatoires), images construites en CI et publiées dans GHCR, runner GitHub auto-hébergé sur le VPS qui tire et déploie (`docker compose pull && up -d`) après approbation manuelle de l'environnement prod ; aucun SSH entrant depuis la CI ; secrets applicatifs jamais dans GitHub. Forgejo écarté (un service exposé de plus à maintenir).
