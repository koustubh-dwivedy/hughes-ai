"""Request / response models for the /threads HTTP surface (HUG-177).

Kept separate from `types/threads.py` (which holds the persistence
shapes) so the wire contract evolves independently from the row layout
in `thread_messages`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from api.types.openui import OpenUIDslPayload
from api.types.threads import ThreadMessage, ThreadSummary


class CreateThreadRequest(BaseModel):
    title: str | None = None


class CreateThreadResponse(BaseModel):
    thread_id: UUID
    title: str | None
    started_at: datetime


class PostMessageRequest(BaseModel):
    content: str
    parent_message_id: UUID | None = None


class GetThreadResponse(BaseModel):
    thread_id: UUID
    title: str | None
    started_at: datetime
    last_active_at: datetime
    messages: list[ThreadMessage]


class ListThreadsResponse(BaseModel):
    threads: list[ThreadSummary] = Field(default_factory=list)


class StreamStep(BaseModel):
    """Intermediate SSE event: a single agent step or tool result."""

    step: int
    kind: str  # "tool_call" | "tool_result" | "thinking"
    name: str | None = None
    args: dict[str, Any] | None = None
    result: dict[str, Any] | None = None


class StreamFinal(BaseModel):
    """Terminal SSE event carrying the persisted assistant message and,
    when the agent emitted OpenUI Lang DSL, the validated payload (HUG-178
    Phase B). `openui` is None when the agent's `final_answer` did not
    populate `openui_dsl`."""

    message: ThreadMessage
    openui: OpenUIDslPayload | None = None


class StreamToken(BaseModel):
    """SSE event carrying a content delta for the assistant's
    streaming summary (HUG-202 Phase 2). The frontend appends each
    delta to the in-flight answer bubble's text. The full canonical
    summary lands in the subsequent `final` event when the turn ends."""

    content_delta: str


class StreamThinking(BaseModel):
    """SSE event carrying a single narration line for the Thinking box
    (HUG-202). The box shows ONE line at a time — each new event REPLACES
    the previous line rather than appending. The full ordered history is
    preserved server-side as the `thinking_trace` and surfaced in the
    References modal once the turn completes."""

    step: int
    line: str


class StreamError(BaseModel):
    """SSE event emitted when the agent runner's graph stream crashes
    (HUG-190 Phase C). Frontend renders this as a user-visible error
    instead of leaving the stream silently incomplete."""

    message: str
