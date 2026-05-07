"""HTTP routes for the conversational `/threads` surface (HUG-177)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from api.repo import threads as threads_repo
from api.services.agent_runner import stream_user_turn
from api.services.llm import make_agent_llm
from api.types.threads_api import (
    CreateThreadRequest,
    CreateThreadResponse,
    GetThreadResponse,
    ListThreadsResponse,
    PostMessageRequest,
)

router = APIRouter()


def _session_id(x_session_id: str | None) -> str:
    if not x_session_id:
        raise HTTPException(status_code=400, detail="X-Session-Id header is required")
    return x_session_id


@router.post("/threads", response_model=CreateThreadResponse)
def create_thread(
    body: CreateThreadRequest,
    request: Request,
    x_session_id: str | None = Header(default=None),
) -> CreateThreadResponse:
    sid = _session_id(x_session_id)
    thread = threads_repo.create_thread(
        session_id=sid, db_url=request.app.state.db_url, title=body.title
    )
    return CreateThreadResponse(
        thread_id=thread.thread_id,
        title=thread.title,
        started_at=thread.started_at,
    )


@router.get("/threads", response_model=ListThreadsResponse)
def list_threads(
    request: Request,
    limit: int = 20,
    x_session_id: str | None = Header(default=None),
) -> ListThreadsResponse:
    sid = _session_id(x_session_id)
    summaries = threads_repo.list_threads_for_session(
        sid, request.app.state.db_url, limit=limit
    )
    return ListThreadsResponse(threads=summaries)


@router.get("/threads/{thread_id}", response_model=GetThreadResponse)
def get_thread(thread_id: UUID, request: Request) -> GetThreadResponse:
    db_url = request.app.state.db_url
    thread = threads_repo.get_thread(thread_id, db_url)
    if thread is None:
        raise HTTPException(status_code=404, detail="thread not found")
    messages = threads_repo.list_messages(thread_id, db_url)
    return GetThreadResponse(
        thread_id=thread.thread_id,
        title=thread.title,
        started_at=thread.started_at,
        last_active_at=thread.last_active_at,
        messages=messages,
    )


@router.post("/threads/{thread_id}/messages")
async def post_message(
    thread_id: UUID,
    body: PostMessageRequest,
    request: Request,
) -> Any:
    db_url = request.app.state.db_url
    thread = threads_repo.get_thread(thread_id, db_url)
    if thread is None:
        raise HTTPException(status_code=404, detail="thread not found")
    history = threads_repo.latest_n_messages(thread_id, n=20, db_url=db_url)
    llm = _get_llm(request)
    request_id = getattr(request.state, "request_id", "")
    stream = stream_user_turn(
        thread_id=thread_id,
        user_content=body.content,
        db_url=db_url,
        llm=llm,
        history=history,
        request_id=request_id,
    )
    return EventSourceResponse(stream)


def _get_llm(request: Request) -> Any:
    """Allow tests to inject a fake by attaching `agent_llm` to app.state."""
    override = getattr(request.app.state, "agent_llm", None)
    if override is not None:
        return override
    return make_agent_llm()
