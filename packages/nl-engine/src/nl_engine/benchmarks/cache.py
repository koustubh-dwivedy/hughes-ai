"""Cache layer for the eval runner — namespaced by path (legacy / agent).

Single JSON file under benchmarks/.cache/responses.json with key prefixes
disambiguating legacy and agent results. Load / save are simple JSON I/O;
serialize / deserialize convert between the per-path result types and the
on-disk dict shape.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from nl_engine.agent.eval_runner import AgentEvalResult
from nl_engine.engine import AnswerResponse, ClarificationResponse


def cache_key(question: str, db_url: str, path: str) -> str:
    """Stable cache key per (question, db_url, path)."""
    return hashlib.sha256(f"{path}|{question}|{db_url}".encode()).hexdigest()


def load_cache(cache_file: Path) -> dict[str, dict[str, object]]:
    if cache_file.exists():
        raw: dict[str, dict[str, object]] = json.loads(cache_file.read_text())
        return raw
    return {}


def save_cache(cache_file: Path, cache: dict[str, dict[str, object]]) -> None:
    cache_file.parent.mkdir(exist_ok=True)
    cache_file.write_text(json.dumps(cache, indent=2))


# ── Legacy (Surface 1) ──────────────────────────────────────────────────────


def serialize_legacy(
    result: AnswerResponse | ClarificationResponse,
) -> dict[str, object]:
    if isinstance(result, AnswerResponse):
        return {
            "type": "answer",
            "sql": result.sql,
            "tables_used": result.tables_used,
            "rows": result.rows,
            "columns": result.columns,
        }
    return {"type": "clarification", "question": result.question}


def deserialize_legacy(
    data: dict[str, object],
) -> AnswerResponse | ClarificationResponse:
    if data.get("type") != "answer":
        return ClarificationResponse(question=str(data.get("question", "")))
    tables_raw = data.get("tables_used")
    tables = (
        [str(t) for t in tables_raw] if isinstance(tables_raw, list) else []
    )
    rows_raw = data.get("rows")
    rows = (
        [dict(r) for r in rows_raw if isinstance(r, dict)]
        if isinstance(rows_raw, list)
        else []
    )
    cols_raw = data.get("columns")
    columns = [str(c) for c in cols_raw] if isinstance(cols_raw, list) else []
    return AnswerResponse(
        sql=str(data.get("sql") or ""),
        tables_used=tables,
        explanation="",
        assumptions=[],
        caveats=[],
        rows=rows,
        columns=columns,
    )


# ── Agent (Surface 2) ───────────────────────────────────────────────────────


def serialize_agent(result: AgentEvalResult) -> dict[str, object]:
    return {
        "rows": result.rows,
        "columns": result.columns,
        "summary": result.summary,
        "tool_call_trace": result.tool_call_trace,
        "step_count": result.step_count,
        "elapsed_seconds": result.elapsed_seconds,
        "final_message_kind": result.final_message_kind,
    }


def deserialize_agent(data: dict[str, object]) -> AgentEvalResult:
    rows_raw = data.get("rows")
    rows = (
        [dict(r) for r in rows_raw if isinstance(r, dict)]
        if isinstance(rows_raw, list)
        else []
    )
    cols_raw = data.get("columns")
    columns = [str(c) for c in cols_raw] if isinstance(cols_raw, list) else []
    trace_raw = data.get("tool_call_trace")
    trace: list[dict[str, Any]] = (
        [dict(t) for t in trace_raw if isinstance(t, dict)]
        if isinstance(trace_raw, list)
        else []
    )
    sc_raw = data.get("step_count")
    el_raw = data.get("elapsed_seconds")
    return AgentEvalResult(
        rows=rows,
        columns=columns,
        summary=str(data.get("summary") or ""),
        tool_call_trace=trace,
        step_count=int(sc_raw) if isinstance(sc_raw, (int, float)) else 0,
        elapsed_seconds=float(el_raw) if isinstance(el_raw, (int, float)) else 0.0,
        final_message_kind=str(data.get("final_message_kind") or "unknown"),
    )
