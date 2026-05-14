"""Integration test: readonly role can SELECT but not INSERT."""
import os

import psycopg
import pytest

pytestmark = pytest.mark.db  # CI integration-test job (HUG-229)


@pytest.fixture
def db_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        pytest.skip("DATABASE_URL not set")
    return url


def test_readonly_can_select_new_tables(db_url: str) -> None:
    with psycopg.connect(db_url) as conn:
        conn.execute("SET ROLE readonly")
        conn.execute("SELECT COUNT(*) FROM members")
        conn.execute("SELECT COUNT(*) FROM officers")
        conn.execute("SELECT COUNT(*) FROM watchlist")
        conn.execute("SELECT COUNT(*) FROM loan_lifecycle_events")
        conn.execute("SELECT COUNT(*) FROM deposit_accounts")
        conn.execute("SELECT COUNT(*) FROM deposit_balances")
        conn.execute("SELECT COUNT(*) FROM deposit_events")


def test_readonly_cannot_insert(db_url: str) -> None:
    with psycopg.connect(db_url, autocommit=True) as conn:
        conn.execute("SET ROLE readonly")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(
                "INSERT INTO members"
                " (member_id, first_name, last_name, joined_at)"
                " VALUES (gen_random_uuid(), 'x', 'x', NOW())"
            )
