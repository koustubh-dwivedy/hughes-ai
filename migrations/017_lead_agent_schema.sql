-- Hughes AI — Lead agent schema (HUG-241, deep-research re-architecture)
--
-- Foundation tables / columns for the autonomous lead-agent migration
-- (the LangGraph re-shape replacing the planner/executor/synthesizer
-- pipeline with a single ReAct lead that exposes plan + memory + run-
-- subagent as ordinary tools). Specifically:
--
--   subagent_calls               — new audit table; one row per
--                                  run_subagent invocation by the
--                                  lead. Persists prompt + result +
--                                  status + plan-step ordinal.
--   thread_messages.plan_id      — new nullable FK; lets the final-
--                                  answer message link back to the
--                                  plan that produced it (powers
--                                  ResearchAuditPanel).
--   research_lead_notes.key      — new column; turns notes into a
--                                  key/value scratchpad so the lead
--                                  can call read_memory(key) /
--                                  write_memory(key, body) per slot.
--   research_plans.status        — additive: adds `proposed` to the
--                                  allowed values for the new shape.
--                                  Old values kept so legacy code
--                                  during the migration window still
--                                  works; HUG-247 drops them.
--
-- Idempotent (`IF NOT EXISTS` guards + targeted constraint drop/add).
-- Cascade behaviour matches 016: thread → plan → notes deletes flow,
-- subagent_calls cascades from threads.

BEGIN;

-- ============================================================
-- SUBAGENT_CALLS — audit row per run_subagent invocation
-- ============================================================

CREATE TABLE IF NOT EXISTS subagent_calls (
    call_id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id          UUID         NOT NULL REFERENCES threads(thread_id) ON DELETE CASCADE,
    plan_id            UUID         REFERENCES research_plans(plan_id) ON DELETE SET NULL,
    parent_message_id  UUID         REFERENCES thread_messages(message_id) ON DELETE SET NULL,
    plan_step_ordinal  INTEGER,
    prompt             TEXT         NOT NULL,
    status             TEXT         NOT NULL,
    summary_text       TEXT,
    rows_json          JSONB,
    mf_query_json      JSONB,
    error_text         TEXT,
    started_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    completed_at       TIMESTAMPTZ,
    CONSTRAINT subagent_calls_status_check CHECK (
        status IN ('pending', 'running', 'complete', 'failed')
    )
);

CREATE INDEX IF NOT EXISTS idx_subagent_calls_thread_status
    ON subagent_calls (thread_id, status);
CREATE INDEX IF NOT EXISTS idx_subagent_calls_plan
    ON subagent_calls (plan_id);

-- ============================================================
-- THREAD_MESSAGES.plan_id — link final_answer back to its plan
-- ============================================================

ALTER TABLE thread_messages
    ADD COLUMN IF NOT EXISTS plan_id UUID
        REFERENCES research_plans(plan_id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_thread_messages_plan_id
    ON thread_messages (plan_id);

-- ============================================================
-- RESEARCH_LEAD_NOTES.key — keyed scratchpad
-- ============================================================

ALTER TABLE research_lead_notes
    ADD COLUMN IF NOT EXISTS key TEXT NOT NULL DEFAULT '';

-- Replace the (plan_id, version) uniqueness with (plan_id, key, version)
-- so multiple keys can coexist under a plan. Drop-if-exists guards
-- idempotency.
ALTER TABLE research_lead_notes
    DROP CONSTRAINT IF EXISTS research_lead_notes_version_per_plan;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'research_lead_notes_version_per_plan_key'
    ) THEN
        ALTER TABLE research_lead_notes
            ADD CONSTRAINT research_lead_notes_version_per_plan_key
            UNIQUE (plan_id, key, version);
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS idx_research_lead_notes_plan_key_version
    ON research_lead_notes (plan_id, key, version DESC);

-- ============================================================
-- RESEARCH_PLANS.status — accept `proposed`
-- ============================================================
-- Keep legacy values (draft/approved/running) until HUG-247 cleans up.

ALTER TABLE research_plans
    DROP CONSTRAINT IF EXISTS research_plans_status_check;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'research_plans_status_check'
    ) THEN
        ALTER TABLE research_plans
            ADD CONSTRAINT research_plans_status_check
            CHECK (status IN (
                'draft',
                'approved',
                'running',
                'complete',
                'aborted',
                'failed',
                'superseded',
                'proposed'
            ));
    END IF;
END
$$;

COMMIT;
