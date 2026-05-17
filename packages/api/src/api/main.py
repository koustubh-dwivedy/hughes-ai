"""FastAPI application entry point."""

import os
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI

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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    app.state.db_url = os.environ["DATABASE_URL"]
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
    yield


app = FastAPI(lifespan=lifespan, root_path=os.environ.get("API_ROOT_PATH", ""))
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
