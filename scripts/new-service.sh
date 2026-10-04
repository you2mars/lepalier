#!/usr/bin/env bash
# Crée services/<nom> depuis services/_template et remplace __SERVICE__ (make new-service NAME=<nom>)
# DESTINATION=<dossier> ne sert qu'à l'essai du gabarit (make test-gabarit, dossier temporaire hors du dépôt).
set -euo pipefail
NAME="${1:?nom du service requis}"
case "$NAME" in identity|referentiel|facturation|charges-eau|documents|envois|veille|reporting) ;; *) echo "service inconnu (voir SYNTHESE_SPECS § 3)"; exit 1;; esac
DEST="${DESTINATION:-services/$NAME}"
[ -e "$DEST" ] && { echo "$DEST existe déjà"; exit 1; }
cp -r services/_template "$DEST"
DB_NAME="${NAME//-/_}"
grep -rl "__SERVICE__" "$DEST" | xargs sed -i "s/__SERVICE__/$NAME/g"
grep -rl "svc_${NAME}" "$DEST" | xargs sed -i "s/svc_${NAME}/svc_${DB_NAME}/g; s#:5432/${NAME}#:5432/${DB_NAME}#g" || true
# hors de services/, le chemin relatif vers libs/commun ne tient plus : chemin absolu
if [ "$(realpath "$(dirname "$DEST")")" != "$(realpath services)" ]; then
  sed -i "s#\.\./\.\./libs/commun#$(realpath libs/commun)#" "$DEST/pyproject.toml"
fi
if grep -rn "__SERVICE__" "$DEST"; then
  echo "Des marques __SERVICE__ subsistent dans $DEST (voir ci-dessus)"
  exit 1
fi
(cd "$DEST" && uv lock -q)
echo "$DEST créé. Reste à faire : entrée dans compose.dev.yml et compose.prod.yml (secrets compris, ADR 0007), job CI (matrice), CLAUDE.md du service."
