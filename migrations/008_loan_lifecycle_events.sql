CREATE TABLE IF NOT EXISTS loan_lifecycle_events (
    event_id    UUID PRIMARY KEY,
    loan_id     UUID NOT NULL REFERENCES booked_loans(loan_id),
    event_month DATE NOT NULL,
    event_type  TEXT NOT NULL
        CHECK (event_type IN ('new', 'renewed', 'paid_off', 'active'))
);

CREATE INDEX IF NOT EXISTS idx_lle_loan_id
    ON loan_lifecycle_events(loan_id);
CREATE INDEX IF NOT EXISTS idx_lle_event_month
    ON loan_lifecycle_events(event_month);
