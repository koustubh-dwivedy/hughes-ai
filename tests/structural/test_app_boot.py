"""FastAPI app must boot with all expected router prefixes wired (HUG-233).

A new router not wired in `api/main.py` is silently invisible until
the first request to its path. This gate imports the app and asserts
the known route prefixes are present.

Lifespan (catalog warmup) does NOT run on plain `import api.main` —
only when an ASGI server runs the app. So no env-var dance needed.
"""

from __future__ import annotations


def test_app_imports_and_has_expected_route_prefixes() -> None:
    from api.main import app

    paths = {getattr(r, "path", "") for r in app.routes}

    # Each assertion identifies the router whose absence would be a
    # silent main.py wiring bug. Add a line here when a new router
    # lands in HUG-212+ (research approve/abort, etc.).
    assert "/health" in paths, "health router not included in main.py"
    assert any(p.startswith("/threads") for p in paths), "threads router missing"
    assert any(p.startswith("/dashboards") for p in paths), "dashboards router missing"
    assert any(p.startswith("/data-model") for p in paths), "data-model router missing"
    assert any(p.startswith("/history") for p in paths), "history router missing"
    assert any(p.startswith("/trust") for p in paths), "trust router missing"
