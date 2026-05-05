"""Drift gate for the committed OpenUI agent system prompt artifact
(HUG-178 Phase B).

Re-runs `packages/frontend/scripts/generate-openui-prompt.mjs` and
compares the result against the committed
`packages/nl-engine/src/nl_engine/agent/openui_prompt.txt`. Fails if
they differ — meaning the OpenUI npm dep was bumped without
re-running `make openui-prompt`.

Skipped (not failed) when `node` isn't on PATH or the frontend's
`node_modules` hasn't been installed locally — that lets contributors
who only touch the Python backend run the structural suite without
needing a frontend toolchain.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GENERATOR = (
    REPO_ROOT / "packages" / "frontend" / "scripts" / "generate-openui-prompt.mjs"
)
COMMITTED_PROMPT = (
    REPO_ROOT
    / "packages"
    / "nl-engine"
    / "src"
    / "nl_engine"
    / "agent"
    / "openui_prompt.txt"
)
FRONTEND_NODE_MODULES = REPO_ROOT / "packages" / "frontend" / "node_modules"


def test_committed_prompt_matches_regeneration() -> None:
    if shutil.which("node") is None:
        pytest.skip("node not on PATH — drift check requires Node")
    if not FRONTEND_NODE_MODULES.exists():
        pytest.skip("frontend node_modules missing — run `pnpm install` first")
    if not GENERATOR.exists():
        pytest.fail(f"generator script missing: {GENERATOR}")
    if not COMMITTED_PROMPT.exists():
        pytest.fail(f"committed prompt artifact missing: {COMMITTED_PROMPT}")

    node_bin = shutil.which("node") or "node"
    proc = subprocess.run(  # noqa: S603 — fixed-path Node invocation
        [node_bin, str(GENERATOR)],
        capture_output=True,
        text=True,
        timeout=15.0,
        check=False,
    )
    assert proc.returncode == 0, f"generator failed: {proc.stderr}"
    fresh = proc.stdout
    committed = COMMITTED_PROMPT.read_text(encoding="utf-8")
    assert fresh == committed, (
        "Committed openui_prompt.txt is stale. "
        "Re-run `make openui-prompt` and commit the result."
    )
