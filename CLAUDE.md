# CLAUDE.md — Hughes AI

This file is the table of contents for the repo. All detailed documentation lives in `docs/`.

## What this repo is

Hughes AI is a lending analytics demo for one synthetic credit union. Users ask open-ended NL questions about loan originations, approvals, delinquency, and portfolio performance. Answers are grounded, explainable, and backed by synthetic Origence LOS + Jack Henry Symitar data.

**Demo-first. Production-grade engineering. Same repo scales to a real product.**

## Repo map

| Path | What it is |
|---|---|
| `packages/synth-data/` | Deterministic synthetic data generators (Origence + Symitar + reconciliation bridge) |
| `packages/nl-engine/` | LangGraph agent (Surface 2) + MetricFlow integration + eval harness |
| `packages/nl-engine/src/nl_engine/agent/` | Agent graph, tools, prompts (`system_prompt.py` + `openui_prompt.txt`) |
| `packages/nl-engine/src/nl_engine/agent/prompts/` | DSPy modules + compiled artifacts (HUG-181) |
| `packages/api/` | FastAPI backend: /threads, /history, /trust, /data-model/*, /dashboards/* |
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

## LLM provider configuration

Single source of truth: `config/llm.yaml`. The agent runs **one LLM** at a time (HUG-190 amendment, 2026-05-07) — no per-call fallback, no provider mixing. To swap providers in production, edit the YAML + supply the matching API key.

```yaml
# config/llm.yaml
provider: openai_compatible   # one of: groq | google | ollama | openai_compatible
model: zai-glm-4.7            # provider-specific identifier
api_key_env: CEREBRAS_API_KEY # name of env var holding the bearer token
base_url_env: CEREBRAS_BASE_URL  # optional; defaults to provider's default
```

`nl_engine.llm.make_llm()` reads the YAML; both the agent (`api/services/llm.py`) and the eval harness (`run_eval.py`) call it. Env vars `LLM_PROVIDER` / `LLM_MODEL` remain as test-only overrides when the YAML is absent.

| Provider | Default model | Required env var |
|---|---|---|
| `groq` | `qwen/qwen3-32b` (ADR-0004 invariants enforced) | `GROQ_API_KEY` |
| `google` | `gemma-4-31b-it` | `GOOGLE_API_KEY` |
| `ollama` | `qwen3-coder:480b` (Ollama Cloud) | `OLLAMA_API_KEY`, optional `OLLAMA_BASE_URL` |
| `openai_compatible` (HUG-206) | none — model required in YAML | env var named by `api_key_env`, optional `base_url_env` |

`openai_compatible` is the generic provider for any endpoint that speaks the OpenAI HTTP wire protocol — Cerebras, Together, Fireworks, Anyscale, vLLM, OpenAI itself. Adding a new such endpoint is a config-file change, not a code change. Examples:

```yaml
# Cerebras / GLM 4.7
provider: openai_compatible
model: zai-glm-4.7
api_key_env: CEREBRAS_API_KEY
base_url_env: CEREBRAS_BASE_URL  # https://api.cerebras.ai/v1

# Fireworks / Llama 70B
provider: openai_compatible
model: accounts/fireworks/models/llama-v3p1-70b-instruct
api_key_env: FIREWORKS_API_KEY
base_url_env: FIREWORKS_BASE_URL  # https://api.fireworks.ai/inference/v1
```

See `docs/decisions/0004-llm-switch-qwen3-32b-groq.md` (Amendments 2026-05-07, 2026-05-10) for the single-LLM rationale and provider-onboarding constraints.

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
2. `docs/metrics.md` — metric definitions (the user-facing reference)
3. `packages/dbt-models/models/semantic/` — MetricFlow semantic models (the canonical metric catalog after HUG-193)
4. `packages/nl-engine/src/nl_engine/agent/system_prompt.py` — agent's tool-calling rules (ANCHOR-A through ANCHOR-E)
5. `packages/synth-data/config/` — synthetic data configuration
