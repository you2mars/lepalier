#!/usr/bin/env bash
# Crée une base et un rôle par service (TEC-DAT-03). Exécuté par l'image postgres au premier démarrage (dev/preprod).
# La base appartient au rôle d'administration (POSTGRES_USER), qui exécute les migrations ; le rôle applicatif
# svc_<service> ne peut que s'y connecter et utiliser le schéma public, puis reçoit ses droits table par table
# dans les migrations (journal en ajout seul). Aucun rôle n'a de droit sur deux bases.
# En prod, les mots de passe viennent de /run/secrets, jamais de ce fichier.
set -euo pipefail
SERVICES="identity referentiel facturation charges_eau documents envois veille reporting"
for svc in $SERVICES; do
  role="svc_${svc}"
  pass_var="PG_PASS_${svc^^}"
  pass="${!pass_var:-changeme}"
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres <<SQL
DO \$\$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '${role}') THEN
    CREATE ROLE ${role} LOGIN PASSWORD '${pass}';
  END IF;
END \$\$;
SELECT 'CREATE DATABASE ${svc} OWNER "${POSTGRES_USER}"' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${svc}')\gexec
REVOKE ALL ON DATABASE ${svc} FROM PUBLIC;
GRANT CONNECT ON DATABASE ${svc} TO ${role};
SQL
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$svc" -c "GRANT USAGE ON SCHEMA public TO ${role};"
done
