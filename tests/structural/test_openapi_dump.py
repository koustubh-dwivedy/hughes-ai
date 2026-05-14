"""FastAPI app must produce a valid, non-empty OpenAPI spec (HUG-233).

An accidentally-removed endpoint (e.g. a router pulled but not re-wired)
shrinks the OpenAPI surface silently. This gate asserts the spec is
well-formed and non-empty.
"""

from __future__ import annotations

import json
from pathlib import Path


def test_openapi_spec_well_formed_and_non_empty(tmp_path: Path) -> None:
    from api.main import app

    spec = app.openapi()

    assert isinstance(spec, dict), "openapi() must return a dict"
    assert spec.get("openapi", "").startswith("3."), (
        f"OpenAPI version not 3.x: {spec.get('openapi')!r}"
    )
    assert spec.get("paths"), "OpenAPI spec has no paths"
    assert len(spec["paths"]) >= 8, (
        f"OpenAPI exposes only {len(spec['paths'])} paths — expected ≥ 8 "
        "(thread routes + dashboard routes + data-model + trust + health)"
    )

    # Dump to tmp_path so a future task can attach this as a CI artifact.
    (tmp_path / "openapi.json").write_text(json.dumps(spec, indent=2))
