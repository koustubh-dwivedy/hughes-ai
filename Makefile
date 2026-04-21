.PHONY: up down dev seed lint lint-fix typecheck test eval eval-full

up:
	docker compose up -d

down:
	docker compose down

dev: up
	@echo "Dev servers not yet implemented (HUG-31, HUG-33)"

seed:
	python scripts/seed.py

lint:
	uv run ruff check .

lint-fix:
	uv run ruff check --fix .

typecheck:
	uv run mypy packages/synth-data packages/nl-engine packages/api

test:
	pytest

eval:
	python scripts/eval.py

eval-full:
	python scripts/eval.py --full
