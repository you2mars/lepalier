#!/usr/bin/env bash
# Crée services/<nom> depuis services/_template et remplace __SERVICE__ (make new-service NAME=<nom>)
# DESTINATION=<dossier> et GABARIT=<dossier> ne servent qu'aux essais (make test-gabarit, tests de scripts/tests),
# dans des dossiers temporaires hors du dépôt.
# Le service est préparé dans un dossier temporaire et n'est mis en place que si aucune marque __…__ ne subsiste.
set -euo pipefail
NAME="${1:?nom du service requis}"
case "$NAME" in identity|referentiel|facturation|charges-eau|documents|envois|veille|reporting) ;; *) echo "service inconnu (voir SYNTHESE_SPECS § 3)"; exit 1;; esac
SOURCE="${GABARIT:-services/_template}"
DEST="${DESTINATION:-services/$NAME}"
[ -e "$DEST" ] && { echo "$DEST existe déjà"; exit 1; }
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
PREPARE="$TMP/$NAME"
cp -r "$SOURCE" "$PREPARE"
DB_NAME="${NAME//-/_}"
grep -rl "__SERVICE__" "$PREPARE" | xargs sed -i "s/__SERVICE__/$NAME/g"
grep -rl "svc_${NAME}" "$PREPARE" | xargs -r sed -i "s/svc_${NAME}/svc_${DB_NAME}/g; s#:5432/${NAME}#:5432/${DB_NAME}#g"
# toute marque restante (__EN_MAJUSCULES__) est une valeur que personne n'a remplacée : refus
if restantes=$(cd "$PREPARE" && grep -rnoE "__[A-Z][A-Z0-9_]*__" .); then
  echo "Des marques du gabarit n'ont pas été remplacées (fichier:ligne:marque) :"
  echo "$restantes" | sed 's#^\./#  #'
  echo "Rien n'a été créé dans $DEST."
  exit 1
fi
mkdir -p "$(dirname "$DEST")"
mv "$PREPARE" "$DEST"
# hors de services/, le chemin relatif vers libs/commun ne tient plus : chemin absolu
if [ "$(realpath "$(dirname "$DEST")")" != "$(realpath services)" ]; then
  sed -i "s#\.\./\.\./libs/commun#$(realpath libs/commun)#" "$DEST/pyproject.toml"
fi
(cd "$DEST" && uv lock -q)
echo "$DEST créé. Reste à faire : entrée dans compose.dev.yml et compose.prod.yml (secrets compris, ADR 0007), job CI (matrice), CLAUDE.md du service."
