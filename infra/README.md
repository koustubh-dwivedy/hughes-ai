# `infra/` — Hughes AI GCP deployment

This directory holds everything needed to deploy the Hughes AI app to GCP at `app.tryhughes.com`. It's a small set of scripts plus a runbook — manual-deploy by design (no CI/CD automation in v1).

## Target architecture

```
Internet
   │
   ▼
DNS  app.tryhughes.com  ──►  Firebase Hosting  (free; global CDN; auto TLS)
                                │
                                ├─ Static SPA: packages/frontend/dist/
                                │
                                └─ /api/**  ──►  Cloud Run: hughes-api
                                                     │
                                                     │  FastAPI / uvicorn :8080
                                                     │  min-instances=1  (always warm)
                                                     │  max-instances=3  (cost ceiling)
                                                     │  --no-allow-unauthenticated
                                                     │
                                                     ├──►  Cloud SQL Postgres
                                                     │       hughes-pg, db-f1-micro
                                                     │       + pgvector
                                                     │
                                                     └──►  Ollama Cloud (GLM 5.1)
                                                              https://ollama.com
```

## Identifiers

| Resource | Value |
|---|---|
| GCP project | `tryhughes` |
| Region | `europe-west1` |
| Cloud SQL instance | `hughes-pg` |
| Database | `cubi` |
| DB roles | `cubi_migrate` (owner), `cubi_runtime` (read-only) |
| Artifact Registry | `europe-west1-docker.pkg.dev/tryhughes/hughes` |
| Cloud Run service | `hughes-api` |
| Runtime service account | `hughes-api-sa@tryhughes.iam.gserviceaccount.com` |
| Secrets | `database-url`, `database-url-migrate`, `ollama-api-key` |
| Public URL | `app.tryhughes.com` (Namecheap A records → Firebase Hosting) |

## Scripts

| Script | What it does | When to run |
|---|---|---|
| `setup.sh` | One-time GCP provisioning: APIs, Cloud SQL, Secret Manager, Artifact Registry, IAM, service account. Idempotent. | First-time bring-up; disaster recovery; second-environment provisioning. |
| `bootstrap.sh` | Applies the 17 migrations against Cloud SQL, runs `make seed --profile small_cu`, runs `make dbt-build`. | After `setup.sh`; after any schema change. |
| `deploy-api.sh` | Builds the API image via Cloud Build, pushes to Artifact Registry, deploys to Cloud Run. | Every API code change. |
| `deploy-frontend.sh` | Builds `packages/frontend` to `dist/`, deploys to Firebase Hosting. | Every frontend code change. |
| `deploy.sh` | Orchestrates `deploy-api.sh` + `deploy-frontend.sh` with pre-flight checks. | Standard redeploy. |

## First-time bring-up (this is the order)

### 0. Prerequisites

- `gcloud` authenticated as a user with Owner on `tryhughes`. Verify with `gcloud auth list`.
- `firebase` CLI installed (`npm install -g firebase-tools`) and authenticated. `firebase login` once if needed.
- Billing enabled on `tryhughes`. Verify with `gcloud billing projects describe tryhughes --format='value(billingEnabled)'` → `True`.
- `OLLAMA_API_KEY` available in `.env` at the repo root, or exported in the shell.

### 1. Provision the data plane

```bash
bash infra/setup.sh
```

Takes ~6–10 min on first run (Cloud SQL instance creation is the slow step). Subsequent runs are ~30 sec and rotate the DB role passwords (the new versions land in Secret Manager; previous versions stay in history).

**What it produces:**
- 7 APIs enabled (run, sqladmin, secretmanager, artifactregistry, firebasehosting, cloudbuild, iam).
- Artifact Registry repo `hughes` in `europe-west1`.
- Cloud SQL `hughes-pg` (POSTGRES_16, db-f1-micro) with database `cubi` and `pgvector`.
- DB roles `cubi_migrate` and `cubi_runtime` with default privileges.
- Secrets `database-url`, `database-url-migrate`, `ollama-api-key`.
- Service account `hughes-api-sa` with `secretmanager.secretAccessor` on the two relevant secrets and `cloudsql.client` at project level.

