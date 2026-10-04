#!/usr/bin/env bash
# Crée services/<nom> depuis services/_template et remplace __SERVICE__ (make new-service NAME=<nom>)
set -euo pipefail
NAME="${1:?nom du service requis}"
case "$NAME" in identity|referentiel|facturation|charges-eau|documents|envois|veille|reporting) ;; *) echo "service inconnu (voir SYNTHESE_SPECS § 3)"; exit 1;; esac
[ -d "services/$NAME" ] && { echo "services/$NAME existe déjà"; exit 1; }
cp -r services/_template "services/$NAME"
DB_NAME="${NAME//-/_}"
grep -rl "__SERVICE__" "services/$NAME" | xargs sed -i "s/__SERVICE__/$NAME/g"
grep -rl "svc_${NAME}" "services/$NAME" | xargs sed -i "s/svc_${NAME}/svc_${DB_NAME}/g; s#:5432/${NAME}#:5432/${DB_NAME}#g" || true
echo "services/$NAME créé. Reste à faire : entrée dans compose.dev.yml et compose.prod.yml, job CI (matrice), CLAUDE.md du service."
