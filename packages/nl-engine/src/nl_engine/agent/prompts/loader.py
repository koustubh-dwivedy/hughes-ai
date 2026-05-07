"""Runtime loader for compiled DSPy artifacts (HUG-181).

`load_compiled(module_name)` returns the deserialized DSPy module if an
artifact exists at `prompts/compiled/<module_name>.json`; otherwise None
so callers fall back to the hand-written signature.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import dspy

log = logging.getLogger(__name__)

COMPILED_DIR = Path(__file__).parent / "compiled"


def load_compiled(module_name: str) -> Any | None:
    """Load `compiled/<module_name>.json` into a `dspy.Module`.

    Returns None and logs a warning when the artifact is missing or
    fails to deserialize — the caller falls back to the hand-written
    signature so the agent never crashes on a bad/missing artifact.
    """
    path = COMPILED_DIR / f"{module_name}.json"
    if not path.exists():
        log.debug("compiled prompt artifact missing: %s", module_name)
        return None
    try:
        instance = dspy.Predict.load(str(path))
    except Exception as exc:  # noqa: BLE001 — fallback path
        log.warning(
            "compiled prompt artifact %s failed to deserialize: %s — "
            "falling back to hand-written signature",
            module_name,
            exc,
        )
        return None
    return instance
