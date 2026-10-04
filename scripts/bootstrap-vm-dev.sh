#!/usr/bin/env bash
# Prépare une VM Debian 13 (Trixie) de développement : Docker, uv (Python 3.12), Node 22, gh, Claude Code, outils.
# Usage : sudo bash scripts/bootstrap-vm-dev.sh <utilisateur>
set -euo pipefail
USER_NAME="${1:-$SUDO_USER}"
[ -z "$USER_NAME" ] && { echo "utilisateur requis"; exit 1; }

apt-get update
apt-get install -y --no-install-recommends ca-certificates curl git gnupg jq make unzip build-essential \
  libpango-1.0-0 libpangoft2-1.0-0 libcairo2 libgdk-pixbuf-2.0-0 fonts-dejavu-core shared-mime-info \
  postgresql-client ripgrep fd-find

# Docker CE (dépôt officiel)
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" > /etc/apt/sources.list.d/docker.list
apt-get update && apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
usermod -aG docker "$USER_NAME"

# GitHub CLI
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg -o /etc/apt/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" > /etc/apt/sources.list.d/github-cli.list
apt-get update && apt-get install -y gh

# Node 22 (NodeSource)
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt-get install -y nodejs

# uv (gestion de Python 3.12 et des dépendances), Claude Code — installés pour l'utilisateur, pas root
sudo -u "$USER_NAME" bash <<'USR'
set -e
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
uv python install 3.12
# Claude Code : installateur natif (voir https://code.claude.com/docs/en/setup pour les alternatives npm / Homebrew)
curl -fsSL https://claude.ai/install.sh | bash
# testssl.sh pour les vérifications TLS (lot 2)
[ -d "$HOME/testssl.sh" ] || git clone --depth 1 https://github.com/testssl/testssl.sh.git "$HOME/testssl.sh"
echo 'export PATH="$HOME/.local/bin:$HOME/testssl.sh:$PATH"' >> "$HOME/.bashrc"
USR

cat <<MSG

VM prête. Étapes suivantes (en tant que $USER_NAME, nouvelle session shell) :
  1. gh auth login          # GitHub (2FA + clé matérielle sur le compte)
  2. git clone <dépôt> && cd <dépôt>
  3. claude                 # première connexion Claude Code, puis /status et /doctor
  4. make doctor && make dev-up
MSG
