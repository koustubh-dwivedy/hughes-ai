-- Hughes AI — Members dimension
-- Adds named member rows backing booked_loans.member_id and applications.member_id

CREATE TABLE IF NOT EXISTS members (
    member_id      UUID PRIMARY KEY,
    first_name     TEXT        NOT NULL,
    last_name      TEXT        NOT NULL,
    joined_at      TIMESTAMPTZ NOT NULL,
    home_branch_id INT         REFERENCES branches(branch_id),
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_members_home_branch_id ON members(home_branch_id);

-- Deferred so bulk COPY of booked_loans doesn't require members to be committed first
ALTER TABLE booked_loans
    ADD CONSTRAINT fk_booked_loans_member_id
    FOREIGN KEY (member_id) REFERENCES members(member_id)
    DEFERRABLE INITIALLY DEFERRED;
