"""Producer-thread plumbing for the LangGraph runner (HUG-206 split-out).

The graph is sync; we run it in a dedicated thread so the asyncio
event loop isn't blocked by LLM latency. Crashes inside the producer
are wrapped in a sentinel and placed on the queue so the consumer
can emit a well-formed SSE `event: error` frame instead of silently
breaking the stream (HUG-190 Phase C).

Lives in its own module so `agent_runner.py` fits the 300-line cap.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from nl_engine.agent.state import AgentState

_log = logging.getLogger(__name__)


class _PRODUCER_ERROR_SENTINEL:  # noqa: N801 — internal sentinel
    """Queue marker for graph.stream crashes; consumer emits an SSE
    `event: error` frame so the stream stays well-formed."""

    def __init__(self, message: str) -> None:
        self.message = message


def is_error_sentinel(chunk: Any) -> bool:
    return isinstance(chunk, _PRODUCER_ERROR_SENTINEL)


def make_producer(
    graph: Any, initial: AgentState, queue: asyncio.Queue[Any]
) -> Any:
    """Build the producer thread function. Crashes are converted into
    a sentinel placed on the queue so the consumer can yield an SSE
    error frame instead of silently breaking the stream."""

    def producer() -> None:
        try:
            for chunk in graph.stream(initial, stream_mode="values"):
                queue.put_nowait(chunk)
        except Exception as exc:  # noqa: BLE001 — surfaced as SSE error frame
            _log.warning(
                "agent_runner producer crashed (%s): %s",
                type(exc).__name__,
                str(exc)[:300],
            )
            queue.put_nowait(_PRODUCER_ERROR_SENTINEL(message=str(exc)[:300]))
        finally:
            queue.put_nowait(None)

    return producer
