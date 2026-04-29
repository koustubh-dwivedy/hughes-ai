-- HUG-59: Add is_nonaccrual flag to booked_loans + watchlist table

ALTER TABLE booked_loans
    ADD COLUMN IF NOT EXISTS is_nonaccrual BOOLEAN NOT NULL DEFAULT FALSE;

CREATE TABLE IF NOT EXISTS watchlist (
    watchlist_id UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    loan_id      UUID        NOT NULL REFERENCES booked_loans(loan_id),
    added_at     TIMESTAMPTZ NOT NULL,
    removed_at   TIMESTAMPTZ,
    reason       TEXT        NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_watchlist_loan_id ON watchlist(loan_id);
CREATE INDEX IF NOT EXISTS idx_watchlist_added_at ON watchlist(added_at);
