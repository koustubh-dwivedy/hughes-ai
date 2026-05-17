#!/usr/bin/env bash
# infra/bootstrap.sh — one-time data bootstrap into Cloud SQL hughes-pg.
#
# Applies migrations/*.sql, runs `make seed --profile small_cu`, runs
# `make dbt-build`, then grants cubi_runtime the precise INSERT/UPDATE
# privileges it needs on the app-state tables (everything else stays
# SELECT-only per the default privileges set by setup.sh).
#
# Idempotent: safe to re-run after a schema change.
#
# Prerequisites:
#   - infra/setup.sh has been run.
#   - gcloud authenticated with secretmanager.secretAccessor on the
#     database-url-migrate secret.

set -euo pipefail

PROJECT="${PROJECT:-tryhughes}"
INSTANCE="${INSTANCE:-hughes-pg}"
DB_NAME="${DB_NAME:-cubi}"
PROXY_PORT="${PROXY_PORT:-5433}"
PROXY_VERSION="${PROXY_VERSION:-v2.16.0}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROXY_DIR="$HOME/.cache/hughes-ai"
PROXY_BIN="$PROXY_DIR/cloud-sql-proxy"

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

INSTANCE_CONN=$(gcloud sql instances describe "$INSTANCE" --project="$PROJECT" \
  --format='value(connectionName)' 2>/dev/null)
if [[ -z "$INSTANCE_CONN" ]]; then
  echo "ERROR: Cloud SQL instance $INSTANCE not found. Run infra/setup.sh first." >&2
  exit 1
fi
ok "instance $INSTANCE_CONN"

# 2. Auto-install cloud-sql-proxy v2 if absent.
log "Cloud SQL Auth Proxy"

if [[ ! -x "$PROXY_BIN" ]]; then
  case "$(uname -s)/$(uname -m)" in
    Darwin/arm64) PLATFORM=darwin.arm64 ;;
    Darwin/x86_64) PLATFORM=darwin.amd64 ;;
    Linux/x86_64) PLATFORM=linux.amd64 ;;
    Linux/aarch64) PLATFORM=linux.arm64 ;;
    *) echo "ERROR: unsupported platform $(uname -s)/$(uname -m)" >&2; exit 1 ;;
  esac
  URL="https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/${PROXY_VERSION}/cloud-sql-proxy.${PLATFORM}"
  mkdir -p "$PROXY_DIR"
  echo "   downloading $URL"
  curl -fsSL -o "$PROXY_BIN" "$URL"
  chmod +x "$PROXY_BIN"
  ok "installed $PROXY_BIN"
else
  ok "already installed: $PROXY_BIN"
fi

# 3. Source cubi_migrate password (used by Auth Proxy auth = gcloud user).
log "Fetching credentials"

MIGRATE_URL=$(gcloud secrets versions access latest --secret=database-url-migrate --project="$PROJECT")
ok "database-url-migrate retrieved"

# Parse user:pass from the Secret Manager URL. Pattern is
# "postgresql+psycopg://USER:PASS@/cubi?host=/cloudsql/...".
MIGRATE_USER=$(echo "$MIGRATE_URL" | sed -E 's|^postgresql\+psycopg://([^:]+):.*|\1|')
MIGRATE_PASS=$(echo "$MIGRATE_URL" | sed -E 's|^postgresql\+psycopg://[^:]+:([^@]+)@.*|\1|')

# 4. Start the Auth Proxy in background; clean up on exit.
log "Starting Auth Proxy on localhost:${PROXY_PORT}"

# Prefer Application Default Credentials when set. Otherwise fall back to
# the gcloud user's current access token (short-lived; refreshed each run).
if [[ -f "$HOME/.config/gcloud/application_default_credentials.json" ]]; then
  PROXY_AUTH=""
else
  ACCESS_TOKEN=$(gcloud auth print-access-token 2>/dev/null)
  if [[ -z "$ACCESS_TOKEN" ]]; then
    echo "ERROR: no ADC and no gcloud access token. Run 'gcloud auth login' first." >&2
    exit 1
  fi
  PROXY_AUTH="--token=$ACCESS_TOKEN"
