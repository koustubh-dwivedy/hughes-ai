# Hughes AI

Lending analytics demo for a synthetic credit union. Ask open-ended natural language questions about loan originations, approvals, delinquency, and portfolio performance — get grounded, explainable answers backed by synthetic Origence LOS and Jack Henry Symitar data.

Built to demo-quality first, scale to production second. Same repo, no replatforming.

## What it does

- **Ask anything** about lending: origination volume, approval rates, funding rates, delinquency, channel mix, product mix
- **Grounded answers** backed by defined metrics, source-of-truth rules, and visible assumptions
- **Reconciliation bridge** linking LOS applications/fundings to booked core loans
- **Query history** so you can revisit, rerun, and learn from prior analyses
- **Trust / data view** showing freshness, source coverage, and reconciliation quality

## Four surfaces only

| Surface | What it shows |
|---|---|
| Ask / Chat | Open-ended NL question input |
| Result | Answer, chart/table, metric definition, lineage, caveats, freshness |
| History | Past queries — revisit, rerun |
| Trust | Data freshness, reconciliation quality, source coverage |

## Data

Synthetic only — no real member data. Deterministic generation from a YAML-configured seed so CI and evals are fully reproducible.

| Source | Synthetic data |
|---|---|
| Origence Connect LOS | Applications, stages, approvals, channels, fundings, product types |
| Jack Henry Symitar | Booked loans, balances, payments, delinquency snapshots, branches |

## Engineering

Production-grade discipline from commit zero:

- Strict module boundaries (Types → Config → Repo → Service → Runtime → UI)
- mypy strict + ruff + biome, all enforced as errors in CI
- Structural tests blocking on import violations and file size limits
- OpenTelemetry traces + Prometheus metrics + Vector-based dev observability stack
- 50+ NL eval benchmark with 85% accuracy gate in CI
- Every query has an audit trail and visible lineage

## Local dev

```bash
# Prerequisites: Python 3.12, Node 20, Docker

make dev        # start Postgres + Redis + observability stack
make seed       # generate and load synthetic data
make lint       # ruff + mypy + biome
make test       # unit + integration tests
make eval       # run NL accuracy benchmark
```

## Repo structure

```
hughes-ai/
├── CLAUDE.md                   # repo map, invariants, dev commands
├── docs/
│   ├── requirements.md         # full product spec
│   ├── metrics.md              # lending metric definitions
│   └── decisions/              # ADR-style decision log
├── packages/
│   ├── synth-data/             # deterministic synthetic data generators
│   ├── nl-engine/              # context layer + NL→SQL + Claude API
│   │   └── context/            # schema_context.yaml, metrics.yaml, rules.yaml, examples.yaml
│   ├── api/                    # FastAPI backend (/ask, /history, /trust)
│   ├── frontend/               # React + Vite + TypeScript
│   └── dbt-models/             # staging → core → lending metrics
└── scripts/                    # seed, eval, bootstrap
```
