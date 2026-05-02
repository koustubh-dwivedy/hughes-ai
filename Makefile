.PHONY: up down dev migrate seed lint lint-fix typecheck test eval eval-full

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

eval:
	python scripts/eval.py

eval-full:
	python scripts/eval.py --full
