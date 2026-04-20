# Hughes AI — Product Requirements

**One-line summary:** A tiny, polished, synthetic-data lending analytics demo with open-ended NL analysis, query history, trust visibility, agent-observable development telemetry, and production-grade engineering discipline from day one.

## Product

Hughes AI is a barebones but production-quality lending analytics demo for one synthetic credit union. It uses synthetic Origence Connect LOS data and synthetic Jack Henry Symitar data to answer open-ended natural-language lending questions with grounded, explainable outputs. The MVP is intentionally small in scope, but the repo, data model, evals, observability, and interfaces are designed so the same codebase can scale into a real product later.

## Users

Primary users are the CEO, CLO, CFO, Head of Lending, and Analyst at a credit union. The goal is to let them self-serve lending analysis instead of relying on manual reporting.

## Data scope (lending domain only)

**Origence Connect LOS (synthetic):**
- applications
- stages
- approvals / declines
- channels
- funding events
- product type

**Jack Henry Symitar (synthetic):**
- booked loans
- balances
- payments
- delinquency snapshots
- branch
- product context

A critical capability is linking and reconciling LOS applications/fundings to booked core loans. That bridge is central to the product's credibility.

## Product surface (4 views only)

1. **Ask / Chat** — open-ended natural language lending questions
2. **Result view** — answer, chart/table, drill-downs, metric definition, lineage, caveats, freshness
3. **Query history** — revisit, rerun, and learn from prior analyses
4. **Trust / data view** — freshness, source coverage, reconciliation quality, known caveats

No mobile app, no alerts, no scheduled reporting, no customer onboarding flows, no compliance workflows in v1.

## Analysis core

Answers grounded in layered business context:
- **Context layer:** four YAML files (schema_context, metrics, rules, examples) loaded at startup
- **ContextSelector:** keyword-based routing picks relevant tables + metrics per question
- **Allowlist grounding:** LLM selects from allowlisted table/metric names before generating SQL
- **Self-check:** intermediate row count inspection before finalizing answer
- **Caveats:** surfaced from metrics.yaml in every answer
- **Clarification:** one sharp clarifying question when question is ambiguous

## Engineering non-negotiables

- Clear repo structure with strict module boundaries
- Typed interfaces (mypy strict, Pydantic)
- Module layer order enforced by structural tests: Types → Config → Repo → Service → Runtime → UI
- Tests and CI gates (all blocking)
- Structured logging (structlog + pino, JSON)
- OpenTelemetry traces and Prometheus metrics
- Audit trail for every query (append-only)
- Documented metric definitions (YAML)
- Deterministic synthetic data generation (reproducible seed)
- Evaluation harness (85% NL accuracy gate in CI)
- Read-only analytics execution (DB-level role + runtime sqlglot AST validation)
- Visible lineage and caveats in every answer
- Custom lint errors include remediation instructions (agent-readable)
- docs/ as system of record; CLAUDE.md as table of contents

## Development telemetry

Agent-accessible dev observability stack: Vector fan-out → Victoria Logs (LogQL) + Victoria Metrics (PromQL) + Victoria Traces (TraceQL). Ephemeral per task. Follows OpenAI harness engineering principle: agent can inspect runtime behavior during development.

## Success bar

- Works end to end on synthetic data
- Users can ask broad lending questions in natural language
- Answers are usually correct, fast, and explainable
- Query history works
- Freshness and reconciliation quality are visible
- Dev telemetry is available during development
- Repo is ready to evolve into a full product without replatforming
