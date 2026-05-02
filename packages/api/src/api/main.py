"""FastAPI application entry point."""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from nl_engine.context_loader import load_all

from api.middleware.request_id import RequestIDMiddleware
from api.routes import ask, dashboards, health, history, log, metrics_route, trust

# Source the repo-root .env so a plain `uvicorn api.main:app` finds
# DATABASE_URL, CEREBRAS_API_KEY, etc. without the caller having to
# pre-source them. Path: packages/api/src/api/main.py → 4 levels up.
load_dotenv(Path(__file__).resolve().parents[4] / ".env")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    app.state.ctx = load_all()
    app.state.db_url = os.environ["DATABASE_URL"]
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(RequestIDMiddleware)
app.include_router(ask.router)
app.include_router(dashboards.router)
app.include_router(health.router)
app.include_router(history.router)
app.include_router(log.router)
app.include_router(metrics_route.router)
app.include_router(trust.router)
