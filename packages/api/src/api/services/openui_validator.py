"""Server-side OpenUI Lang DSL validator (HUG-178 Phase B).

Wraps a Node subprocess that imports `@openuidev/react-lang`'s
`createParser` and parses the LLM-emitted DSL against the standard
`openuiLibrary`. Soft-skips on every failure mode (Node missing,
subprocess crash, timeout, JSON parse error) — the OpenUI parser on
the frontend is permissive and the renderer has its own error
boundary, so unverified DSL still flows to the browser.

The Node script lives at
`packages/frontend/scripts/validate-openui-dsl.mjs` so it can resolve
its npm deps from the frontend's `node_modules`.
"""

from __future__ import annotations

import json
import shutil
import subprocess  # nosec B404 — Node validator is the documented integration path
from datetime import UTC, datetime
from pathlib import Path

import structlog

from api.types.openui import OpenUIDslPayload, OpenUIValidationError

log = structlog.stdlib.get_logger()

_REPO_ROOT = Path(__file__).resolve().parents[5]
_VALIDATOR_SCRIPT = (
    _REPO_ROOT / "packages" / "frontend" / "scripts" / "validate-openui-dsl.mjs"
)
_TIMEOUT_SECONDS = 5.0


def _validator_script_exists() -> bool:
    """Indirection so unit tests can stub it; the real path may not exist
    in containerized test envs that don't ship the frontend bundle."""
    return _VALIDATOR_SCRIPT.exists()


def _soft_skip(dsl: str, reason: str, **fields: object) -> OpenUIDslPayload:
    log.warning("openui_validator_soft_skip", reason=reason, **fields)
    return OpenUIDslPayload(
        dsl_text=dsl,
        validated=False,
        validation_errors=[],
        validated_at=None,
    )


def _run_validator(dsl: str) -> subprocess.CompletedProcess[str] | OpenUIDslPayload:
    """Spawn the Node validator. Returns the completed process on success
    or a soft-skip payload on any subprocess-level failure mode."""
    node_bin = shutil.which("node")
    if node_bin is None:
        return _soft_skip(dsl, "node_not_on_path")
    if not _validator_script_exists():
        return _soft_skip(dsl, "validator_script_missing", path=str(_VALIDATOR_SCRIPT))
    try:
        return subprocess.run(  # noqa: S603  # nosec B603 — node path resolved via shutil.which, DSL on stdin
            [node_bin, str(_VALIDATOR_SCRIPT)],
            input=dsl,
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return _soft_skip(dsl, "validator_timeout", timeout_s=_TIMEOUT_SECONDS)
    except OSError as exc:
        return _soft_skip(dsl, "validator_oserror", error=str(exc))


def _build_payload(dsl: str, parsed: dict[str, object]) -> OpenUIDslPayload:
    """Convert the validator's `{valid, errors}` JSON into an
    `OpenUIDslPayload`. Synthesizes a `no_root` error when the parser
    reports `valid:false` without surfacing structured errors so
    `is_renderable` remains correct."""
    raw_errors = parsed.get("errors")
    error_list = raw_errors if isinstance(raw_errors, list) else []
    errors = [
        OpenUIValidationError(
            code=str(e.get("code", "unknown")),
            message=str(e.get("message", "")),
        )
        for e in error_list
        if isinstance(e, dict)
    ]
    if not parsed.get("valid", False) and not errors:
        errors.append(
            OpenUIValidationError(
                code="no_root",
                message="DSL did not produce a renderable root element",
            )
        )
    return OpenUIDslPayload(
        dsl_text=dsl,
        validated=True,
        validation_errors=errors,
        validated_at=datetime.now(UTC),
    )


def validate_openui_dsl(dsl: str) -> OpenUIDslPayload:
    """Validate an OpenUI Lang DSL string via the Node subprocess.

    Returns an `OpenUIDslPayload` with `validated=True` on a successful
    parse (parser-level errors land in `validation_errors`). On any
    failure mode (Node missing, script absent, timeout, non-zero exit
    with no usable stdout, JSON parse error), returns `validated=False`
    with an empty error list and a structlog warning.
    """
    proc_or_skip = _run_validator(dsl)
    if isinstance(proc_or_skip, OpenUIDslPayload):
        return proc_or_skip
    proc = proc_or_skip
    stdout = proc.stdout.strip()
    if not stdout:
        return _soft_skip(
            dsl, "validator_no_stdout", returncode=proc.returncode, stderr=proc.stderr
        )
    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError as exc:
        return _soft_skip(dsl, "validator_bad_json", error=str(exc), stdout=stdout)
    if not isinstance(parsed, dict):
        return _soft_skip(dsl, "validator_unexpected_shape", payload=parsed)
    return _build_payload(dsl, parsed)
