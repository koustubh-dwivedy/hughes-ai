"""Partial-JSON extractor for the streaming `final_answer.summary` arg
(HUG-202 Phase 2).

The agent's `final_answer` tool args land as token-by-token JSON
deltas across many AIMessageChunks. We extract just the `summary`
string value as it grows so the SSE consumer can stream it to the
user — the other fields (openui_dsl, rows, mf_query) arrive whole in
the `final` event and don't need streaming.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any

from langchain_core.messages import AIMessageChunk

from nl_engine.agent.streaming import emit_token

# Match `"summary"  :  "<body>` where <body> may contain backslash-
# escaped chars but no unescaped closing quote. The regex deliberately
# does NOT require a trailing quote — that's what makes it work on a
# partial JSON buffer where the model is still typing.
_SUMMARY_PATTERN = re.compile(r'"summary"\s*:\s*"((?:[^"\\]|\\.)*)')


def _decode_partial(raw: str) -> str:
    """Convert a JSON-escaped fragment into the literal text the user
    will see. `json.loads` happily decodes a wrapped fragment as long
    as escape sequences are well-formed — for partial data we may have
    a dangling backslash, which we strip to keep the decoder happy."""
    fragment = raw[:-1] if raw.endswith("\\") else raw
    try:
        return str(json.loads(f'"{fragment}"'))
    except json.JSONDecodeError:
        return fragment


def extract_partial_summary(buffer: str) -> str | None:
    """Return the (possibly incomplete) summary string from a partial
    `final_answer` args JSON. None when the `summary` key hasn't been
    emitted yet."""
    match = _SUMMARY_PATTERN.search(buffer)
    if match is None:
        return None
    return _decode_partial(match.group(1))


def make_summary_streamer(request_id: str) -> Callable[[Any], None]:
    """Build an `on_chunk` callback the LLM streamer calls per
    AIMessageChunk. The callback accumulates `final_answer` args
    JSON and emits incremental `summary` deltas via `emit_token`.

    Closure state is per-call so a new ReAct step starts fresh.
    """
    args_buffer: list[str] = [""]
    emitted_len: list[int] = [0]

    def on_chunk(chunk: Any) -> None:
        if not isinstance(chunk, AIMessageChunk):
            return
        tcs = getattr(chunk, "tool_call_chunks", None)
        if not tcs:
            return
        for tc in tcs:
            name = tc.get("name")
            # Tool-call name is set on the first chunk; subsequent chunks
            # carry args only. So accept either name == "final_answer"
            # OR name is None (continuation of the current tool call).
            if name not in (None, "final_answer"):
                args_buffer[0] = ""
                emitted_len[0] = 0
                continue
            args_chunk = tc.get("args") or ""
            if not args_chunk:
                continue
            args_buffer[0] += args_chunk
            summary = extract_partial_summary(args_buffer[0])
            if summary is None:
                continue
            if len(summary) > emitted_len[0]:
                delta = summary[emitted_len[0]:]
                emitted_len[0] = len(summary)
                emit_token(request_id, delta)

    return on_chunk
