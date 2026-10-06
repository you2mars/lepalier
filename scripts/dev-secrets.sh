#!/usr/bin/env bash
# Secrets de développement (ADR 0007) : make dev-secrets [FORCE=1]
# Valeurs aléatoires (openssl rand), jamais affichées ni journalisées. Fichiers 0400 au nom de 10001:10001 (utilisateur
# de l'image app-base), car Compose monte les secrets tels quels hors Swarm (uid/gid/mode ignorés).
# SECRETS_DIR et APPELS_INTERNES ne servent qu'aux tests (dossiers temporaires, jamais deploy/secrets/).
set -euo pipefail
set +x
DOSSIER="${SECRETS_DIR:-deploy/secrets}"
APPELS="${APPELS_INTERNES:-deploy/appels-internes.txt}"
UID_APP=10001
# alpine 3.20 épinglée par digest (index multi-architecture)
IMAGE_OUTIL="alpine:3.20@sha256:d9e853e87e55526f6b2917df91a2115c36dd7c696a35be12163d44e6e2a4b6bc"
SERVICES=" identity referentiel facturation charges-eau documents envois veille reporting "

[ -f "$APPELS" ] || { echo "Liste des appels internes introuvable : $APPELS"; exit 1; }
if [ -d "$DOSSIER" ] && [ -n "$(ls -A "$DOSSIER")" ]; then
  if [ -z "${FORCE:-}" ]; then
    echo "Secrets déjà présents dans $DOSSIER/ : rien n'est régénéré."
    echo "FORCE=1 pour les remplacer (les sessions et les jetons en cours deviendront invalides)."
    exit 0
  fi
fi

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
umask 077

openssl rand -hex 32 > "$TMP/cle_hmac_identite"
# identity seul (ADR 0007, complément) : chiffrement du secret TOTP, une ligne « <version> <clé> » par clé, la
# première chiffre ; pseudonymisation des e-mails dans les tentatives de connexion
printf '1 %s\n' "$(openssl rand -hex 32)" > "$TMP/cle_chiffrement_identity"
openssl rand -hex 32 > "$TMP/cle_pseudonymisation_identity"
# mot de passe du rôle svc_<service> de chaque base, monté sous le nom mdp_base dans le service et dans son
# conteneur <service>-migrations, qui aligne le rôle sur ce secret à chaque démarrage
for service in $SERVICES; do
  openssl rand -hex 32 > "$TMP/mdp_base_$service"
done
while read -r appelant appele reste || [ -n "${appelant:-}" ]; do
  case "${appelant:-}" in "" | "#"*) continue ;; esac
  if [[ -n "${reste:-}" || "$SERVICES" != *" $appelant "* || "$SERVICES" != *" ${appele:-?} "* || "$appelant" == "$appele" ]]; then
    echo "Ligne invalide dans $APPELS : « $appelant ${appele:-} ${reste:-} » (attendu : <appelant> <appelé>, deux services distincts)"
    exit 1
  fi
  couple="${appelant}_vers_${appele}"
  openssl rand -base64 32 | tr '+/' '-_' | tr -d '=\n' > "$TMP/jeton_$couple"
  openssl dgst -sha256 -hex -r "$TMP/jeton_$couple" | cut -d' ' -f1 > "$TMP/empreinte_$couple"
done < "$APPELS"

# les anciens fichiers ne sont retirés qu'une fois les nouveaux générés sans erreur
mkdir -p "$DOSSIER"
chmod 0700 "$DOSSIER"
find "$DOSSIER" -maxdepth 1 -type f -delete
cp "$TMP"/* "$DOSSIER"/
if ! docker run --rm --network none -v "$(realpath "$DOSSIER"):/s" "$IMAGE_OUTIL" \
  sh -c "chown $UID_APP:$UID_APP /s/* && chmod 0400 /s/*"; then
  echo "Les secrets ont été écrits dans $DOSSIER/ mais leurs droits n'ont pas pu être posés" >&2
  echo "(étape docker run : propriétaire $UID_APP:$UID_APP, mode 0400). Les services ne pourront pas les lire." >&2
  echo "Vérifiez que Docker fonctionne et que l'image $IMAGE_OUTIL est accessible, puis relancez : make dev-secrets FORCE=1" >&2
  exit 1
fi
echo "Secrets créés dans $DOSSIER/ (valeurs non affichées, fichiers 0400 au nom de l'uid $UID_APP) :"
ls -1 "$DOSSIER" | sed 's/^/  /'
