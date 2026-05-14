-- Hughes AI — Research tables (HUG-202, deep-research feature)
--
-- Adds four typed tables holding research-specific structure that
-- doesn't fit thread_messages' message-log shape:
--
--   research_plans       — versioned plan-as-doc; one row per plan
--                          version, status enum tracks lifecycle.
--   research_steps       — typed step rows under a plan; ordinal +
--                          status enum.
--   research_findings    — one row per subagent finding, linked to
--                          its step; structured rows + mf_query +
--                          citations in JSONB columns.
--   research_lead_notes  — the lead's running markdown notes (the
--                          "external plan memory" primitive from
--                          Anthropic's lead+subagents pattern);
--                          versioned per plan.
--
-- Auth inherits from threads.user_id via FK on research_plans. All
-- four tables cascade-delete from their parent (thread → plan →
-- step → finding; plan → note) so deleting a thread leaves no
-- orphans. Migration is idempotent.

-- ============================================================
-- RESEARCH_PLANS — versioned plan documents
-- ============================================================

CREATE TABLE IF NOT EXISTS research_plans (
    plan_id     UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id   UUID         NOT NULL REFERENCES threads(thread_id) ON DELETE CASCADE,
    version     INTEGER      NOT NULL,
    status      TEXT         NOT NULL,
    plan_json   JSONB        NOT NULL,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT research_plans_version_per_thread UNIQUE (thread_id, version),
    CONSTRAINT research_plans_status_check CHECK (
        status IN (
            'draft',
            'approved',
            'running',
            'complete',
            'aborted',
            'failed',
            'superseded'
        )
    )
);

CREATE INDEX IF NOT EXISTS idx_research_plans_thread_version
    ON research_plans (thread_id, version DESC);

-- ============================================================
-- RESEARCH_STEPS — typed step rows per plan
-- ============================================================

CREATE TABLE IF NOT EXISTS research_steps (
    step_id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id            UUID         NOT NULL REFERENCES research_plans(plan_id) ON DELETE CASCADE,
    ordinal            INTEGER      NOT NULL,
    description        TEXT         NOT NULL,
    status             TEXT         NOT NULL,
    assigned_subagent  TEXT,
    started_at         TIMESTAMPTZ,
    completed_at       TIMESTAMPTZ,
    CONSTRAINT research_steps_ordinal_per_plan UNIQUE (plan_id, ordinal),
    CONSTRAINT research_steps_status_check CHECK (
        status IN ('pending', 'running', 'complete', 'failed', 'skipped')
    )
);

CREATE INDEX IF NOT EXISTS idx_research_steps_plan
    ON research_steps (plan_id, ordinal);

-- ============================================================
-- RESEARCH_FINDINGS — one row per subagent finding
-- ============================================================

CREATE TABLE IF NOT EXISTS research_findings (
    finding_id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    step_id               UUID         NOT NULL REFERENCES research_steps(step_id) ON DELETE CASCADE,
    summary_text          TEXT,
    structured_rows_json  JSONB,
    mf_query_json         JSONB,
    cited_artifacts       JSONB,
    created_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_research_findings_step
    ON research_findings (step_id);

-- ============================================================
-- RESEARCH_LEAD_NOTES — lead's external plan memory (versioned)
-- ============================================================

CREATE TABLE IF NOT EXISTS research_lead_notes (
    note_id     UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id     UUID         NOT NULL REFERENCES research_plans(plan_id) ON DELETE CASCADE,
    version     INTEGER      NOT NULL,
    body_md     TEXT         NOT NULL,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT research_lead_notes_version_per_plan UNIQUE (plan_id, version)
);

CREATE INDEX IF NOT EXISTS idx_research_lead_notes_plan_version
    ON research_lead_notes (plan_id, version DESC);
