-- Hughes AI — Reload-safe agent turns (HUG-266)
--
-- Problem: agent execution was tied to the SSE connection lifetime.
-- When the client disconnected (page reload), sse-starlette cancelled
-- the SSE-consuming generator, which stopped consume_queue, which
-- meant chat_process_message never ran for the rest of the turn and
-- the assistant rows for that turn were never persisted to
-- thread_messages. The background LangGraph thread kept running but
-- its output went to a dead queue.
--
-- Fix (HUG-266): decouple agent execution from SSE. Background task
-- persists every message to thread_messages immediately. SSE handler
-- becomes a tail that polls thread_messages for new rows. On reload,
-- the SPA detects an in-flight turn and reconnects to the tail.
--
-- This migration adds the durable state the new architecture needs:
--   turn_state              — one row per agent turn. Tracks status
--                             ('running' | 'complete' | 'failed' |
--                             'aborted') so reloads can detect
--                             whether to reconnect, and so orphan
--                             cleanup on API restart can mark dead
--                             in-process tasks as 'failed'.
--   thread_messages.seq_no  — strictly-monotonic cursor for tail
--                             polling (`WHERE seq_no > $cursor`).
--   thread_messages.turn_id — links each message to the turn that
--                             produced it. Lets the tail filter to a
--                             single turn even if a second turn
--                             starts on the same thread before the
--                             first is observed (multi-tab edge case).
--
-- Additive only — rolling back the new code leaves the new columns
-- unused; the old code path ignores them. No schema rollback needed.

BEGIN;

CREATE TABLE IF NOT EXISTS turn_state (
    turn_id      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id    UUID        NOT NULL REFERENCES threads(thread_id) ON DELETE CASCADE,
    status       TEXT        NOT NULL CHECK (status IN ('running','complete','failed','aborted')),
    started_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    error_text   TEXT,
    last_seq_no  BIGINT
);

-- Partial index: only running rows matter for "is this thread mid-turn?"
-- lookups. Small index, fast existence checks.
CREATE INDEX IF NOT EXISTS idx_turn_state_thread_running
    ON turn_state (thread_id)
    WHERE status = 'running';

-- General index for orphan cleanup and audit queries.
CREATE INDEX IF NOT EXISTS idx_turn_state_status_started
    ON turn_state (status, started_at);

-- BIGSERIAL gives a strictly-monotonic cursor without depending on
-- created_at (which is vulnerable to clock skew under concurrency).
ALTER TABLE thread_messages
    ADD COLUMN IF NOT EXISTS seq_no  BIGSERIAL,
    ADD COLUMN IF NOT EXISTS turn_id UUID REFERENCES turn_state(turn_id) ON DELETE SET NULL;

-- Backfill seq_no for pre-existing rows in created_at order so the tail
-- cursor is consistent across the whole history. BIGSERIAL's sequence
-- already advanced for new inserts; only old rows need values.
UPDATE thread_messages
   SET seq_no = nextval(pg_get_serial_sequence('thread_messages', 'seq_no'))
 WHERE seq_no IS NULL;

-- After backfill, enforce NOT NULL so the tail cursor is always well-defined.
ALTER TABLE thread_messages
    ALTER COLUMN seq_no SET NOT NULL;

-- Tail uses (thread_id, seq_no) for `WHERE thread_id=X AND seq_no > cursor`.
CREATE INDEX IF NOT EXISTS idx_thread_messages_thread_seq
    ON thread_messages (thread_id, seq_no);

-- Tail also filters by turn_id to scope to a single turn.
CREATE INDEX IF NOT EXISTS idx_thread_messages_turn
    ON thread_messages (turn_id, seq_no)
    WHERE turn_id IS NOT NULL;

COMMIT;
