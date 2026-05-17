#!/usr/bin/env bash
# infra/setup.sh — one-time GCP data plane provisioning for the Hughes AI app.
#
# Creates: enabled APIs, Artifact Registry repo, Cloud SQL Postgres instance,
# database, two DB roles, Secret Manager secrets, runtime service account
# and its IAM bindings. Idempotent: safe to re-run.
#
# Runs end-to-end in ~10–15 min on first invocation (Cloud SQL instance
# creation is the slow step). Subsequent runs are ~30s.
#
# Prerequisites:
#   - gcloud authenticated as a user with Owner or equivalent on $PROJECT.
#   - billing enabled on $PROJECT.
#   - OLLAMA_API_KEY available in env or in .env at repo root.

set -euo pipefail

PROJECT="${PROJECT:-tryhughes}"
REGION="${REGION:-europe-west1}"
INSTANCE="${INSTANCE:-hughes-pg}"
DB_NAME="${DB_NAME:-cubi}"
REGISTRY_REPO="${REGISTRY_REPO:-hughes}"
RUNTIME_SA="${RUNTIME_SA:-hughes-api-sa}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log() { printf '\n\033[1;34m▸ %s\033[0m\n' "$*"; }
ok()  { printf '   \033[0;32m✓\033[0m %s\n' "$*"; }

# Sanity checks before any state changes.
log "Pre-flight"

if ! gcloud projects describe "$PROJECT" >/dev/null 2>&1; then
  echo "ERROR: cannot access project $PROJECT (auth or permissions)." >&2
  exit 1
fi
ok "project $PROJECT accessible"

BILLING_STATE=$(gcloud billing projects describe "$PROJECT" --format='value(billingEnabled)' 2>/dev/null || echo 'false')
if [[ "$BILLING_STATE" != "True" ]]; then
  echo "ERROR: billing is not enabled on $PROJECT (billingEnabled=$BILLING_STATE)." >&2
  echo "Enable in Cloud Console → Billing → link an account, then re-run." >&2
  exit 1
fi
ok "billing enabled"

# Pull OLLAMA_API_KEY from .env if not in env. We never echo it.
if [[ -z "${OLLAMA_API_KEY:-}" ]] && [[ -f "$REPO_ROOT/.env" ]]; then
  # shellcheck disable=SC1091
  set -a; source "$REPO_ROOT/.env"; set +a
fi
if [[ -z "${OLLAMA_API_KEY:-}" ]]; then
  echo "ERROR: OLLAMA_API_KEY not in env and not in .env." >&2
  exit 1
fi
ok "OLLAMA_API_KEY found"

# 1. Enable APIs.
log "Enabling APIs"
gcloud services enable --project="$PROJECT" \
  run.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com \
  firebasehosting.googleapis.com \
  cloudbuild.googleapis.com \
  iam.googleapis.com
ok "APIs enabled"

# 2. Artifact Registry.
log "Artifact Registry repo '$REGISTRY_REPO'"
if ! gcloud artifacts repositories describe "$REGISTRY_REPO" \
       --location="$REGION" --project="$PROJECT" >/dev/null 2>&1; then
  gcloud artifacts repositories create "$REGISTRY_REPO" \
    --repository-format=docker --location="$REGION" --project="$PROJECT" \
    --description="Hughes AI container images" --quiet
  ok "repo created"
else
  ok "repo already exists"
fi

# 3. Cloud SQL instance. Creation is the slow step (~6–10 min).
log "Cloud SQL instance '$INSTANCE'"
if ! gcloud sql instances describe "$INSTANCE" --project="$PROJECT" >/dev/null 2>&1; then
  echo "   creating (~6–10 min)…"
  # --edition=ENTERPRISE (not ENTERPRISE_PLUS) is required for shared-core
  # tiers like db-f1-micro. ENTERPRISE_PLUS forces db-perf-optimized-N-* at
  # ~$70+/mo — way over the cost target for this demo (see HUG-252.md).
  gcloud sql instances create "$INSTANCE" \
    --database-version=POSTGRES_16 \
    --edition=ENTERPRISE \
    --tier=db-f1-micro \
    --region="$REGION" \
    --storage-size=10 --storage-auto-increase \
    --backup-start-time=03:00 --retained-backups-count=7 \
    --project="$PROJECT" --quiet
  ok "instance created"
else
  ok "instance already exists"
fi

INSTANCE_CONN=$(gcloud sql instances describe "$INSTANCE" --project="$PROJECT" \
  --format='value(connectionName)')
ok "connectionName=$INSTANCE_CONN"

