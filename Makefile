.PHONY: up down dev migrate seed lint lint-fix typecheck test audit eval deep-eval openui-prompt update-sse-goldens verify-prod-role

# HUG-231: regenerate the SSE event-contract goldens. Run when the
# expected SSE event sequence intentionally changes (new event added,
# rename, re-order). Review the diff before committing.
update-sse-goldens:
	UPDATE_SSE_GOLDENS=1 uv run pytest packages/api/tests/test_sse_contract.py -v

# HUG-232: regenerate JSON schema snapshots in
# packages/frontend/src/shared/api/schemas/ from `api.types.*` Pydantic
# models. Run when you change a Pydantic model and want the schema
# to match. CI runs the same script with --check to catch drift.
types:
	uv run python scripts/generate_type_schemas.py

up:
	docker compose up -d

down:
	docker compose down

dev: up
	@echo "Dev servers not yet implemented (HUG-31, HUG-33)"

# Apply every migrations/*.sql file in numeric order against the local
# Postgres container. Idempotent — each file uses IF NOT EXISTS / IF
# EXISTS guards. Run after `make up` on a fresh DB or whenever a new
# migration lands.
migrate:
	@for f in migrations/*.sql; do \
		echo "→ $$f"; \
		docker cp "$$f" hughes-ai-postgres-1:/tmp/migration.sql && \
		docker exec hughes-ai-postgres-1 psql -U cubidev -d cubi -f /tmp/migration.sql; \
	done

seed:
	uv run python scripts/seed.py --profile small_cu

dbt-build:
	cd packages/dbt-models && uv run dbt build --select staging marts --profiles-dir .

dbt-test:
	cd packages/dbt-models && uv run dbt test --select staging marts --profiles-dir .

# HUG-166: hard-gate audit. Cross-system reconciliation, logical
# invariants, regulatory closure, statistical bands.
# Run after `make seed && make dbt-build`.
audit:
	cd packages/dbt-models && uv run dbt test --profiles-dir .
	uv run pytest tests/audit/ -v
	uv run python scripts/audit_data_model.py

lint:
	uv run ruff check .
	uv run bandit -c pyproject.toml -r packages/
	uv run semgrep --config .semgrep/ --error packages/

lint-fix:
	uv run ruff check --fix .

typecheck:
	uv run mypy packages/synth-data packages/nl-engine packages/api --strict

test:
	pytest

# HUG-193: Surface 1 was retired, so `make eval` runs the LangGraph agent
# against every question in questions.yaml (no path subset, no two-path
# legacy/agent comparison). The old `--full` flag is gone — there is no
# subset to skip.
eval:
	python scripts/eval.py

# HUG-248: deep-research eval harness — runs the 14 rubric questions
# at tests/deep_research/questions.yaml through the lead-agent path
# (RESEARCH_LEAD_AGENT_ENABLED=1) and scores each answer with an
# LLM-as-judge against the rubric. Use --dry-run to validate harness
# wiring without LLM calls.
deep-eval:
	python scripts/deep_eval.py

# HUG-178 Phase B: regenerate the OpenUI agent system prompt artifact.
# Re-run after bumping @openuidev/react-ui or @openuidev/lang-core.
# Direct node invocation (skips pnpm headers that bleed into stdout).
openui-prompt:
	cd packages/frontend && node scripts/generate-openui-prompt.mjs \
		> ../nl-engine/src/nl_engine/agent/openui_prompt.txt

# Bug 5 (2026-05-17): comprehensive end-to-end deep-query test.
# Drives the live API + frontend through Playwright, asserts SSE
# events, DB rows, structlog, and Prometheus all line up on a real
# deep starter question. Needs the API process up at :8000 with a
# real LLM key + a warm MetricFlow catalog (first call pays 3-4 min).
e2e-deep:
	cd packages/frontend && RUN_DEEP_E2E=1 npx playwright test deep-query-full-stack.spec.ts --reporter=list

# HUG-257: starts the Cloud SQL Auth Proxy and runs pytest
# infra/tests/test_runtime_role.py, which asserts the cubi_runtime role's
# privilege model (read-only on lending, INSERT/UPDATE on app-state, no
# DELETE anywhere). Requires gcloud authenticated and the proxy installed
# at ~/.cache/hughes-ai/cloud-sql-proxy (auto-installed by bootstrap.sh).
verify-prod-role:
	@PROXY=$$HOME/.cache/hughes-ai/cloud-sql-proxy; \
	if [ ! -x "$$PROXY" ]; then echo "Run infra/bootstrap.sh first (it installs the proxy)."; exit 1; fi; \
	TOKEN=$$(gcloud auth print-access-token 2>/dev/null); \
	if [ -z "$$TOKEN" ]; then echo "gcloud has no active credential. Run 'gcloud auth login'."; exit 1; fi; \
	$$PROXY tryhughes:europe-west1:hughes-pg --port=5433 --token="$$TOKEN" > /tmp/proxy.log 2>&1 & \
	PID=$$!; trap "kill $$PID 2>/dev/null" EXIT INT TERM; \
	for i in $$(seq 1 30); do (echo > /dev/tcp/localhost/5433) 2>/dev/null && break; sleep 1; done; \
	uv run pytest infra/tests/test_runtime_role.py -v
