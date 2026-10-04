#!/usr/bin/env bash
# Prépare le VPS Hetzner CPX32 (Debian 13) — à écrire au lot 2 selon SPEC_TECHNIQUE § 11.2, § 11.4 (TEC-WEB-09/12), § 12.
# Étapes attendues (ne rien exécuter avant relecture) :
#  1. utilisateur non-root + sudo, SSH par clé seulement, unattended-upgrades, nftables (443, 80, 51820/udp)
#  2. WireGuard (serveur sur le VPS, pair = poste de Youssef et réseau Proxmox pour les sauvegardes)
#  3. volume Hetzner → LUKS2 (cryptsetup luksFormat, aes-xts-plain64) → /srv/app ; unité systemd RequiresMountsFor pour la pile
#  4. Docker CE, GHCR login (jeton lecture seule), runner GitHub auto-hébergé (service systemd, utilisateur dédié)
#  5. nginx (nginx.prod.conf), certbot DNS-01, CrowdSec + bouncer (ou fail2ban), page de maintenance
#  6. restic (NAS via WireGuard + stockage objet), timers de sauvegarde 03:00, script de vérification
#  7. docker compose -f compose.prod.yml up -d ; testssl.sh ; nmap externe ; restauration de test
set -euo pipefail
echo "Script à compléter au lot 2 (voir en-tête). Aucune action exécutée."
