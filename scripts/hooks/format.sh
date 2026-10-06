#!/usr/bin/env bash
# Hook PostToolUse (Edit|Write) : formate le fichier modifié selon son type. Lit l'entrée JSON du hook sur stdin.
cd "$CLAUDE_PROJECT_DIR"
set -euo pipefail
file=$(jq -r '.tool_input.file_path // empty' 2>/dev/null || true)
[ -z "$file" ] && exit 0
case "$file" in
  *.py) command -v ruff >/dev/null && ruff format "$file" >/dev/null 2>&1 && ruff check --fix "$file" >/dev/null 2>&1 || true ;;
  *.ts|*.tsx|*.js|*.jsx|*.css|*.json|*.md) [ -f front/node_modules/.bin/prettier ] && front/node_modules/.bin/prettier --write "$file" >/dev/null 2>&1 || true ;;
esac
exit 0
