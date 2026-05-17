#!/usr/bin/env bash
# infra/deploy-api.sh — build the API image (Cloud Build) and deploy to
# Cloud Run hughes-api.
#
# Tags images with the git SHA (immutable; for rollback) and :latest.
# If the working tree is dirty, the SHA tag is suffixed with -dirty and a
# warning is printed (don't block — useful during iteration; runbook says
# commit-first for prod).
#
# Idempotent: every run produces a new Cloud Run revision routed 100% by
# default. Roll back with `gcloud run services update-traffic hughes-api
# --to-revisions=<prev>=100`.

set -euo pipefail

PROJECT="${PROJECT:-tryhughes}"
PROJECT_NUMBER="${PROJECT_NUMBER:-14067832725}"
REGION="${REGION:-europe-west1}"
INSTANCE="${INSTANCE:-hughes-pg}"
REGISTRY_REPO="${REGISTRY_REPO:-hughes}"
SERVICE="${SERVICE:-hughes-api}"
RUNTIME_SA="${RUNTIME_SA:-hughes-api-sa}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log() { printf '\n\033[1;34m▸ %s\033[0m\n' "$*"; }
ok()  { printf '   \033[0;32m✓\033[0m %s\n' "$*"; }
warn(){ printf '   \033[0;33m!\033[0m %s\n' "$*"; }

# 1. Pre-flight.
log "Pre-flight"

if ! gcloud projects describe "$PROJECT" >/dev/null 2>&1; then
  echo "ERROR: cannot access project $PROJECT" >&2
  exit 1
fi
ok "project $PROJECT"

SA_EMAIL="${RUNTIME_SA}@${PROJECT}.iam.gserviceaccount.com"
if ! gcloud iam service-accounts describe "$SA_EMAIL" --project="$PROJECT" >/dev/null 2>&1; then
  echo "ERROR: runtime SA $SA_EMAIL not found. Run infra/setup.sh first." >&2
  exit 1
fi
ok "SA $SA_EMAIL"

INSTANCE_CONN=$(gcloud sql instances describe "$INSTANCE" --project="$PROJECT" \
  --format='value(connectionName)' 2>/dev/null)
if [[ -z "$INSTANCE_CONN" ]]; then
  echo "ERROR: Cloud SQL instance $INSTANCE not found." >&2
  exit 1
fi
ok "instance $INSTANCE_CONN"

# Compute image tag from git SHA. Mark dirty trees explicitly.
cd "$REPO_ROOT"
SHA=$(git rev-parse --short HEAD)
if [[ -n "$(git status --porcelain)" ]]; then
  TAG="${SHA}-dirty"
  warn "working tree is dirty; tagging image ${TAG}"
else
  TAG="$SHA"
fi
IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT}/${REGISTRY_REPO}/api"

# 2. Build via Cloud Build (native amd64; bypasses arm64 cross-compile).
log "Cloud Build → ${IMAGE_URI}:${TAG}"
gcloud builds submit "$REPO_ROOT" \
  --config=/dev/stdin --project="$PROJECT" \
  --substitutions=_TAG="$TAG",_IMAGE="$IMAGE_URI" <<'YAML'
steps:
  - name: gcr.io/cloud-builders/docker
    args: ['build', '-f', 'packages/api/Dockerfile', '-t', '${_IMAGE}:${_TAG}', '-t', '${_IMAGE}:latest', '.']
  - name: gcr.io/cloud-builders/docker
    args: ['push', '${_IMAGE}:${_TAG}']
  - name: gcr.io/cloud-builders/docker
    args: ['push', '${_IMAGE}:latest']
options:
  logging: CLOUD_LOGGING_ONLY
YAML
ok "image pushed"

# 3. Deploy.
log "Cloud Run deploy"
gcloud run deploy "$SERVICE" \
  --image="${IMAGE_URI}:${TAG}" \
  --region="$REGION" --project="$PROJECT" \
  --min-instances=1 --max-instances=3 \
  --memory=2Gi --cpu=1 --timeout=300 --concurrency=40 \
  --add-cloudsql-instances="$INSTANCE_CONN" \
  --service-account="$SA_EMAIL" \
  --set-secrets=DATABASE_URL=database-url:latest,OLLAMA_API_KEY=ollama-api-key:latest \
  --set-env-vars=API_WARM_CATALOG=1,API_ROOT_PATH=/api \
  --no-allow-unauthenticated \
  --quiet
ok "service deployed"

# 4. Grant Firebase Hosting permission to invoke Cloud Run.
log "Granting Firebase Hosting → run.invoker"
FH_SA="service-${PROJECT_NUMBER}@gcp-sa-firebasehosting.iam.gserviceaccount.com"
gcloud run services add-iam-policy-binding "$SERVICE" \
  --member="serviceAccount:${FH_SA}" \
  --role="roles/run.invoker" \
  --region="$REGION" --project="$PROJECT" --quiet >/dev/null
ok "${FH_SA} can invoke ${SERVICE}"

SERVICE_URL=$(gcloud run services describe "$SERVICE" --region="$REGION" --project="$PROJECT" --format='value(status.url)')

log "Deploy complete"
cat <<EOF

  Service URL:  $SERVICE_URL
  Image tag:    ${IMAGE_URI}:${TAG}
  Health check: curl -H "Authorization: Bearer \$(gcloud auth print-identity-token)" $SERVICE_URL/api/health

  Cold-start warmup may take up to ~4 min on the first request after a
  new revision. min-instances=1 keeps a warm instance after that.
EOF
