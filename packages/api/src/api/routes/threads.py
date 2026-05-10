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


def _session_id(x_hughes_session: str | None) -> str:
    if not x_hughes_session:
        raise HTTPException(
            status_code=400, detail="X-Hughes-Session header is required"
        )
    return x_hughes_session


def _user_id(
    x_hughes_user: str | None, x_hughes_session: str | None
) -> str:
    """HUG-205: thread ownership uses the durable user_id from the
    frontend's localStorage. During the rollout window we accept the
    session_id as a fallback so older clients still work; once the
    rollout completes we tighten this to require X-Hughes-User."""
    if x_hughes_user:
        return x_hughes_user
    return _session_id(x_hughes_session)


@router.post("/threads", response_model=CreateThreadResponse)
def create_thread(
    body: CreateThreadRequest,
    request: Request,
    x_hughes_session: str | None = Header(default=None),
    x_hughes_user: str | None = Header(default=None),
) -> CreateThreadResponse:
    sid = _session_id(x_hughes_session)
    uid = _user_id(x_hughes_user, x_hughes_session)
    thread = threads_repo.create_thread(
        session_id=sid,
        user_id=uid,
        db_url=request.app.state.db_url,
        title=body.title,
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
    x_hughes_session: str | None = Header(default=None),
    x_hughes_user: str | None = Header(default=None),
) -> ListThreadsResponse:
    uid = _user_id(x_hughes_user, x_hughes_session)
    summaries = threads_repo.list_threads_for_user(
        uid, request.app.state.db_url, limit=limit
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
