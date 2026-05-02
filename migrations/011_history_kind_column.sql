-- HUG-141: Add kind discriminator to query_history so dashboard audit
-- entries can be filtered out of the user-facing chat history rail.

ALTER TABLE query_history
    ADD COLUMN IF NOT EXISTS kind TEXT NOT NULL DEFAULT 'ask'
        CHECK (kind IN ('ask', 'dashboard_audit'));

-- The append-only trigger from migration 002 rejects any UPDATE on
-- query_history. Toggle it around the one-time backfill so this
-- migration is apply-able by any psql client without manual setup.
ALTER TABLE query_history DISABLE TRIGGER query_history_append_only;

-- Backfill existing rows: anything whose question begins with "dashboard:"
-- was written by save_dashboard_audit and should be classified accordingly.
UPDATE query_history
   SET kind = 'dashboard_audit'
 WHERE kind = 'ask'
   AND question LIKE 'dashboard:%';

ALTER TABLE query_history ENABLE TRIGGER query_history_append_only;

CREATE INDEX IF NOT EXISTS query_history_kind_idx
    ON query_history (kind, created_at DESC);
