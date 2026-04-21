-- Hughes AI — Lending Schema
-- Origence Connect LOS (applications side) + Jack Henry Symitar (core side)

CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- ORIGENCE-SIDE: lookup tables
-- ============================================================

CREATE TABLE IF NOT EXISTS product_types (
    product_type_id SERIAL PRIMARY KEY,
    name            TEXT        NOT NULL UNIQUE,
    description     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS channels (
    channel_id SERIAL PRIMARY KEY,
    name       TEXT        NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- ORIGENCE-SIDE: fact tables
-- ============================================================

CREATE TABLE IF NOT EXISTS applications (
    application_id   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    member_id        UUID        NOT NULL,
    product_type_id  INT         NOT NULL REFERENCES product_types(product_type_id),
    channel_id       INT         NOT NULL REFERENCES channels(channel_id),
    requested_amount NUMERIC(12, 2) NOT NULL,
    applied_at       TIMESTAMPTZ NOT NULL,
    status           TEXT        NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT applications_status_check CHECK (
        status IN ('pending', 'approved', 'declined', 'withdrawn', 'funded')
    )
);

CREATE INDEX IF NOT EXISTS idx_applications_product_type_id ON applications(product_type_id);
CREATE INDEX IF NOT EXISTS idx_applications_channel_id      ON applications(channel_id);

CREATE TABLE IF NOT EXISTS stages (
    stage_id       UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID        NOT NULL REFERENCES applications(application_id),
    stage_name     TEXT        NOT NULL,
    entered_at     TIMESTAMPTZ NOT NULL,
    exited_at      TIMESTAMPTZ,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_stages_application_id ON stages(application_id);

CREATE TABLE IF NOT EXISTS approvals (
    approval_id     UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id  UUID        NOT NULL REFERENCES applications(application_id),
    decision        TEXT        NOT NULL,
    decided_at      TIMESTAMPTZ NOT NULL,
    approved_amount NUMERIC(12, 2),
    rate            NUMERIC(6, 4),
    term_months     INT,
    decline_reason  TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT approvals_decision_check CHECK (
        decision IN ('approved', 'declined', 'conditional')
    )
);

CREATE INDEX IF NOT EXISTS idx_approvals_application_id ON approvals(application_id);

CREATE TABLE IF NOT EXISTS funding_events (
    funding_id     UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID        NOT NULL REFERENCES applications(application_id),
    funded_at      TIMESTAMPTZ NOT NULL,
    funded_amount  NUMERIC(12, 2) NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_funding_events_application_id ON funding_events(application_id);

-- ============================================================
-- SYMITAR-SIDE: lookup tables
-- ============================================================

CREATE TABLE IF NOT EXISTS branches (
    branch_id  SERIAL PRIMARY KEY,
    name       TEXT        NOT NULL UNIQUE,
    region     TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- SYMITAR-SIDE: fact tables
-- ============================================================

CREATE TABLE IF NOT EXISTS booked_loans (
    loan_id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id   UUID        REFERENCES applications(application_id),  -- nullable: LOS bridge
    branch_id        INT         NOT NULL REFERENCES branches(branch_id),
    member_id        UUID        NOT NULL,
    product_type_id  INT         NOT NULL REFERENCES product_types(product_type_id),
    originated_at    TIMESTAMPTZ NOT NULL,
    original_balance NUMERIC(12, 2) NOT NULL,
    balance          NUMERIC(12, 2) NOT NULL,
    rate             NUMERIC(6, 4)  NOT NULL,
    term_months      INT         NOT NULL,
    maturity_at      TIMESTAMPTZ NOT NULL,
    status           TEXT        NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT booked_loans_status_check CHECK (
        status IN ('current', 'delinquent', 'charged_off', 'paid_off')
    )
);

CREATE INDEX IF NOT EXISTS idx_booked_loans_application_id  ON booked_loans(application_id);
CREATE INDEX IF NOT EXISTS idx_booked_loans_branch_id       ON booked_loans(branch_id);
CREATE INDEX IF NOT EXISTS idx_booked_loans_product_type_id ON booked_loans(product_type_id);

CREATE TABLE IF NOT EXISTS loan_balances (
    balance_id    UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    loan_id       UUID    NOT NULL REFERENCES booked_loans(loan_id),
    snapshot_date DATE    NOT NULL,
    balance       NUMERIC(12, 2) NOT NULL,
    created_at    TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    UNIQUE (loan_id, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_loan_balances_loan_id ON loan_balances(loan_id);

CREATE TABLE IF NOT EXISTS payments (
    payment_id     UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    loan_id        UUID        NOT NULL REFERENCES booked_loans(loan_id),
    paid_at        TIMESTAMPTZ NOT NULL,
    amount         NUMERIC(12, 2) NOT NULL,
    principal      NUMERIC(12, 2) NOT NULL,
    interest       NUMERIC(12, 2) NOT NULL,
    payment_method TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_payments_loan_id ON payments(loan_id);

CREATE TABLE IF NOT EXISTS delinquency_snapshots (
    snapshot_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    loan_id            UUID NOT NULL REFERENCES booked_loans(loan_id),
    snapshot_date      DATE NOT NULL,
    days_past_due      INT  NOT NULL DEFAULT 0,
    delinquency_bucket TEXT,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (loan_id, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_delinquency_snapshots_loan_id ON delinquency_snapshots(loan_id);
