"""HTTP routes for the conversational `/threads` surface (HUG-177)."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from api.logging import get_logger
from api.repo import threads as threads_repo
from api.services.lead_agent import stream_lead_turn
from api.services.llm import make_agent_llm
from api.services.title_generator import generate_title
from api.types.threads_api import (
    CreateThreadRequest,
    CreateThreadResponse,
    GetThreadResponse,
    ListThreadsResponse,
    PostMessageRequest,
)

router = APIRouter()

# Cap how long the SSE stream waits for the title task after the agent
# finishes. If the title is genuinely slow, we don't want to hold the
# socket open forever — the row is still in the DB on the next list
# refetch, just not delivered as a real-time event this turn.
_TITLE_EMIT_TIMEOUT_SEC = 60.0


async def _generate_and_persist_title(
    thread_id: UUID, user_content: str, llm: Any, db_url: str
) -> str | None:
    """Generate a title via the LLM and persist it. Returns the title on
    a successful write, or `None` if the LLM/DB call failed or the
    thread already had a title (idempotent guard in
    `update_thread_title`).

    Emits `thread_title.start`, `thread_title.generated`, and
    `thread_title.background_failed` with millisecond timings so the
    cost of the LLM call and the DB UPDATE can be separated."""
    slog = get_logger().bind(
        component="api.routes.threads", thread_id=str(thread_id)
    )
    slog.info("thread_title.start", user_content_len=len(user_content))
    loop = asyncio.get_event_loop()
    started = loop.time()
    try:
        llm_started = loop.time()
        title = await asyncio.to_thread(generate_title, user_content, llm)
        llm_elapsed_ms = int((loop.time() - llm_started) * 1000)
        db_started = loop.time()
        wrote = await asyncio.to_thread(
            threads_repo.update_thread_title, thread_id, title, db_url
        )
        db_elapsed_ms = int((loop.time() - db_started) * 1000)
        slog.info(
            "thread_title.generated",
            title=title,
            wrote=wrote,
            llm_elapsed_ms=llm_elapsed_ms,
            db_elapsed_ms=db_elapsed_ms,
            total_elapsed_ms=int((loop.time() - started) * 1000),
        )
        return title if wrote else None
    except Exception as exc:  # noqa: BLE001 — best-effort title; never fail the request
        slog.warning(
            "thread_title.background_failed",
            error_type=type(exc).__name__,
            error=str(exc)[:200],
            elapsed_ms=int((loop.time() - started) * 1000),
        )
        return None


async def _await_title_with_telemetry(
    title_task: asyncio.Task[str | None],
    slog: Any,
    inner_elapsed_ms: int,
) -> str | None:
    try:
        return await asyncio.wait_for(
            asyncio.shield(title_task), timeout=_TITLE_EMIT_TIMEOUT_SEC
        )
    except TimeoutError:
        slog.warning(
            "thread_title.wait_timeout",
            timeout_sec=_TITLE_EMIT_TIMEOUT_SEC,
            inner_elapsed_ms=inner_elapsed_ms,
        )
        return None


def _wrap_stream_with_title_hook(
    inner: AsyncIterator[dict[str, Any]],
    thread_id: UUID,
    user_content: str,
    llm: Any,
    db_url: str,
) -> AsyncIterator[dict[str, Any]]:
    """Yield from `inner`, then emit a `title` SSE event the moment the
    background title task lands. The title task starts immediately (in
    parallel with the agent) so the title is usually ready by the time
    the agent's last step streams. If the client disconnects mid-stream
    the title task is shielded so the DB row still gets written."""

    slog = get_logger().bind(
        component="api.routes.threads", thread_id=str(thread_id)
    )

    async def _gen() -> AsyncIterator[dict[str, Any]]:
        title_task = asyncio.create_task(
            _generate_and_persist_title(thread_id, user_content, llm, db_url)
        )
        slog.info("thread_title.wrapper_started")
        loop = asyncio.get_event_loop()
        inner_started = loop.time()
        try:
            async for ev in inner:
                yield ev
            inner_done = loop.time()
            title = await _await_title_with_telemetry(
                title_task, slog, int((inner_done - inner_started) * 1000)
            )
            if title:
                yield {
                    "event": "title",
                    "data": json.dumps(
                        {"thread_id": str(thread_id), "title": title}
                    ),
                }
                slog.info(
                    "thread_title.emitted",
                    title=title,
                    wait_after_inner_ms=int((loop.time() - inner_done) * 1000),
                )
            else:
                reason = "task_returned_none" if title_task.done() else "timeout"
                slog.info("thread_title.not_emitted", reason=reason)
        finally:
            if not title_task.done():
                slog.info("thread_title.detached_on_client_disconnect")

    return _gen()


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
    # HUG-247 Phase B: the autonomous lead-agent path is the only path.
    # The legacy coordinator.route_turn dispatch has been removed; the
    # RESEARCH_LEAD_AGENT_ENABLED flag is no longer consulted.
    stream = stream_lead_turn(
        thread_id=thread_id,
        user_content=body.content,
        db_url=db_url,
        llm=llm,
        history=history,
        request_id=request_id,
    )
    # Schedule a fire-and-forget LLM-generated sidebar title on the
    # first user/assistant exchange. `update_thread_title` is
    # conditional on `title IS NULL`, so re-fires are no-ops.
    if thread.title is None:
        stream = _wrap_stream_with_title_hook(
            stream, thread_id, body.content, llm, db_url
        )
    return EventSourceResponse(stream)


def _get_llm(request: Request) -> Any:
    """Allow tests to inject a fake by attaching `agent_llm` to app.state."""
    override = getattr(request.app.state, "agent_llm", None)
    if override is not None:
        return override
    return make_agent_llm()