### 2. Bootstrap the demo data

```bash
bash infra/bootstrap.sh
```

What it does:
- Auto-installs Cloud SQL Auth Proxy v2 to `~/.cache/hughes-ai/cloud-sql-proxy` if not present.
- Starts the proxy on `localhost:5433`.
- Runs `scripts/apply_migrations.py` against the Cloud SQL DB (applies the 17 idempotent SQL files).
- Runs `make seed --profile small_cu` and `make dbt-build` against the Cloud SQL DB.
- Grants `cubi_runtime` the `INSERT, UPDATE` privileges it needs on app-state tables (threads, query_history, research_*). Lending data stays SELECT-only.
- Runs `scripts/verify_seed.py` to assert row-count floors (3000 members / 8000 deposit_accounts / 500 applications).
- Smoke-checks the privilege model end-to-end.

Idempotent; safe to re-run after a schema change.

### 3. Deploy the API to Cloud Run

```bash
bash infra/deploy-api.sh
```

What it does:
- Builds the image via Cloud Build (native amd64; bypasses arm64 cross-compile).
- Tags as `{git-sha}` + `:latest`; dirty trees get `-dirty` suffix on the SHA tag.
- Deploys `hughes-api` to Cloud Run `europe-west1` with `min-instances=1`, `max-instances=3`, secrets, `--no-allow-unauthenticated`, and the dedicated runtime SA.
- Grants Firebase Hosting's service identity `roles/run.invoker` on `hughes-api`.

### 4. Deploy the SPA to Firebase Hosting

```bash
bash infra/deploy-frontend.sh
```

If the script exits with an auth error, run `firebase login` once (interactive), then re-run.

### 5. Wire `app.tryhughes.com` (DNS at Namecheap)

The domain registrar is **Namecheap**. Firebase Hosting will tell you the exact records needed.

1. Firebase Console → project `tryhughes` → Hosting → "Add custom domain" → enter `app.tryhughes.com`.
2. Firebase returns a TXT record (verification) and two A records (traffic).
3. In Namecheap → Domain List → `tryhughes.com` → Manage → Advanced DNS → "Add New Record":
   - **TXT record**: Type=`TXT`, Host=`_firebase-hosting-verification.app` (or whatever Firebase shows), Value=(from Firebase), TTL=Automatic.
   - Once Firebase verifies (~5–15 min), Firebase will swap to asking for two **A records**: Type=`A`, Host=`app`, Value=(IPs from Firebase), TTL=Automatic. Add both.
4. SSL provisions automatically ~20–30 min after DNS propagates.
5. Verify:
   ```bash
   dig +short A app.tryhughes.com           # returns Firebase IPs
   curl -sI https://app.tryhughes.com/      # 200, valid cert
   curl -sI https://app.tryhughes.com/api/health  # 200
   ```

### 6. Enable cost cap on Ollama Cloud

The Ollama Cloud dashboard is the only place to set a hard monthly spend cap.

1. Log in to your Ollama Cloud account.
2. Billing → Usage Limits → set a monthly cap (suggested: $25 to start; raise once you understand traffic).
3. Confirm the cap shows in the dashboard.

### 7. Run runtime-role assertions

```bash
make verify-prod-role
```

This starts the Cloud SQL Auth Proxy and runs `pytest infra/tests/test_runtime_role.py`, which asserts the `cubi_runtime` role can SELECT all tables, INSERT/UPDATE app-state tables, and CANNOT INSERT/UPDATE/DELETE lending tables. Fail = privilege drift; investigate before the next deploy.

## Runbook

### Inspect logs

```bash
# Cloud Run (API logs, structlog JSON)
gcloud run services logs read hughes-api --region=europe-west1 --project=tryhughes --limit=100

# Tail in real time
gcloud run services logs tail hughes-api --region=europe-west1 --project=tryhughes

# Cloud SQL (instance logs)
gcloud logging read 'resource.type="cloudsql_database" AND resource.labels.database_id="tryhughes:hughes-pg"' \
  --project=tryhughes --limit=50 --format='value(textPayload)'

# Firebase Hosting (request logs — visible in Firebase Console; not via gcloud)
# https://console.firebase.google.com/project/tryhughes/hosting/main
```

