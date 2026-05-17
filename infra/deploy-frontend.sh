#!/usr/bin/env bash
# infra/deploy-frontend.sh — build packages/frontend and deploy to Firebase
# Hosting (tryhughes).
#
# Tries firebase-tools auth via gcloud ADC first; if that fails, prints
# clear instructions for the one-time `firebase login` and exits.

set -euo pipefail

PROJECT="${PROJECT:-tryhughes}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log() { printf '\n\033[1;34m▸ %s\033[0m\n' "$*"; }
ok()  { printf '   \033[0;32m✓\033[0m %s\n' "$*"; }

# 1. Pre-flight.
log "Pre-flight"

if ! command -v firebase >/dev/null; then
  echo "ERROR: firebase CLI not installed. Run: npm install -g firebase-tools" >&2
  exit 1
fi
ok "firebase CLI present ($(firebase --version 2>/dev/null | head -1))"

if ! command -v pnpm >/dev/null; then
  echo "ERROR: pnpm not installed." >&2
  exit 1
fi
ok "pnpm present"

# 2. Build the SPA.
log "Building SPA"
(cd "$REPO_ROOT/packages/frontend" && pnpm install --frozen-lockfile && pnpm build)
DIST="$REPO_ROOT/packages/frontend/dist"
if [[ ! -d "$DIST" ]]; then
  echo "ERROR: build did not produce $DIST" >&2
  exit 1
fi
ok "dist produced ($(du -sh "$DIST" | awk '{print $1}'))"

# 3. Deploy. firebase-tools picks up gcloud ADC when present; if not, it
#    prompts for `firebase login`, which we don't want in autonomous mode.
log "Deploying to Firebase Hosting (project: $PROJECT)"

set +e
firebase deploy --only hosting --project "$PROJECT" --non-interactive
RC=$?
set -e

if [[ $RC -ne 0 ]]; then
  echo
  echo "Firebase deploy failed. Most likely cause: firebase-tools needs"
  echo "interactive auth. Run the following once, then re-run this script:"
  echo
  echo "    firebase login"
  echo
  echo "If you're on a headless machine, generate a CI token instead:"
  echo "    firebase login:ci"
  echo "    # then export FIREBASE_TOKEN=<token> before re-running this script."
  exit $RC
fi

ok "deployed"

log "Done"
cat <<EOF

  SPA URL: https://${PROJECT}.web.app
            https://${PROJECT}.firebaseapp.com
  API:     https://${PROJECT}.web.app/api/health  (rewrites to Cloud Run hughes-api)

  Custom domain app.tryhughes.com is wired in HUG-256 (operator step).
EOF
