"""FastAPI application entry point."""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from nl_engine.context_loader import load_all

from api.middleware.request_id import RequestIDMiddleware
from api.routes import ask, health, history, metrics_route, trust


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    app.state.ctx = load_all()
    app.state.db_url = os.environ["DATABASE_URL"]
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(RequestIDMiddleware)
app.include_router(ask.router)
app.include_router(health.router)
app.include_router(history.router)
app.include_router(metrics_route.router)
app.include_router(trust.router)
