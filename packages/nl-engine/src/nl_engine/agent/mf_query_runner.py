"""MetricFlow query execution + retry + structured-error helpers.

Lifted out of `tools.py` so that file stays under the 300-LOC structural
cap WITHOUT trimming the prompt-bearing tool docstrings (HUG-200's
regression — see ADR-0006). This module is pure code: no @tool
decorators, no LLM-visible docstrings. Only `mf_query` (in tools.py)
calls into it, and the structured tool-result it returns matches the
shape the agent expects.

Three responsibilities:
  * `run_mf_query_with_retry(args)` — single-attempt + transient-only
    retry, with structlog telemetry on every attempt.
  * `mf_error_payload(exc)` — converts a MetricFlow exception into the
    {"error": "...", "hint": "..."} dict the agent sees on the next
    step, including any "did you mean" suggestion the underlying CLI
    surfaced.
  * Internal `_log_mf_run` — emits the `mf_query.run` structured log.

Retry semantics (HUG-190 Phase B): structural errors (column not
found, "did you mean", validation) surface immediately so the agent
can correct on the next LLM call. Transient errors (timeout, subprocess
process error) get one extra retry with a 500ms backoff.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from nl_engine.agent.mf_errors import classify_mf_error, extract_mf_hint
from nl_engine.logging import get_logger

log = logging.getLogger(__name__)
slog = get_logger().bind(component="agent.tools")

# Transient errors get one extra retry; structural errors are surfaced
# to the agent immediately so it can correct on the next LLM call.
_MF_QUERY_TRANSIENT_RETRY_DELAY_S = 0.5


def safe_mf() -> Any:
    """Import MetricFlow lazily so unit tests don't require dbt deps."""
    from nl_engine.repo import metricflow as mf

    return mf


def _mf_query_once(args: Any) -> dict[str, Any]:
    mf = safe_mf()
    result = mf.query(
        metric=args.metric,
        dimensions=args.dimensions or None,
        where=args.where,
        order=args.order,
        limit=args.limit,
    )
    return {
        "metric": result.metric,
        "dimensions": result.dimensions,
        "rows": result.rows,
    }


def _log_mf_run(
    args: Any, result: dict[str, Any], t0: float, attempt: int
) -> None:
    slog.info(
        "mf_query.run",
        metric=args.metric,
        dimensions=list(args.dimensions),
        where=args.where,
        order=args.order,
        limit=args.limit,
        row_count=len(result.get("rows", [])),
        elapsed_ms=int((time.monotonic() - t0) * 1000),
        attempt=attempt,
    )


def run_mf_query_with_retry(args: Any) -> dict[str, Any]:
    """Smart retry: surface structural errors immediately; retry only
    transient errors once with a small backoff (HUG-190 Phase B)."""
    t0 = time.monotonic()
    try:
        result = _mf_query_once(args)
        _log_mf_run(args, result, t0, attempt=1)
        return result
    except Exception as exc:  # noqa: BLE001 — surfaced as tool-result
        kind = classify_mf_error(exc)
        slog.warning(
            "mf_query.attempt_failed",
            metric=args.metric, attempt=1, kind=kind, error=str(exc)[:300],
        )
        log.warning("mf_query attempt 1 failed (%s): %s", kind, exc)
        if kind != "transient":
            return mf_error_payload(exc)
    time.sleep(_MF_QUERY_TRANSIENT_RETRY_DELAY_S)
    try:
        result = _mf_query_once(args)
        _log_mf_run(args, result, t0, attempt=2)
        return result
    except Exception as retry_exc:  # noqa: BLE001 — surfaced as tool-result
        slog.warning(
            "mf_query.attempt_failed",
            metric=args.metric, attempt=2,
            kind="transient_retry_failed", error=str(retry_exc)[:300],
        )
        log.warning("mf_query attempt 2 failed (transient retry): %s", retry_exc)
        return mf_error_payload(retry_exc)


def mf_error_payload(exc: Exception) -> dict[str, Any]:
    """Return a structured tool-result so the agent sees the error +
    any 'did you mean' hint MetricFlow surfaced. The graph's tool
    executor wraps tool returns in a ToolMessage; the agent reads this
    on the next step."""
    msg = str(exc)
    hint = extract_mf_hint(msg)
    payload: dict[str, Any] = {"error": msg}
    if hint:
        payload["hint"] = hint
    return payload
