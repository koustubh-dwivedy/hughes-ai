# E2E Tests — Startup Contract

Playwright tests require the full stack to be running. Tests will fast-fail with
clear instructions if the API is unreachable.

## Startup sequence

```bash
# 1. Docker services (Postgres, Redis, Vector + observability)
make dev

# 2. Synthetic data — run once, or after schema changes
make seed

# 3. API server
cd packages/api
uvicorn api.main:app --reload
# listening on http://localhost:8000

# 4. (CI only) Vite dev server — started automatically by Playwright webServer config
#    Locally: if you already have `pnpm dev` running on :5173, it will be reused

# 5. Run E2E tests
cd packages/frontend
npx pnpm@10.33.0 test:e2e

# Interactive UI mode (local only)
npx pnpm@10.33.0 test:e2e:ui
```

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `API_URL` | `http://localhost:8000` | Override API base URL in global-setup health check |
| `CI` | unset | When set: starts fresh Vite server, enables GitHub reporter, 1 retry |

## Playwright config highlights

- **testDir**: `./tests/e2e`
- **baseURL**: `http://localhost:5173`
- **Browser**: Chromium only (avoids cross-browser flake for a demo product)
- **Parallelism**: disabled — tests share one API server
- **Traces**: captured on first retry
- **Screenshots**: captured on failure

## Adding tests

Place new test files in `tests/e2e/` with the `.spec.ts` extension.
Use `page.goto("/")` — baseURL is pre-configured.
