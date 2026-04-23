-- Append-only audit log of every NL query and its result.
-- No UPDATE or DELETE is permitted (enforced by trigger below).

CREATE TABLE IF NOT EXISTS query_history (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    question     TEXT        NOT NULL,
    sql          TEXT        NOT NULL,
    answer_json  JSONB       NOT NULL DEFAULT '{}',
    assumptions  JSONB       NOT NULL DEFAULT '[]',
    caveats      JSONB       NOT NULL DEFAULT '[]',
    lineage_json JSONB       NOT NULL DEFAULT '{}',
    token_usage  JSONB       NOT NULL DEFAULT '{}',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS query_history_created_at_idx
    ON query_history (created_at DESC);

-- Enforce append-only at the database level.
CREATE OR REPLACE FUNCTION query_history_no_modify()
    RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'query_history is append-only: % is not allowed', TG_OP;
END;
$$;

CREATE OR REPLACE TRIGGER query_history_append_only
    BEFORE UPDATE OR DELETE ON query_history
    FOR EACH ROW EXECUTE FUNCTION query_history_no_modify();
