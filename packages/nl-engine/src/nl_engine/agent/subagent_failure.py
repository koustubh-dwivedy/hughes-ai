"""Classify why a worker subagent did not produce `final_answer` (HUG-261).

The lead receives `error_kind` in failed `run_subagent` payloads and uses
it to choose between reformulating the prompt (`structural_step_cap`) and
re-dispatching identically up to once (`transient_worker_exception`).

Kept in its own module so `subagent_tool.py` stays under the 300-line cap.
"""

from __future__ import annotations

from langchain_core.messages import AIMessage, BaseMessage

ERROR_KIND_STRUCTURAL_STEP_CAP = "structural_step_cap"
ERROR_KIND_TRANSIENT_WORKER_EXCEPTION = "transient_worker_exception"
ERROR_KIND_UNKNOWN = "unknown"

# Substring distinguishing the step-cap AIMessage (emitted by
# graph._step_cap_node) from other terminal AIMessages. Stable across
# cap values because the prefix is independent of the {cap} interpolation.
_STEP_CAP_MARKER = "couldn't reach an answer within the"


def classify_no_final_answer(messages: list[BaseMessage]) -> str:
    """Inspect the worker's final AIMessage. If it matches the step-cap
    message, the worker exhausted its budget. Otherwise the LLM ended
    without a terminal tool call for some other reason; we surface that
    as `unknown` so the lead defaults to structural handling (no retry).
    """
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            content = msg.content if isinstance(msg.content, str) else ""
            if _STEP_CAP_MARKER in content:
                return ERROR_KIND_STRUCTURAL_STEP_CAP
            return ERROR_KIND_UNKNOWN
    return ERROR_KIND_UNKNOWN
