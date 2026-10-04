Migrations Alembic du service. Une migration par changement, réversible, non destructive (expansion puis contraction à la livraison suivante).

`env.py` lit `APP_MIGRATION_DATABASE_URL` (rôle propriétaire des tables, TEC-DAT-03) et refuse de s'exécuter sans elle. Chaque migration accorde au rôle applicatif les droits sur les tables qu'elle crée (`migrations/droits.py` : `lecture_ecriture`, ou `ajout_seul` pour une table immuable comme `journal`). Le DDL est écrit à la main, sans importer les tables de `commun` ni de `app`, pour que l'historique reste stable.
