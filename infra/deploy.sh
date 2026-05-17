#!/usr/bin/env bash
# infra/deploy.sh — one-command redeploy. Orchestrates deploy-api.sh and
# deploy-frontend.sh with pre-flight checks.
#
# Default: refuses to run if the working tree is dirty. Override with
# ALLOW_DIRTY=1 (useful during iteration).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

log() { printf '\n\033[1;34m▸ %s\033[0m\n' "$*"; }
ok()  { printf '   \033[0;32m✓\033[0m %s\n' "$*"; }

log "Pre-flight"

if ! command -v gcloud >/dev/null; then
  echo "ERROR: gcloud not installed." >&2; exit 1
fi
ok "gcloud present"

if ! gcloud auth list --filter=status:ACTIVE --format='value(account)' | grep -q .; then
  echo "ERROR: gcloud has no active account. Run: gcloud auth login" >&2; exit 1
fi
ok "gcloud authenticated as $(gcloud config get account 2>/dev/null)"

if [[ -z "${ALLOW_DIRTY:-}" ]] && [[ -n "$(git status --porcelain)" ]]; then
  echo "ERROR: working tree has uncommitted changes." >&2
  echo "Either commit them or re-run with ALLOW_DIRTY=1 to proceed anyway." >&2
  git status --short >&2
  exit 1
fi

log "deploy-api.sh"
bash "$REPO_ROOT/infra/deploy-api.sh"

log "deploy-frontend.sh"
bash "$REPO_ROOT/infra/deploy-frontend.sh"

log "All done"
cat <<EOF

  Default site: https://tryhughes.web.app
  Custom site:  https://app.tryhughes.com  (after HUG-256 DNS records are live)
EOF
