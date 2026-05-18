"""HUG-266 — reload-resume endpoints for in-flight agent turns.

Two reads. Both are owned by `routes/turns.py` (not `routes/threads.py`)
so the latter stays under the 300-line structural cap.

- `GET /threads/{tid}/turn-status` — SPA mount probe. Returns
  `{"status":"idle"}` when no turn is running, otherwise the turn_id +
  last_seq_no the SPA needs to call `/tail` with.
- `GET /threads/{tid}/tail` — SSE reconnect. Returns an SSE stream
  that tails `thread_messages` for the currently-running turn from
  `from_seq` onwards. 404 if no turn is in flight.

Both reuse the ownership check from `routes/threads._user_id` and the
SSE producer from `services/tail_turn`.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from api.repo import threads as threads_repo
from api.repo import turn_state as turn_state_repo
from api.routes.threads import _user_id
from api.services.tail_turn import tail_turn

router = APIRouter()


def _authorize(
    thread_id: UUID,
    request: Request,
    x_hughes_user: str | None,
    x_hughes_session: str | None,
) -> str:
    db_url: str = request.app.state.db_url
    thread = threads_repo.get_thread(thread_id, db_url)
    if thread is None:
        raise HTTPException(status_code=404, detail="thread not found")
    if thread.user_id != _user_id(x_hughes_user, x_hughes_session):
        raise HTTPException(status_code=403, detail="not your thread")
    return db_url


@router.get("/threads/{thread_id}/turn-status")
def get_turn_status(
    thread_id: UUID,
    request: Request,
    x_hughes_session: str | None = Header(default=None),
    x_hughes_user: str | None = Header(default=None),
) -> dict[str, Any]:
    db_url = _authorize(thread_id, request, x_hughes_user, x_hughes_session)
    state = turn_state_repo.get_running_for_thread(thread_id, db_url)
    if state is None:
        return {"status": "idle"}
    return {
        "status": state.status,
        "turn_id": str(state.turn_id),
        "last_seq_no": state.last_seq_no,
        "started_at": state.started_at.isoformat(),
    }


@router.get("/threads/{thread_id}/tail")
def tail_running_turn(
    thread_id: UUID,
    request: Request,
    from_seq: int = 0,
    x_hughes_session: str | None = Header(default=None),
    x_hughes_user: str | None = Header(default=None),
) -> Any:
    db_url = _authorize(thread_id, request, x_hughes_user, x_hughes_session)
    state = turn_state_repo.get_running_for_thread(thread_id, db_url)
    if state is None:
        raise HTTPException(status_code=404, detail="no running turn")
    return EventSourceResponse(
        tail_turn(
            thread_id=thread_id,
            turn_id=state.turn_id,
            from_seq=from_seq,
            db_url=db_url,
        )
    )