### Roll back a bad deploy

```bash
# List recent Cloud Run revisions.
gcloud run revisions list --service=hughes-api --region=europe-west1 --project=tryhughes \
  --format='table(metadata.name,metadata.creationTimestamp,status.imageDigest)' --limit=10

# Send 100% of traffic to a previous revision.
gcloud run services update-traffic hughes-api --region=europe-west1 --project=tryhughes \
  --to-revisions=hughes-api-00042-xyz=100

# Firebase Hosting rollback — via Console (Hosting → Release history → Rollback)
# or:
firebase hosting:rollback --project=tryhughes
```

### Rotate `OLLAMA_API_KEY`

```bash
# 1. Add a new secret version with the new key value.
printf '%s' "$NEW_KEY" | gcloud secrets versions add ollama-api-key \
  --project=tryhughes --data-file=-

# 2. Roll the Cloud Run revision so it picks up the new version (the
#    revision's secret binding uses `:latest`, but Cloud Run caches the
#    resolved version at revision-creation time — only new revisions pick
#    up the new secret).
gcloud run services update hughes-api --region=europe-west1 --project=tryhughes \
  --update-secrets=OLLAMA_API_KEY=ollama-api-key:latest

# 3. Verify (after warmup completes):
TOKEN=$(gcloud auth print-identity-token)
curl -H "Authorization: Bearer $TOKEN" \
  https://hughes-api-<hash>-ew.a.run.app/api/health
```

The old version stays in Secret Manager history; revert with `--update-secrets=OLLAMA_API_KEY=ollama-api-key:N` where N is the old version number (find via `gcloud secrets versions list ollama-api-key`).

### Re-bootstrap data after a schema change

```bash
bash infra/bootstrap.sh
```

The script is idempotent. New migrations apply in numeric order; existing rows are not wiped (seed is content-cached). For a full reset, drop all tables manually first via the Cloud SQL Auth Proxy.

### Add a new runtime env var

```bash
# Non-secret value:
gcloud run services update hughes-api --region=europe-west1 --project=tryhughes \
  --update-env-vars=NEW_VAR=value

# Secret value:
printf '%s' "$VALUE" | gcloud secrets create my-secret --project=tryhughes \
  --replication-policy=automatic --data-file=-
gcloud secrets add-iam-policy-binding my-secret --project=tryhughes \
  --member="serviceAccount:hughes-api-sa@tryhughes.iam.gserviceaccount.com" \
  --role=roles/secretmanager.secretAccessor
gcloud run services update hughes-api --region=europe-west1 --project=tryhughes \
  --update-secrets=MY_SECRET=my-secret:latest
```

### Check current monthly cost

- **GCP (Cloud SQL + Cloud Run + Artifact Registry):** Cloud Console → Billing → Reports, filter by project=`tryhughes`. Or:

  ```bash
  open "https://console.cloud.google.com/billing/01E474-EA1515-FA74B1/reports?project=tryhughes"
  ```

- **Ollama Cloud (LLM):** the Ollama Cloud dashboard's Billing/Usage page. Compare against the spend cap set in section 6.

- **Estimated baseline (idle / low traffic):** ~$25-35/mo for Cloud SQL db-f1-micro + Cloud Run min-instances=1 + Artifact Registry storage. LLM is on top of that.

### Inspect the Cloud SQL DB directly

```bash
# Start the Auth Proxy in one terminal:
~/.cache/hughes-ai/cloud-sql-proxy tryhughes:europe-west1:hughes-pg --port=5433

# In another terminal, get a connection URL and use psql/psycopg/whatever:
MIGRATE_URL=$(gcloud secrets versions access latest --secret=database-url-migrate --project=tryhughes)
# Replace host=/cloudsql/... with localhost:5433 for TCP.
```

## Decisions log

See `infra/decisions/` for the per-issue plans and the chronological `AUTONOMOUS_RUN_LOG.md`.
