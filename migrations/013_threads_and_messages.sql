-- Hughes AI — Threads + thread_messages (HUG-175)
-- Adds: threads, thread_messages tables for multi-turn conversation
-- persistence, plus thread_id + message_id columns on query_history for
-- linkage to legacy single-shot rows. All idempotent.

-- ============================================================
-- THREADS — one row per conversation
-- ============================================================

CREATE TABLE IF NOT EXISTS threads (
    thread_id        UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id       TEXT        NOT NULL,
    title            TEXT,
    started_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_active_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at         TIMESTAMPTZ,
    slots            JSONB       NOT NULL DEFAULT '{}'::jsonb,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_threads_session_id    ON threads(session_id);
CREATE INDEX IF NOT EXISTS idx_threads_last_active   ON threads(last_active_at DESC);

-- ============================================================
-- THREAD_MESSAGES — one row per message in a thread
-- ============================================================

CREATE TABLE IF NOT EXISTS thread_messages (
    message_id        UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id         UUID        NOT NULL REFERENCES threads(thread_id),
    parent_message_id UUID        REFERENCES thread_messages(message_id),
    role              TEXT        NOT NULL,
    content           TEXT,
    tool_calls        JSONB,
    tool_results      JSONB,
    openui_dsl        TEXT,
    mf_query          JSONB,
    rows              JSONB,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT thread_messages_role_check
        CHECK (role IN ('user', 'assistant', 'tool', 'system'))
);

CREATE INDEX IF NOT EXISTS idx_thread_messages_thread_id
    ON thread_messages(thread_id);
CREATE INDEX IF NOT EXISTS idx_thread_messages_thread_created
    ON thread_messages(thread_id, created_at);

-- ============================================================
-- QUERY_HISTORY — add thread linkage columns (nullable for legacy rows)
-- ============================================================

ALTER TABLE query_history
    ADD COLUMN IF NOT EXISTS thread_id  UUID REFERENCES threads(thread_id),
    ADD COLUMN IF NOT EXISTS message_id UUID REFERENCES thread_messages(message_id);

CREATE INDEX IF NOT EXISTS idx_query_history_thread_id
    ON query_history(thread_id);
