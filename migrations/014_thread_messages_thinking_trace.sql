-- Hughes AI — thread_messages.thinking_trace (HUG-202 Phase 3)
--
-- Adds a JSONB column to persist the agent's chain of work during a
-- turn: each tool call, tool result, and narration line, in order.
-- The Thinking-box shows ONE line at a time during streaming; this
-- column is what the References modal reads to surface the full
-- audit trail after the turn completes.
--
-- Idempotent: ADD COLUMN IF NOT EXISTS so re-running the migration
-- doesn't fail on databases that already applied it.

ALTER TABLE thread_messages
    ADD COLUMN IF NOT EXISTS thinking_trace JSONB;
