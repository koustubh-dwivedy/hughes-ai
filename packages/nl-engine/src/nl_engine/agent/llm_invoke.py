"""Wall-clock timeout + transient-error helpers for the agent's LLM call.

Lifted out of `graph.py` to keep that file under the 300-LOC cap
(HUG-190 Phase C-bis², 2026-05-07). The agent calls
`bound.invoke(messages)` once per ReAct step; this module provides:

* `_invoke_with_wall_timeout(bound, msgs, timeout_s)` — runs the call
  in a worker thread and force-returns a `_LLMWallClockTimeout` if it
  exceeds the budget. Defends against provider-layer hangs that
  bypass the underlying HTTP timeout (observed with langchain-ollama
  against Ollama Cloud — TCP connection stays open, no bytes flow,
  no timeout fires).
* `is_transient_llm_error(exc)` — substring match for the kind of
  error worth retrying on the SAME provider (5xx, network timeout,
  connection reset). Returns False for auth errors, malformed prompts,
  etc., where retrying wouldn't help.
"""

from __future__ import annotations

import threading
from typing import Any

from langchain_core.messages import BaseMessage

# Wall-clock fallback for `bound.invoke()`. Defense-in-depth on top of
# any per-provider HTTP timeout. Override via AGENT_STEP_TIMEOUT_S.
AGENT_STEP_DEFAULT_TIMEOUT_S = 150.0

# Substring markers for LLM errors worth retrying on the same provider.
# Catches Ollama 500s, network timeouts, connection drops, etc. — the
# kind of transient infra failure where retrying the identical request
# usually succeeds. Genuine bugs (auth errors, malformed prompts) keep
# propagating.
TRANSIENT_LLM_MARKERS: tuple[str, ...] = (
    "500 internal",
    "502 bad gateway",
    "503 service unavailable",
    "504 gateway timeout",
    "internal server error",
    "timeout",
    "timed out",
    "connection reset",
    "connection refused",
    "responseerror",
)


class LLMWallClockTimeoutError(TimeoutError):
    """Raised when bound.invoke() exceeds the wall-clock budget. Inherits
    from TimeoutError so `is_transient_llm_error` matches it on the
    'timeout' marker and the retry layer kicks in automatically."""


def is_transient_llm_error(exc: BaseException) -> bool:
    """Return True iff this exception's text contains a transient marker.
    Conservative: when in doubt, treat as non-transient and surface to
    the user via graceful message (don't burn retry budget on errors
    that won't self-heal)."""
    msg = (str(exc) + " " + type(exc).__name__).lower()
    return any(marker in msg for marker in TRANSIENT_LLM_MARKERS)


def invoke_with_wall_timeout(
    bound: Any, msgs: list[BaseMessage], timeout_s: float
) -> Any:
    """Run `bound.invoke(msgs)` with a hard wall-clock timeout.

    If the invoke() exceeds `timeout_s`, raises `LLMWallClockTimeout`
    so the caller's transient-retry logic kicks in. We use a daemon
    `threading.Thread` (not `ThreadPoolExecutor`) deliberately:
    `ThreadPoolExecutor.__exit__` blocks on `shutdown(wait=True)`, which
    would force us to wait for the hung worker thread anyway — defeating
    the whole point of the wall-clock guard. With a daemon thread we
    exit cleanly immediately on timeout; the hung thread eventually
    dies when the underlying socket times out OR when the process exits.
    """
    result_box: dict[str, Any] = {}

    def runner() -> None:
        try:
            result_box["value"] = bound.invoke(msgs)
        except BaseException as exc:  # noqa: BLE001 — surfaced via box
            result_box["error"] = exc

    worker = threading.Thread(
        target=runner, daemon=True, name="agent-step-llm"
    )
    worker.start()
    worker.join(timeout=timeout_s)
    if worker.is_alive():
        raise LLMWallClockTimeoutError(
            f"LLM call exceeded wall-clock budget of {timeout_s}s "
            "(connection still open but no response — provider hang)"
        )
    if "error" in result_box:
        raise result_box["error"]
    return result_box["value"]