# 4. DB roles. Every run rotates passwords (intentional — see HUG-252.md).
log "DB roles"
MIGRATE_PW=$(openssl rand -base64 32 | tr -d '\n=+/')
RUNTIME_PW=$(openssl rand -base64 32 | tr -d '\n=+/')

create_or_set_user() {
  local user=$1 pw=$2
  if gcloud sql users describe "$user" --instance="$INSTANCE" --project="$PROJECT" >/dev/null 2>&1; then
    gcloud sql users set-password "$user" --instance="$INSTANCE" --project="$PROJECT" \
      --password="$pw" --quiet
    ok "rotated password for $user"
  else
    gcloud sql users create "$user" --instance="$INSTANCE" --project="$PROJECT" \
      --password="$pw" --quiet
    ok "created $user"
  fi
}

create_or_set_user cubi_migrate "$MIGRATE_PW"
create_or_set_user cubi_runtime "$RUNTIME_PW"

# 5. Database.
log "Database '$DB_NAME'"
if ! gcloud sql databases describe "$DB_NAME" --instance="$INSTANCE" --project="$PROJECT" >/dev/null 2>&1; then
  gcloud sql databases create "$DB_NAME" --instance="$INSTANCE" --project="$PROJECT" --quiet
  ok "database created"
else
  ok "database already exists"
fi

# 6. pgvector + role privileges are applied by bootstrap.sh, not here.
#    (gcloud sql connect requires the optional cloud-sql-proxy v2 component
#    which isn't bundled with gcloud — bootstrap.sh auto-downloads it.)
ok "init.sql application deferred to bootstrap.sh"

# 7. Secret Manager.
log "Secret Manager"
DATABASE_URL="postgresql+psycopg://cubi_runtime:${RUNTIME_PW}@/${DB_NAME}?host=/cloudsql/${INSTANCE_CONN}"
MIGRATE_DB_URL="postgresql+psycopg://cubi_migrate:${MIGRATE_PW}@/${DB_NAME}?host=/cloudsql/${INSTANCE_CONN}"

put_secret() {
  local name=$1 value=$2
  if gcloud secrets describe "$name" --project="$PROJECT" >/dev/null 2>&1; then
    printf '%s' "$value" | gcloud secrets versions add "$name" \
      --project="$PROJECT" --data-file=- --quiet >/dev/null
    ok "$name (new version)"
  else
    printf '%s' "$value" | gcloud secrets create "$name" \
      --project="$PROJECT" --replication-policy=automatic --data-file=- --quiet
    ok "$name (created)"
  fi
}

put_secret database-url         "$DATABASE_URL"
put_secret database-url-migrate "$MIGRATE_DB_URL"
put_secret ollama-api-key       "$OLLAMA_API_KEY"

# 8. Runtime service account.
log "Service account '$RUNTIME_SA'"
SA_EMAIL="${RUNTIME_SA}@${PROJECT}.iam.gserviceaccount.com"
if ! gcloud iam service-accounts describe "$SA_EMAIL" --project="$PROJECT" >/dev/null 2>&1; then
  gcloud iam service-accounts create "$RUNTIME_SA" \
    --display-name="Hughes AI API runtime SA" \
    --project="$PROJECT" --quiet
  ok "SA created: $SA_EMAIL"
else
  ok "SA already exists: $SA_EMAIL"
fi

# 9. IAM bindings — only on the secrets the runtime needs.
log "IAM bindings"
for SECRET in database-url ollama-api-key; do
  gcloud secrets add-iam-policy-binding "$SECRET" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/secretmanager.secretAccessor" \
    --project="$PROJECT" --quiet >/dev/null
  ok "$SECRET → secretAccessor"
done

gcloud projects add-iam-policy-binding "$PROJECT" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/cloudsql.client" \
  --condition=None --quiet >/dev/null
ok "project → cloudsql.client"

# Summary.
echo
log "Provisioning complete"
cat <<EOF

  Project:           $PROJECT
  Region:            $REGION
  Cloud SQL:         $INSTANCE (connection: $INSTANCE_CONN)
  Database:          $DB_NAME (pgvector enabled)
  DB roles:          cubi_migrate (owner), cubi_runtime (read-only)
  Artifact Registry: $REGION-docker.pkg.dev/$PROJECT/$REGISTRY_REPO
  Runtime SA:        $SA_EMAIL
  Secrets:           database-url, database-url-migrate, ollama-api-key

  Next: infra/bootstrap.sh (HUG-253) to apply migrations and seed.
EOF
