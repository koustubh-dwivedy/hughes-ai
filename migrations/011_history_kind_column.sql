-- HUG-141: Add kind discriminator to query_history so dashboard audit
-- entries can be filtered out of the user-facing chat history rail.

ALTER TABLE query_history
    ADD COLUMN IF NOT EXISTS kind TEXT NOT NULL DEFAULT 'ask'
        CHECK (kind IN ('ask', 'dashboard_audit'));

-- Backfill existing rows: anything whose question begins with "dashboard:"
-- was written by save_dashboard_audit and should be classified accordingly.
UPDATE query_history
   SET kind = 'dashboard_audit'
 WHERE kind = 'ask'
   AND question LIKE 'dashboard:%';

CREATE INDEX IF NOT EXISTS query_history_kind_idx
    ON query_history (kind, created_at DESC);
