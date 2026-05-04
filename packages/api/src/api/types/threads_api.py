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
    """Terminal SSE event carrying the persisted assistant message."""

    message: ThreadMessage
