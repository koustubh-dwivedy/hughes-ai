"""POST /ask — NL→SQL pipeline endpoint."""

from fastapi import APIRouter, Request
from nl_engine.engine import ClarificationResponse
from nl_engine.engine import ask as engine_ask
from pydantic import BaseModel

from api.repo.history import save_query

router = APIRouter()


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    request_id: str
    question: str
    sql: str | None = None
    explanation: str | None = None
    tables_used: list[str] = []
    assumptions: list[str] = []
    caveats: list[str] = []
    rows: list[dict[str, object]] = []
    columns: list[str] = []
    clarification: str | None = None


@router.post("/ask", response_model=AskResponse)
async def ask_endpoint(body: AskRequest, request: Request) -> AskResponse:
    rid: str = request.state.request_id
    result = engine_ask(
        body.question, request.app.state.db_url, request.app.state.ctx
    )
    if isinstance(result, ClarificationResponse):
        return AskResponse(
            request_id=rid,
            question=body.question,
            clarification=result.question,
        )
    save_query(body.question, result, rid, request.app.state.db_url)
    return AskResponse(
        request_id=rid,
        question=body.question,
        sql=result.sql,
        explanation=result.explanation,
        tables_used=result.tables_used,
        assumptions=result.assumptions,
        caveats=result.caveats,
        rows=result.rows,
        columns=result.columns,
    )
