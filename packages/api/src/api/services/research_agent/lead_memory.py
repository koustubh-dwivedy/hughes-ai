"""Lead's running notes — external plan memory (HUG-220, M1).

Anthropic's lead+subagents pattern uses a markdown doc that survives
context truncation: after every worker batch, the lead reads its
previous note, reads the new findings, writes a new versioned note.
On the next tick the lead reads the latest note again as "what I
know so far". This is the load-bearing primitive that lets a deep
research turn span 10+ worker batches without the context window
exploding.

Today's surface area:
  - `write_note(plan_id, body_md, db_url)` — persists a new version
    via the HUG-203 repo. Truncates body_md at `MAX_NOTE_CHARS` and
    emits `research.lead.note_truncated` when it had to cut. Bumps
    the histogram + emits `research.lead.note_written`.
  - `read_latest_note(plan_id, db_url)` — convenience wrapper around
    the repo's `get_latest_lead_note` that returns the body or "" if
    no note exists yet.

`MAX_NOTE_CHARS=2000` chosen so the note can be re-injected into the
lead's prompt many times without dominating the context. Production
will tune this per provider; today's stub-LLM tests don't care.

Re-plan logic (HUG-221, M2) and the coordinator's batch-callback
wiring are separate concerns; M1 just exposes the primitives.
"""

from __future__ import annotations

from uuid import UUID

from nl_engine.logging import get_logger

from api.prometheus import research_lead_note_chars
from api.repo import research as research_repo
from api.services.research_agent.telemetry import (
    EVENT_LEAD_NOTE_WRITTEN,
    log_event,
)
from api.types.research import LeadNote

_MAX_NOTE_CHARS = 2000
_TRUNCATION_MARK = "\n\n…(note truncated — full text in older versions)"

_slog = get_logger().bind(component="research.lead_memory")


def _maybe_truncate(body_md: str) -> tuple[str, bool]:
    """Return (clipped, was_truncated). Trim from the END (older
    info matters less than the just-written digest at the top)."""
    if len(body_md) <= _MAX_NOTE_CHARS:
        return body_md, False
    keep = _MAX_NOTE_CHARS - len(_TRUNCATION_MARK)
    return body_md[:keep] + _TRUNCATION_MARK, True


def write_note(plan_id: UUID, body_md: str, db_url: str) -> LeadNote:
    """Persist a new lead-note version. Bumps the histogram + emits
    `research.lead.note_written` (+ `.note_truncated` if clip occurred)."""
    body, truncated = _maybe_truncate(body_md)
    note = research_repo.append_lead_note(plan_id, body, db_url)
    research_lead_note_chars.observe(len(body))
    log_event(
        EVENT_LEAD_NOTE_WRITTEN,
        plan_id=str(plan_id),
        note_id=str(note.note_id),
        version=note.version,
        chars=len(body),
        truncated=truncated,
    )
    if truncated:
        _slog.warning(
            "lead_memory.note_truncated",
            plan_id=str(plan_id),
            note_id=str(note.note_id),
            original_chars=len(body_md),
            kept_chars=len(body),
        )
    return note


def read_latest_note(plan_id: UUID, db_url: str) -> str:
    """Return the most recent note's body_md, or "" if no note yet.
    Convenience wrapper so callers don't have to handle None."""
    note = research_repo.get_latest_lead_note(plan_id, db_url)
    return note.body_md if note is not None else ""
