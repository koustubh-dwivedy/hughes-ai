"""Every Python module under `packages/*/src/**` must import cleanly (HUG-233).

A circular import or a syntax error in a module not exercised by any
test currently surfaces only when someone happens to use the module.
This gate walks every source file and tries to import its parent
package. Failures get collected and reported together so a single CI
run lists every broken module at once.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_PACKAGES = _REPO / "packages"

# Skip generated / vendored / artifact paths.
_SKIP_DIR_NAMES = {
    "__pycache__",
    ".venv",
    "node_modules",
    "compiled",   # packages/nl-engine/src/nl_engine/agent/prompts/compiled
    "target",     # packages/dbt-models/target
    "dbt_packages",
    "logs",
    "build",
    "dist",
}


def _iter_modules() -> list[str]:
    """Yield dotted module names rooted at each package's `src/<pkg>`."""
    mods: list[str] = []
    for src in _PACKAGES.glob("*/src"):
        for path in src.rglob("*.py"):
            if any(part in _SKIP_DIR_NAMES for part in path.parts):
                continue
            rel = path.relative_to(src).with_suffix("")
            # __init__.py is covered when we import its parent package.
            if rel.name == "__init__":
                rel = rel.parent
            if str(rel) in {".", ""}:
                continue
            mods.append(".".join(rel.parts))
    return sorted(set(mods))


@pytest.mark.parametrize("modname", _iter_modules())
def test_module_imports_cleanly(modname: str) -> None:
    # Make every package's src/ importable for the duration of the test
    # session. We add all of them at module-load time so paramatrize sees
    # discoverable modules.
    for src in _PACKAGES.glob("*/src"):
        if str(src) not in sys.path:
            sys.path.insert(0, str(src))
    try:
        importlib.import_module(modname)
    except Exception as exc:  # noqa: BLE001 — surface ANY import failure
        pytest.fail(f"`import {modname}` failed: {type(exc).__name__}: {exc}")
