"""Generate JSON Schema snapshots from every Pydantic model in
`api/types/*` (HUG-232).

Why snapshots instead of inline TS generation:
  - JSON Schema is canonical; TS generators differ in convention
    (camel-case, optional handling, type-vs-interface) and would lock
    us into one tool.
  - The frontend keeps hand-written TS in
    `packages/frontend/src/features/intelligence/research/types.ts`
    etc. — humans curate naming + ergonomics on the TS side.
  - CI's gate is: "schemas are current". When a Pydantic model
    changes (HUG-209 adds a field), the schema diff fails CI with
    the EXACT change. The frontend dev sees what to update on the
    TS side at the same time.

Output: `packages/frontend/src/shared/api/schemas/{module}.json`,
one file per `api/types/*.py`. Deterministic (sorted keys, 2-space
indent) so the diff is clean.

Usage:
    python scripts/generate_type_schemas.py            # write
    python scripts/generate_type_schemas.py --check    # diff
"""

from __future__ import annotations

import argparse
import importlib
import inspect
import json
import sys
from pathlib import Path

from pydantic import BaseModel

_REPO = Path(__file__).resolve().parents[1]
_TYPES_DIR = _REPO / "packages" / "api" / "src" / "api" / "types"
_SCHEMAS_DIR = (
    _REPO / "packages" / "frontend" / "src" / "shared" / "api" / "schemas"
)

# Make api.* importable.
sys.path.insert(0, str(_REPO / "packages" / "api" / "src"))


def _iter_modules() -> list[str]:
    out: list[str] = []
    for path in sorted(_TYPES_DIR.glob("*.py")):
        if path.name == "__init__.py":
            continue
        out.append(f"api.types.{path.stem}")
    return out


def _models_in_module(modname: str) -> list[type[BaseModel]]:
    """Return every BaseModel subclass DEFINED in the given module
    (not just imported)."""
    mod = importlib.import_module(modname)
    out: list[type[BaseModel]] = []
    for _, obj in inspect.getmembers(mod):
        if (
            inspect.isclass(obj)
            and issubclass(obj, BaseModel)
            and obj is not BaseModel
            and obj.__module__ == modname
        ):
            out.append(obj)
    return sorted(out, key=lambda c: c.__name__)


def _schemas_for_module(modname: str) -> dict[str, dict[str, object]]:
    """Return `{ModelName: model_json_schema, ...}` for the module."""
    return {m.__name__: m.model_json_schema() for m in _models_in_module(modname)}


def _serialize(schemas: dict[str, dict[str, object]]) -> str:
    """Deterministic JSON output — sorted keys, 2-space indent, no
    trailing whitespace."""
    return json.dumps(schemas, sort_keys=True, indent=2) + "\n"


def _generate(write: bool) -> int:
    """Generate schemas. If `write` is True, write to disk; otherwise
    compare to committed files and fail on diff."""
    if write:
        _SCHEMAS_DIR.mkdir(parents=True, exist_ok=True)
    drifted: list[str] = []
    seen: set[Path] = set()
    for modname in _iter_modules():
        schemas = _schemas_for_module(modname)
        if not schemas:
            continue
        short = modname.split(".")[-1]
        out_path = _SCHEMAS_DIR / f"{short}.json"
        seen.add(out_path)
        new = _serialize(schemas)
        if write:
            out_path.write_text(new)
            continue
        existing = out_path.read_text() if out_path.exists() else ""
        if existing != new:
            drifted.append(short)

    # Detect stale files (schema removed in code but file lingers).
    if not write:
        for path in _SCHEMAS_DIR.glob("*.json"):
            if path not in seen:
                drifted.append(f"{path.stem}  (stale; module was removed)")

    if drifted:
        print(
            "❌ JSON Schema drift detected:\n"
            + "\n".join(f"  - {d}" for d in drifted)
            + "\n\nRun `make types` and commit the regenerated "
            "schemas, plus update the corresponding TypeScript types in "
            "packages/frontend/src/features/.../*types.ts. "
            "If you're removing a model, also delete its stale .json."
        )
        return 1

    print(f"✅ {len(seen)} schemas current.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="compare to committed; fail on drift (CI mode)",
    )
    args = parser.parse_args()
    return _generate(write=not args.check)


if __name__ == "__main__":
    sys.exit(main())