fi

# shellcheck disable=SC2086
"$PROXY_BIN" "$INSTANCE_CONN" --port="$PROXY_PORT" $PROXY_AUTH > /tmp/cloud-sql-proxy.log 2>&1 &
PROXY_PID=$!
trap 'kill "$PROXY_PID" 2>/dev/null || true' EXIT

# Wait until the proxy is accepting connections (max 30s).
for i in $(seq 1 30); do
  if (echo > /dev/tcp/localhost/"$PROXY_PORT") >/dev/null 2>&1; then
    ok "proxy ready (pid=$PROXY_PID, ${i}s)"
    break
  fi
  if [[ $i -eq 30 ]]; then
    echo "ERROR: Auth Proxy did not start within 30s; logs:" >&2
    cat /tmp/cloud-sql-proxy.log >&2
    exit 1
  fi
  sleep 1
done

# TCP DATABASE_URL for everything that runs through the proxy.
TCP_DATABASE_URL="postgresql://${MIGRATE_USER}:${MIGRATE_PASS}@localhost:${PROXY_PORT}/${DB_NAME}"

# 5a. Optional: wipe the public schema. Set WIPE_FIRST=1 when re-bootstrapping
#     against a DB that already has previous migration state. The migrations
#     here are NOT idempotent across re-applies (e.g., ALTER TABLE ADD
#     CONSTRAINT in 003_members.sql doesn't guard with IF NOT EXISTS — that's
#     a known gap in the migration files, fixable but out of scope here).
if [[ "${WIPE_FIRST:-0}" == "1" ]]; then
  log "WIPE_FIRST=1 — dropping public schema"
  uv run python - "$TCP_DATABASE_URL" <<'PY'
import sys
import psycopg
with psycopg.connect(sys.argv[1], autocommit=True) as conn, conn.cursor() as cur:
    cur.execute("DROP SCHEMA IF EXISTS public CASCADE")
    cur.execute("CREATE SCHEMA public")
    cur.execute("GRANT ALL ON SCHEMA public TO cubi_migrate")
    cur.execute("GRANT USAGE ON SCHEMA public TO cubi_runtime")
PY
  ok "public schema dropped + recreated"
fi

# 5b. init.sql (pgvector + role default privileges). Applied here rather
#     than in setup.sh because setup.sh has no Auth Proxy / psql equivalent
#     available without an extra binary install. Idempotent (CREATE
#     EXTENSION IF NOT EXISTS + ALTER DEFAULT PRIVILEGES that can be
#     re-applied safely).
log "Applying init.sql (pgvector + role grants)"
uv run python - "$TCP_DATABASE_URL" "$REPO_ROOT/infra/sql/init.sql" <<'PY'
import sys
import psycopg

db_url, sql_path = sys.argv[1], sys.argv[2]
with open(sql_path) as f:
    sql = f.read()
with psycopg.connect(db_url) as conn, conn.cursor() as cur:
    cur.execute(sql)
    conn.commit()
PY
ok "init.sql applied"

# 5b. Migrations.
log "Applying migrations"
DATABASE_URL="$TCP_DATABASE_URL" uv run python "$REPO_ROOT/scripts/apply_migrations.py"
ok "migrations applied"

# 6. Seed. Always use --force here: the content-hash cache in seed.py is
#    laptop-local and shared across DBs, so a cache hit from a prior local
#    Postgres seed would falsely skip Cloud SQL seeding. --force costs
#    ~30s and guarantees the rows land in this DB.
log "Seeding (small_cu profile, --force)"
DATABASE_URL="$TCP_DATABASE_URL" uv run python "$REPO_ROOT/scripts/seed.py" --profile small_cu --force
ok "seed complete"

