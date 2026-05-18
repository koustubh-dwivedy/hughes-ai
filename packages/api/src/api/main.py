"""FastAPI application entry point."""

import os
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.logging import get_logger
from api.middleware.request_id import RequestIDMiddleware
from api.routes import (
    dashboards,
    data_model,
    health,
    history,
    log,
    metrics_route,
    research,
    threads,
    trust,
)

# Source the repo-root .env so a plain `uvicorn api.main:app` finds
# DATABASE_URL, GROQ_API_KEY, etc. without the caller having to
# pre-source them. Path: packages/api/src/api/main.py → 4 levels up.
load_dotenv(Path(__file__).resolve().parents[4] / ".env")


def _populate_dbt_env_from_database_url(url: str) -> None:
    """Mirror DATABASE_URL into DBT_HOST/PORT/USER/PASSWORD/DBNAME.

    The agent's `mf query` subprocess (nl_engine.repo.metricflow) uses
    dbt-postgres, which reads its connection params from DBT_* env vars per
    packages/dbt-models/profiles.yml. Without these the subprocess tries
    localhost:5432 — fine locally, fatal on Cloud Run.

    setdefault'd so anyone who set DBT_HOST etc. explicitly (local dev,
    docker-compose) keeps their override.
    """
    from urllib.parse import parse_qs, urlparse  # noqa: PLC0415
    parsed = urlparse(url)
    if parsed.username:
        os.environ.setdefault("DBT_USER", parsed.username)
    if parsed.password:
        os.environ.setdefault("DBT_PASSWORD", parsed.password)
    dbname = parsed.path.lstrip("/") if parsed.path else ""
    if dbname:
        os.environ.setdefault("DBT_DBNAME", dbname)
    qs = parse_qs(parsed.query)
    if "host" in qs:
        # Cloud SQL Unix socket: postgresql://u:p@/db?host=/cloudsql/...
        os.environ.setdefault("DBT_HOST", qs["host"][0])
    elif parsed.hostname:
        os.environ.setdefault("DBT_HOST", parsed.hostname)
    if parsed.port:
        os.environ.setdefault("DBT_PORT", str(parsed.port))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    app.state.db_url = os.environ["DATABASE_URL"]
    _populate_dbt_env_from_database_url(app.state.db_url)
    if os.environ.get("API_WARM_CATALOG", "1") == "1":
        # Warm the MetricFlow catalog so the first user query doesn't
        # pay the ~4-min, 65-subprocess startup tax. The lru_cache on
        # `nl_engine.repo.metricflow.list_metrics()` persists for the
        # worker's lifetime. Tests set `API_WARM_CATALOG=0` to skip.
        from nl_engine.repo import metricflow as mf  # noqa: PLC0415
        slog = get_logger().bind(component="api.lifespan")
        slog.info("catalog_warmup.start")
        t0 = time.perf_counter()
        metrics = mf.list_metrics()
        slog.info(
            "catalog_warmup.done",
            elapsed_sec=round(time.perf_counter() - t0, 2),
            metric_count=len(metrics),
        )
        # HUG-263: pre-warm the `mf query` subprocess path. list_metrics
        # warms `mf list dimensions` but NOT `mf query` — that path's
        # semantic_manifest parse cost was 51 s on cold-start on
        # 2026-05-18, eating 15 % of a worker's 10-step budget. One
        # trivial query amortises that cost into container startup.
        if metrics:
            t1 = time.perf_counter()
            try:
                mf.query(metric=metrics[0].name, limit=1)
                slog.info(
                    "query_warmup.done",
                    elapsed_sec=round(time.perf_counter() - t1, 2),
                    metric=metrics[0].name,
                )
            except Exception as exc:  # noqa: BLE001 — non-fatal
                slog.warning(
                    "query_warmup.failed",
                    error=str(exc),
                    metric=metrics[0].name,
                )
    yield


# HUG-260: SPA at app.tryhughes.com calls the API at api.tryhughes.com
# (Cloud Run domain mapping), so the browser needs CORS to allow
# cross-origin fetches. Allowlist is env-var driven; defaults to prod
# + local-dev.
_CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "API_CORS_ORIGINS",
        "https://app.tryhughes.com,http://localhost:5173",
    ).split(",")
    if o.strip()
]

app = FastAPI(lifespan=lifespan, root_path=os.environ.get("API_ROOT_PATH", ""))
app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Hughes-User", "X-Hughes-Session"],
)
app.add_middleware(RequestIDMiddleware)
app.include_router(dashboards.router)
app.include_router(data_model.router)
app.include_router(health.router)
app.include_router(history.router)
app.include_router(log.router)
app.include_router(metrics_route.router)
app.include_router(research.router)
app.include_router(threads.router)
app.include_router(trust.router)
