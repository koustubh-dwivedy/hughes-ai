-- Hughes AI — Officers dimension
-- Adds named loan officers backing booked_loans.officer_id

CREATE TABLE IF NOT EXISTS officers (
    officer_id  UUID        PRIMARY KEY,
    name        TEXT        NOT NULL,
    branch_id   INT         NOT NULL REFERENCES branches(branch_id),
    hired_at    TIMESTAMPTZ NOT NULL,
    status      TEXT        NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT officers_status_check CHECK (status IN ('active', 'departed'))
);

CREATE INDEX IF NOT EXISTS idx_officers_branch_id ON officers(branch_id);

-- Deferred so bulk COPY of booked_loans doesn't require officers to be committed first
ALTER TABLE booked_loans
    ADD COLUMN officer_id UUID REFERENCES officers(officer_id)
    DEFERRABLE INITIALLY DEFERRED;
