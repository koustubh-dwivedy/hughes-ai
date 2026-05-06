"""GET /history, GET /history/{id}.

The `POST /history/{id}/rerun` endpoint was tied to Surface 1's `AskResponse`
shape and was removed alongside the Surface 1 retirement (HUG-193). The
frontend never called it; legacy SQL re-execution is now a manual step
via the agent surface or a SQL client.
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from api.repo.history import get_history, get_history_by_id

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
