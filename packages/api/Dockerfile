# Hughes AI API — Cloud Run image.
# Build context is the REPO ROOT (the workspace needs all three members).
#   docker build -f packages/api/Dockerfile -t hughes-api:<tag> .

# ---------- stage 1: builder ----------
FROM python:3.12-slim AS builder

# Pin uv to the local-dev version so the resolver is identical to laptops/CI.
RUN pip install --no-cache-dir uv==0.11.7

WORKDIR /app

# Workspace + lockfile first so dep-only changes hit the cache.
COPY pyproject.toml uv.lock ./
COPY packages/api/pyproject.toml packages/api/pyproject.toml
COPY packages/nl-engine/pyproject.toml packages/nl-engine/pyproject.toml
COPY packages/synth-data/pyproject.toml packages/synth-data/pyproject.toml

# Source for each workspace member. `uv sync` installs them editable
# (pyproject specifies hatchling.build with `packages = ["src/..."]`),
# so the absolute path /app/packages/*/src must match in the runtime
# stage too — see the COPY --from=builder lines below.
COPY packages/api/src packages/api/src
COPY packages/nl-engine/src packages/nl-engine/src
COPY packages/synth-data/src packages/synth-data/src

# --no-dev drops ruff/mypy/pytest/etc.
# --group runtime-extras pulls in dbt-postgres + dbt-metricflow so the
# `mf` CLI is on PATH at runtime — required by api.main:lifespan, which
# invokes it via subprocess through nl_engine.repo.metricflow.
RUN uv sync --frozen --no-dev --group runtime-extras

# ---------- stage 2: runtime ----------
FROM python:3.12-slim AS runtime

# libpq5: psycopg native bindings against Postgres.
# ca-certificates: TLS to https://ollama.com (LLM provider).
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Non-root user for Cloud Run hardening.
RUN groupadd --system --gid 1000 hughes \
    && useradd --system --uid 1000 --gid hughes --home /app --shell /usr/sbin/nologin hughes

WORKDIR /app

# Resolved venv + workspace source. Paths kept identical to the builder
# stage so the editable .pth entries in the venv stay valid.
COPY --from=builder --chown=hughes:hughes /app/.venv ./.venv
COPY --from=builder --chown=hughes:hughes /app/packages/api ./packages/api
COPY --from=builder --chown=hughes:hughes /app/packages/nl-engine ./packages/nl-engine
COPY --from=builder --chown=hughes:hughes /app/packages/synth-data ./packages/synth-data

# Runtime data assets read by the agent:
#   config/llm.yaml          — LLM provider selector (nl_engine.llm.factory)
#   packages/dbt-models/     — dbt project the `mf` subprocess reads
COPY --chown=hughes:hughes config ./config
COPY --chown=hughes:hughes packages/dbt-models ./packages/dbt-models

USER hughes

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8080

# Direct exec form so uvicorn is PID 1 and Cloud Run's SIGTERM lands on it.
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"]
