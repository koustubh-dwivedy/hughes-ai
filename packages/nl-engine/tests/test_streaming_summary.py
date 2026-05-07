"""HUG-202 Phase 2: partial-JSON extraction of `final_answer.summary`
from a streaming buffer. Token deltas have to keep flowing as the LLM
types — this is the regex/decoder driving that."""

from __future__ import annotations

from langchain_core.messages import AIMessageChunk
from nl_engine.agent import streaming as streaming_mod
from nl_engine.agent.streaming_summary import (
    extract_partial_summary,
    make_summary_streamer,
)


def _emit_record(rid: str) -> tuple[list[str], object]:
    """Register a sink that records every emitted delta. Returns the
    list and the request_id so the caller can clean up if needed."""
    captured: list[str] = []
    streaming_mod.set_token_sink(rid, captured.append)
    return captured, rid


def test_partial_summary_returns_none_before_summary_key_arrives() -> None:
    assert extract_partial_summary("{") is None
    assert extract_partial_summary('{"openui_dsl"') is None


def test_partial_summary_decodes_escaped_chars() -> None:
    buf = '{"summary": "Loan-to-deposit ratio is 13.48\\n(strong).'
    text = extract_partial_summary(buf)
    assert text == "Loan-to-deposit ratio is 13.48\n(strong)."


def test_partial_summary_handles_dangling_backslash() -> None:
    # Mid-escape sequence — drop the trailing backslash and recover
    # the prefix without raising.
    buf = '{"summary": "Hello \\'
    assert extract_partial_summary(buf) == "Hello "


def test_partial_summary_stops_at_unescaped_closing_quote() -> None:
    buf = '{"summary": "Hi", "rows": []}'
    assert extract_partial_summary(buf) == "Hi"


def test_summary_streamer_emits_growing_deltas_in_order() -> None:
    captured, rid = _emit_record("test-stream-1")
    on_chunk = make_summary_streamer(rid)
    # Incremental tool_call_chunks for `final_answer`. The first
    # carries the name; subsequent ones carry args only.
    chunks_args = [
        '{"summary": "',
        "Hello",
        " world",
        '"',
        ', "rows": []}',
    ]
    on_chunk(
        AIMessageChunk(
            content="",
            tool_call_chunks=[
                {"name": "final_answer", "args": chunks_args[0], "id": "c", "index": 0}
            ],
        )
    )
    for piece in chunks_args[1:]:
        on_chunk(
            AIMessageChunk(
                content="",
                tool_call_chunks=[
                    {"name": None, "args": piece, "id": "c", "index": 0}
                ],
            )
        )
    streaming_mod.clear_token_sink(rid)
    assert captured == ["Hello", " world"]


def test_summary_streamer_resets_when_a_different_tool_starts() -> None:
    captured, rid = _emit_record("test-stream-2")
    on_chunk = make_summary_streamer(rid)
    on_chunk(
        AIMessageChunk(
            content="",
            tool_call_chunks=[
                {"name": "list_metrics", "args": "{}", "id": "x", "index": 0}
            ],
        )
    )
    # No emit yet — list_metrics resets the buffer.
    on_chunk(
        AIMessageChunk(
            content="",
            tool_call_chunks=[
                {
                    "name": "final_answer",
                    "args": '{"summary": "ok"',
                    "id": "y",
                    "index": 0,
                }
            ],
        )
    )
    streaming_mod.clear_token_sink(rid)
    assert captured == ["ok"]


def test_emit_token_with_unregistered_request_id_is_a_noop() -> None:
    streaming_mod.emit_token("never-registered", "x")  # must not raise


def test_emit_token_swallows_sink_exceptions() -> None:
    rid = "test-stream-bad-sink"

    def boom(_delta: str) -> None:
        raise RuntimeError("boom")

    streaming_mod.set_token_sink(rid, boom)
    streaming_mod.emit_token(rid, "hello")  # must not raise
    streaming_mod.clear_token_sink(rid)
