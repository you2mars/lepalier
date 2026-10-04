# docs/

| Fichier | Rôle | Origine |
| --- | --- | --- |
| `SPEC_FONCTIONNELLE.md` | Spécification fonctionnelle complète | **À exporter** depuis le Claude Doc « Spécifications fonctionnelles — Gestion locative personnelle d'un immeuble de 20 lots » (menu Export → Markdown) et déposer ici sous ce nom |
| `SPEC_TECHNIQUE.md` | Spécification technique complète (microservices, nginx, Hetzner) | **À exporter** depuis le Claude Doc « Spécifications techniques — Gestion locative personnelle (immeuble SCI, 20 lots) » |
| `SYNTHESE_SPECS.md` | Résumé des deux specs : contexte, architecture, règles clés, décisions | Fourni ; suffisant pour démarrer, mais les specs complètes font foi |
| `PLAN_DE_DEV.md` | Plan de développement par lots, rituels, journal | Fourni, vivant (Claude Code y tient le journal des lots) |
| `UX_CHARTE.md` | Charte d'ergonomie et d'accessibilité, règles numérotées, protocole de test utilisateur | Fourni |
| `DEFINITION_OF_DONE.md` | Critères de clôture d'un lot | Fourni |
| `LEXIQUE.md` | Vocabulaire métier et libellés d'interface imposés | Fourni, à enrichir |
| `RECETTE/lot-N.md` | Recette manuelle de chaque lot, validée ligne à ligne par Youssef | Fournis, complétés par `/recette N` |
| `ADR/` | Décisions d'architecture datées | Fournis, à compléter à chaque décision |

Après l'export des deux specs, lancer `make docs-check` : il vérifie que les deux fichiers existent et que les identifiants APP-/TEC- cités dans le plan y figurent.
