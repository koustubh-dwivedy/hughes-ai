"""GET /history, GET /history/{id}, POST /history/{id}/rerun."""

import uuid
from datetime import datetime
from typing import cast

from fastapi import APIRouter, HTTPException, Request
from nl_engine.engine import AnswerResponse
from nl_engine.executor import execute_sql
from pydantic import BaseModel

from api.repo.history import get_history, get_history_by_id, save_query
from api.routes.ask import AskResponse

router = APIRouter(prefix="/history")


class HistorySummary(BaseModel):
    id: uuid.UUID
    question: str
    sql: str
    created_at: datetime
    kind: str = "ask"


class HistoryDetail(HistorySummary):
    answer_json: dict[str, object] = {}
    assumptions: list[str] = []
    caveats: list[str] = []
    lineage_json: dict[str, object] = {}
    token_usage: dict[str, object] = {}


def _str_list(val: object) -> list[str]:
    return [str(v) for v in val] if isinstance(val, list) else []


@router.get("", response_model=list[HistorySummary])
async def list_history(
    request: Request, limit: int = 20, kind: str | None = None
) -> list[dict[str, object]]:
    if kind is not None and kind not in {"ask", "dashboard_audit"}:
        raise HTTPException(
            status_code=400,
            detail="kind must be 'ask' or 'dashboard_audit'",
        )
    return get_history(limit, request.app.state.db_url, kind=kind)


@router.get("/{record_id}", response_model=HistoryDetail)
async def get_history_record(
    record_id: uuid.UUID, request: Request
) -> dict[str, object]:
    record = get_history_by_id(record_id, request.app.state.db_url)
    if record is None:
        raise HTTPException(status_code=404, detail="Not found")
    return record


@router.post("/{record_id}/rerun", response_model=AskResponse)
async def rerun_query(
    record_id: uuid.UUID, request: Request
) -> AskResponse:
    rid: str = request.state.request_id
    record = get_history_by_id(record_id, request.app.state.db_url)
    if record is None:
        raise HTTPException(status_code=404, detail="Not found")
    sql = str(record["sql"])
    question = str(record["question"])
    answer_json = cast(
        dict[str, object], record.get("answer_json") or {}
    )
    lineage_json = cast(
        dict[str, object], record.get("lineage_json") or {}
    )
    rows, columns = execute_sql(sql, request.app.state.db_url)
    result = AnswerResponse(
        sql=sql,
        explanation=str(answer_json.get("explanation", "")),
        tables_used=_str_list(lineage_json.get("tables_used", [])),
        assumptions=_str_list(record.get("assumptions") or []),
        caveats=_str_list(record.get("caveats") or []),
        rows=rows,
        columns=columns,
    )
    save_query(question, result, rid, request.app.state.db_url)
    return AskResponse(
        request_id=rid,
        question=question,
        sql=result.sql,
        explanation=result.explanation,
        tables_used=result.tables_used,
        assumptions=result.assumptions,
        caveats=result.caveats,
        rows=result.rows,
        columns=result.columns,
    )