# 7. dbt build. NOTE: not `--select staging marts` (which the Makefile uses
#    for local dev) — that excludes `models/core/` (dim_calendar etc.) and
#    fails on a fresh DB. For first-time bootstrap we need everything.
log "Building dbt models"
export DBT_HOST=localhost
export DBT_PORT="$PROXY_PORT"
export DBT_USER="$MIGRATE_USER"
export DBT_PASSWORD="$MIGRATE_PASS"
export DBT_DBNAME="$DB_NAME"
(cd "$REPO_ROOT/packages/dbt-models" && uv run dbt build --profiles-dir . --quiet)
ok "dbt build done"

# 8. Grant cubi_runtime the precise app-state writes it needs. Lending-data
#    tables stay SELECT-only via the default privileges set in setup.sh.
log "Granting cubi_runtime app-state writes"

uv run python - "$TCP_DATABASE_URL" <<'PY'
import sys
import psycopg

db_url = sys.argv[1]
APP_STATE_TABLES = [
    "query_history",
    "threads",
    "thread_messages",
    "research_plans",
    "research_lead_notes",
    "research_steps",
    "research_findings",
    # HUG-258 follow-up: missed by the original bootstrap; subagent_calls
    # is written by the lead-agent's run_subagent tool path.
    "subagent_calls",
]

with psycopg.connect(db_url) as conn, conn.cursor() as cur:
    # USAGE on sequences (so INSERTs that use SERIAL/IDENTITY can call nextval).
    cur.execute("GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO cubi_runtime")
    for t in APP_STATE_TABLES:
        cur.execute(f"GRANT INSERT, UPDATE ON {t} TO cubi_runtime")  # noqa: S608  # nosec
        print(f"   GRANT INSERT, UPDATE ON {t}")
    conn.commit()
PY
ok "grants applied"

# 9. Verify seed row counts.
log "Verifying row counts"
DATABASE_URL="$TCP_DATABASE_URL" uv run python "$REPO_ROOT/scripts/verify_seed.py"
ok "row counts verified"

# 10. Smoke-check the read-only guarantee using cubi_runtime.
log "Smoke-testing cubi_runtime privileges"

RUNTIME_URL=$(gcloud secrets versions access latest --secret=database-url --project="$PROJECT")
RUNTIME_USER=$(echo "$RUNTIME_URL" | sed -E 's|^postgresql\+psycopg://([^:]+):.*|\1|')
RUNTIME_PASS=$(echo "$RUNTIME_URL" | sed -E 's|^postgresql\+psycopg://[^:]+:([^@]+)@.*|\1|')
RUNTIME_TCP_URL="postgresql://${RUNTIME_USER}:${RUNTIME_PASS}@localhost:${PROXY_PORT}/${DB_NAME}"

uv run python - "$RUNTIME_TCP_URL" <<'PY'
import sys
import psycopg

db_url = sys.argv[1]

with psycopg.connect(db_url) as conn:
    # cubi_runtime CAN SELECT on lending tables.
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM members")
        n = cur.fetchone()[0]
    assert n >= 3000, f"members count too low: {n}"

    # cubi_runtime CANNOT INSERT on lending tables.
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO members (member_id, first_name, last_name, joined_at) "
                "VALUES (gen_random_uuid(), 'x', 'x', NOW())"
            )
        conn.rollback()
        print("   ✗ INSERT INTO members SHOULD have been denied")
        raise SystemExit(2)
    except psycopg.errors.InsufficientPrivilege:
        conn.rollback()

    # cubi_runtime CAN INSERT on query_history (app-state). The harmless
    # 'smoke' row stays — query_history is append-only; that's the design.
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO query_history (question, sql) VALUES ('smoke', 'SELECT 1')"
        )
    conn.commit()

print("   ✓ cubi_runtime read-only on lending, INSERT-able on app-state")
PY

ok "privilege model verified"

log "Bootstrap complete"
cat <<EOF

  Database:  $DB_NAME (instance $INSTANCE_CONN)
  Migrate role: $MIGRATE_USER (used by bootstrap.sh only)
  Runtime role: $RUNTIME_USER (used by Cloud Run)
  Next: infra/deploy-api.sh (HUG-254) to bring the API online.
EOF
