# CLAUDE.md — Hughes AI

This file is the table of contents for the repo. All detailed documentation lives in `docs/`.

## What this repo is

Hughes AI is a lending analytics demo for one synthetic credit union. Users ask open-ended NL questions about loan originations, approvals, delinquency, and portfolio performance. Answers are grounded, explainable, and backed by synthetic Origence LOS + Jack Henry Symitar data.

**Demo-first. Production-grade engineering. Same repo scales to a real product.**

## Repo map

| Path | What it is |
|---|---|
| `packages/synth-data/` | Deterministic synthetic data generators (Origence + Symitar + reconciliation bridge) |
| `packages/nl-engine/` | Context layer + NL→SQL pipeline + Gemma 4 (Google AI Studio) integration |
| `packages/nl-engine/context/` | YAML grounding files: schema_context, metrics, rules, examples |
| `packages/api/` | FastAPI backend: /ask, /history, /trust, /dashboards/* |
| `packages/frontend/` | React + Vite + TypeScript single-page app |
| `packages/frontend/src/dashboards/` | Dashboard page modules (ExecutiveSummary, DepositPortfolio, PastDue, OfficerBranch, Chat) |
| `packages/dbt-models/` | dbt: staging → core → lending metrics marts |
| `docs/requirements.md` | Full product requirements |
| `docs/metrics.md` | All lending metric definitions with formulas and caveats |
| `docs/dashboards.md` | Dashboard panel reference — routes, endpoints, backing marts |
| `docs/decisions/` | Decision log (ADR-style) |
| `scripts/` | seed.py, eval.py, bootstrap.sh |

## Module layer architecture

Dependencies flow FORWARD only. Enforced by structural tests.

```
types → config → repo → service → runtime → ui
```

Crossing layers is a CI failure, not a convention.

## Invariants (mechanically enforced)

- No `print()` in Python — use `structlog` (ruff error)
- No `console.log()` in TypeScript — use `pino` (biome error)
- No f-string SQL — use parameterized queries (Semgrep)
- Max 300 lines per file (structural test)
- All SQL execution is read-only at the DB role level
- Every query produces an audit log entry

## Dev commands

```bash
make dev        # docker-compose up (Postgres, Redis, Vector + Victoria observability)
make migrate    # apply every migrations/*.sql file in numeric order against local Postgres (idempotent)
make seed       # generate + load synthetic data (deterministic; cache invalidates when profile
                #   YAML or any generator source file changes — see scripts/seed.py _SRC_FILES)
make lint       # ruff + mypy + biome + semgrep
make test       # pytest unit + integration
make eval       # NL accuracy benchmark (20-question subset by default)
make eval-full  # full 50+ question benchmark
```

## Synth data profile (small_cu)

| Dimension | Value |
|---|---|
| Members | 3,000 |
| Deposit accounts | 8,000 |
| History span | 26 months |
| Watchlist share | 4% of active loans |
| Deterministic seed | 42 |

## CI gates (all blocking)

Lint → typecheck → unit → structural → security → doc-validation → integration → nl-eval → build

## Key files to read first

1. `docs/requirements.md` — product spec
2. `docs/metrics.md` — metric definitions (grounding layer depends on this)
3. `packages/nl-engine/context/` — the four YAML grounding files
4. `packages/synth-data/config/` — synthetic data configuration
