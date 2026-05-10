"""Pydantic models for the threads / thread_messages persistence layer (HUG-175)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

MessageRole = Literal["user", "assistant", "tool", "system"]


class Thread(BaseModel):
    thread_id: UUID
    session_id: str
    # HUG-205 — durable identity that owns this thread, stored in the
    # frontend's localStorage. Persists across tab close / browser
    # restart, unlike `session_id` which is per-visit. Optional during
    # the rollout window because backfilled rows from before the
    # migration may inherit `session_id` here.
    user_id: str | None = None
    title: str | None = None
    started_at: datetime
    last_active_at: datetime
    ended_at: datetime | None = None
    slots: dict[str, Any] = Field(default_factory=dict)


class ThreadMessage(BaseModel):
    message_id: UUID
    thread_id: UUID
    parent_message_id: UUID | None = None
    role: MessageRole
    content: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    tool_results: list[dict[str, Any]] | None = None
    openui_dsl: str | None = None
    mf_query: dict[str, Any] | None = None
    rows: list[dict[str, Any]] | None = None
    # HUG-202 Phase 3 — chronological agent trace for the References
    # modal. Each entry: {kind, label, at, ...kind-specific fields}.
    # None for non-final-answer messages.
    thinking_trace: list[dict[str, Any]] | None = None
    created_at: datetime


class ThreadSummary(BaseModel):
    """Compact thread view returned by GET /threads."""

    thread_id: UUID
    title: str | None
    started_at: datetime
    last_active_at: datetime
