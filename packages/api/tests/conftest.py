"""Shared pytest fixtures for the api package."""

from __future__ import annotations

import os

import pytest


@pytest.fixture(scope="session", autouse=True)
def _disable_catalog_warmup() -> None:
    """Skip the ~4-min MetricFlow catalog warm-up that runs in the
    FastAPI lifespan during normal startup. Without this, every
    `TestClient(app)` in the 92 api tests would spawn 65 `mf`
    subprocess calls. The agent path itself is mocked in tests so
    skipping the warm-up doesn't affect coverage."""
    os.environ.setdefault("API_WARM_CATALOG", "0")
