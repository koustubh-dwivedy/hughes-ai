CREATE TABLE IF NOT EXISTS deposit_products (
    deposit_product_id UUID        PRIMARY KEY,
    name               TEXT        NOT NULL,
    is_core_deposit    BOOLEAN     NOT NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS deposit_accounts (
    account_id         UUID        PRIMARY KEY,
    member_id          UUID        NOT NULL REFERENCES members(member_id),
    branch_id          INTEGER     NOT NULL REFERENCES branches(branch_id),
    deposit_product_id UUID        NOT NULL REFERENCES deposit_products(deposit_product_id),
    opened_at          TIMESTAMPTZ NOT NULL,
    closed_at          TIMESTAMPTZ,
    current_balance    NUMERIC(18, 2) NOT NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_deposit_accounts_member
    ON deposit_accounts(member_id);
CREATE INDEX IF NOT EXISTS idx_deposit_accounts_branch
    ON deposit_accounts(branch_id);
CREATE INDEX IF NOT EXISTS idx_deposit_accounts_product
    ON deposit_accounts(deposit_product_id);
