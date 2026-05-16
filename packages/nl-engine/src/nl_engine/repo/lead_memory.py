"""Lead-agent external memory primitive: keyed scratchpad backed by
`research_lead_notes` (HUG-241).

The lead writes notes via `write_lead_note(plan_id, key, body)` between
subagent dispatches and reads them back via `read_lead_note_by_key`.
Each `(plan_id, key)` keeps its own version chain — successive writes
append a new row at version + 1, and reads return the latest body for
that key. The migration's `(plan_id, key, version)` unique constraint
prevents race-window collisions.

Bodies > `MAX_NOTE_CHARS` are truncated to the cap to prevent runaway
LLM-generated payloads from blowing out the column. The caller (the
`write_memory` tool) emits a `research.lead.note_written` event with
`truncated=true` when this happens.

This module is the nl-engine-side helper. The api layer has parallel
helpers in `api.repo.research` for serving GET endpoints; they share
the same DB but live in separate packages per the import-graph rules
(`nl_engine` may not import from `api`).
"""

from __future__ import annotations

from typing import NamedTuple
from uuid import UUID

import psycopg

# Cap that prevents one runaway tool call from filling the notes column.
# At 2000 chars, the lead can write substantive paragraphs without
# generating multi-page outputs the model can't summarise back later.
MAX_NOTE_CHARS = 2000


class WriteResult(NamedTuple):
    """Returned by `write_lead_note`.

    `truncated` is True iff the input exceeded `MAX_NOTE_CHARS` and we
    stored only the first `MAX_NOTE_CHARS` characters."""

    body: str
    version: int
    truncated: bool


def read_lead_note_by_key(plan_id: UUID, key: str, db_url: str) -> str | None:
    """Latest body for `(plan_id, key)`. None if no note exists.

    Reads the highest version under `(plan_id, key)` ordered by version
    desc. Returns the `body_md` directly (callers don't need note_id /
    timestamp for memory recall)."""
    with (
        psycopg.connect(db_url) as conn,
        conn.cursor() as cur,
    ):
        cur.execute(
            "SELECT body_md FROM research_lead_notes"
            " WHERE plan_id = %s AND key = %s"
            " ORDER BY version DESC LIMIT 1",
            (str(plan_id), key),
        )
        row = cur.fetchone()
    return row[0] if row is not None else None


def write_lead_note(
    plan_id: UUID, key: str, body_md: str, db_url: str
) -> WriteResult:
    """Append a new version under `(plan_id, key)`. Truncates the body
    to `MAX_NOTE_CHARS` if it exceeds the cap.

    Computes the next version inside the same connection to avoid the
    SELECT→INSERT race; the unique constraint on
    `(plan_id, key, version)` is the secondary safeguard."""
    truncated = len(body_md) > MAX_NOTE_CHARS
    stored = body_md[:MAX_NOTE_CHARS] if truncated else body_md
    with (
        psycopg.connect(db_url) as conn,
        conn.cursor() as cur,
    ):
        cur.execute(
            "SELECT COALESCE(MAX(version), 0) + 1 FROM research_lead_notes"
            " WHERE plan_id = %s AND key = %s",
            (str(plan_id), key),
        )
        row = cur.fetchone()
        version = int(row[0]) if row is not None else 1
        cur.execute(
            "INSERT INTO research_lead_notes (plan_id, key, version, body_md)"
            " VALUES (%s, %s, %s, %s)",
            (str(plan_id), key, version, stored),
        )
    return WriteResult(body=stored, version=version, truncated=truncated)
