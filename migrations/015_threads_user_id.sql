-- Hughes AI — threads.user_id (HUG-205)
--
-- Splits "telemetry session" from "thread ownership". Until now, the
-- frontend's per-tab sessionStorage UUID doubled as both the log-
-- correlation handle AND the thread-list filter. Closing a tab
-- minted a fresh UUID and orphaned the user's history. This column
-- introduces a separate durable identity stored in the frontend's
-- localStorage; thread visibility now follows it across tab closes,
-- browser restarts, and days of dormancy.
--
-- The session_id column stays. It still tags every row with the
-- visit during which the thread was created, which is useful audit
-- context. But thread access goes through user_id from now on.

ALTER TABLE threads
    ADD COLUMN IF NOT EXISTS user_id TEXT;

-- Backfill so existing rows aren't orphaned in the schema. Each
-- thread inherits its session_id as user_id — no live frontend will
-- hold these UUIDs in localStorage today (they came from sessionStorage
-- that got wiped on tab close), but the data stays queryable in psql
-- and a one-line UPDATE could reassign batches to a real user_id later.
UPDATE threads
   SET user_id = session_id
 WHERE user_id IS NULL;

-- Index supports the dominant access pattern: GET /threads filtered by
-- user_id, ordered by last_active_at DESC.
CREATE INDEX IF NOT EXISTS idx_threads_user_id_active
    ON threads(user_id, last_active_at DESC);
