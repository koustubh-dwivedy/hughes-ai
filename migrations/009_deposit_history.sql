CREATE TABLE IF NOT EXISTS deposit_balances (
    balance_id    UUID PRIMARY KEY,
    account_id    UUID NOT NULL REFERENCES deposit_accounts(account_id),
    snapshot_date DATE NOT NULL,
    balance       NUMERIC(18, 2) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dep_bal_account
    ON deposit_balances(account_id);
CREATE INDEX IF NOT EXISTS idx_dep_bal_snapshot
    ON deposit_balances(snapshot_date);

CREATE TABLE IF NOT EXISTS deposit_events (
    event_id   UUID PRIMARY KEY,
    account_id UUID NOT NULL REFERENCES deposit_accounts(account_id),
    event_type TEXT NOT NULL
        CHECK (event_type IN ('opened', 'closed', 'balance_change')),
    event_at   TIMESTAMPTZ NOT NULL,
    amount     NUMERIC(18, 2) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dep_evt_account
    ON deposit_events(account_id);
CREATE INDEX IF NOT EXISTS idx_dep_evt_type
    ON deposit_events(event_type);
