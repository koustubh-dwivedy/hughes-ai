-- Hughes AI — Data Model Revamp (HUG-162)
-- Adds: dealers, households, household_members, account_owners,
--       card_balances, card_transactions, dealer_id FK on booked_loans.
-- All idempotent. No drops; product enum changes are data-only.

-- ============================================================
-- DEALER (Origence indirect-lending side)
-- ============================================================

CREATE TABLE IF NOT EXISTS dealers (
    dealer_id     UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name          TEXT        NOT NULL,
    dealer_type   TEXT        NOT NULL,
    address_city  TEXT,
    address_state TEXT,
    markup_tier   TEXT        NOT NULL,                  -- 'standard' | 'premium' | 'aggressive'
    active_from   TIMESTAMPTZ NOT NULL,
    active_until  TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT dealers_dealer_type_check
        CHECK (dealer_type IN ('auto_franchise', 'auto_independent'))
);

ALTER TABLE booked_loans
    ADD COLUMN IF NOT EXISTS dealer_id            UUID REFERENCES dealers(dealer_id),
    ADD COLUMN IF NOT EXISTS dealer_reserve_amount NUMERIC(12, 2);

CREATE INDEX IF NOT EXISTS idx_booked_loans_dealer_id ON booked_loans(dealer_id);

-- ============================================================
-- MEMBER 360 (households + bridge tables)
-- ============================================================

CREATE TABLE IF NOT EXISTS households (
    household_id      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    household_name    TEXT        NOT NULL,
    primary_member_id UUID        NOT NULL REFERENCES members(member_id),
    formed_at         TIMESTAMPTZ NOT NULL,
    dissolved_at      TIMESTAMPTZ,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_households_primary_member_id
    ON households(primary_member_id);

CREATE TABLE IF NOT EXISTS household_members (
    household_member_id UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id        UUID        NOT NULL REFERENCES households(household_id),
    member_id           UUID        NOT NULL REFERENCES members(member_id),
    role                TEXT        NOT NULL,
    joined_at           TIMESTAMPTZ NOT NULL,
    left_at             TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT household_members_role_check
        CHECK (role IN ('primary', 'joint', 'dependent'))
);

CREATE INDEX IF NOT EXISTS idx_household_members_household_id
    ON household_members(household_id);
CREATE INDEX IF NOT EXISTS idx_household_members_member_id
    ON household_members(member_id);

-- account_owners works for both loans and deposit accounts via owner_kind +
-- owner_account_id (UUID references either booked_loans.loan_id or
-- deposit_accounts.account_id). Foreign key not enforced at DB level
-- because the referent is polymorphic; integrity is enforced in audit tests.
CREATE TABLE IF NOT EXISTS account_owners (
    owner_id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_kind        TEXT        NOT NULL,            -- 'loan' | 'deposit'
    owner_account_id  UUID        NOT NULL,
    member_id         UUID        NOT NULL REFERENCES members(member_id),
    role              TEXT        NOT NULL,
    since             TIMESTAMPTZ NOT NULL,
    until_ts          TIMESTAMPTZ,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT account_owners_role_check
        CHECK (role IN ('primary', 'joint', 'pod_beneficiary', 'authorized_signer')),
    CONSTRAINT account_owners_kind_check
        CHECK (owner_kind IN ('loan', 'deposit'))
);

CREATE INDEX IF NOT EXISTS idx_account_owners_owner_account_id
    ON account_owners(owner_account_id);
CREATE INDEX IF NOT EXISTS idx_account_owners_member_id
    ON account_owners(member_id);

-- ============================================================
-- CREDIT CARD ledger (transaction-grade detail for revolving credit)
-- ============================================================

CREATE TABLE IF NOT EXISTS card_balances (
    balance_id    UUID    PRIMARY KEY DEFAULT gen_random_uuid(),
    loan_id       UUID    NOT NULL REFERENCES booked_loans(loan_id),
    snapshot_date DATE    NOT NULL,
    balance       NUMERIC(12, 2) NOT NULL,
    credit_limit  NUMERIC(12, 2) NOT NULL,
    created_at    TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    UNIQUE (loan_id, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_card_balances_loan_id ON card_balances(loan_id);

CREATE TABLE IF NOT EXISTS card_transactions (
    transaction_id UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    loan_id        UUID        NOT NULL REFERENCES booked_loans(loan_id),
    occurred_at    TIMESTAMPTZ NOT NULL,
    amount         NUMERIC(12, 2) NOT NULL,
    txn_type       TEXT        NOT NULL,
    merchant_category TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT card_transactions_type_check
        CHECK (txn_type IN ('purchase', 'payment', 'cash_advance', 'fee', 'interest_accrual'))
);

CREATE INDEX IF NOT EXISTS idx_card_transactions_loan_id ON card_transactions(loan_id);
CREATE INDEX IF NOT EXISTS idx_card_transactions_occurred_at
    ON card_transactions(occurred_at);
