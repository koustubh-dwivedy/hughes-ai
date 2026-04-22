.PHONY: up down dev seed lint lint-fix typecheck test eval eval-full

up:
	docker compose up -d

down:
	docker compose down

dev: up
	@echo "Dev servers not yet implemented (HUG-31, HUG-33)"

seed:
	uv run python scripts/seed.py --profile small_cu

dbt-build:
	cd packages/dbt-models && uv run dbt build --select staging --profiles-dir .

dbt-test:
	cd packages/dbt-models && uv run dbt test --select staging --profiles-dir .

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
