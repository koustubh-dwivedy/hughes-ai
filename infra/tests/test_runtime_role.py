"""HUG-257 — runtime DB role privilege assertions.

Connects as cubi_runtime (via the Cloud SQL Auth Proxy on localhost:5433)
and verifies the role's privilege model holds in production:
- can SELECT lending tables
- cannot INSERT/UPDATE/DELETE lending tables
- can INSERT/UPDATE app-state tables
- cannot DELETE app-state tables (DELETE is not granted to anyone but the
  migrate role; it's the strongest signal that we haven't accidentally
  over-granted)

Run via:
    make verify-prod-role

Prerequisites:
- infra/setup.sh + infra/bootstrap.sh have been run.
- `cloud-sql-proxy` available and proxying tryhughes:europe-west1:hughes-pg
  on localhost:5433 (the Makefile target sets this up).

This file lives in infra/tests/ (not tests/) so the standard pytest suite
does not pick it up — it requires cloud credentials + a live Auth Proxy,
which CI doesn't have.
"""

from __future__ import annotations

import os
import subprocess

import psycopg
import pytest


def _runtime_url() -> str:
    """Fetch the runtime DATABASE_URL from Secret Manager and rewrite for TCP.

    Secret Manager holds a Unix-socket URL (Cloud Run uses /cloudsql/<conn>);
    the test connects via TCP through the Auth Proxy on localhost:5433.
    """
    project = os.environ.get("GCP_PROJECT", "tryhughes")
    raw = subprocess.check_output(
        ["gcloud", "secrets", "versions", "access", "latest",
         "--secret=database-url", f"--project={project}"],
        text=True,
    ).strip()
    # raw looks like postgresql+psycopg://USER:PASS@/cubi?host=/cloudsql/...
    # Convert to postgresql://USER:PASS@localhost:5433/cubi
    user_pass = raw.split("://", 1)[1].split("@", 1)[0]
    db_name = os.environ.get("DB_NAME", "cubi")
    return f"postgresql://{user_pass}@localhost:5433/{db_name}"


@pytest.fixture(scope="module")
def conn():
    with psycopg.connect(_runtime_url()) as c:
        yield c


def test_can_select_lending_table(conn):
    """cubi_runtime can read members (lending data)."""
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM members")
        n = cur.fetchone()[0]
    assert n >= 3000, f"members table looks empty or under-seeded: {n}"
    conn.rollback()


def test_cannot_insert_lending_table(conn):
    """cubi_runtime CANNOT write to lending tables."""
    with pytest.raises(psycopg.errors.InsufficientPrivilege), conn.cursor() as cur:
        cur.execute(
            "INSERT INTO members (member_id, first_name, last_name, joined_at) "
            "VALUES (gen_random_uuid(), 'x', 'x', NOW())"
        )
    conn.rollback()


def test_cannot_update_lending_table(conn):
    """cubi_runtime CANNOT update lending tables."""
    with pytest.raises(psycopg.errors.InsufficientPrivilege), conn.cursor() as cur:
        cur.execute("UPDATE members SET first_name = 'x' WHERE 1 = 0")
    conn.rollback()


def test_cannot_delete_lending_table(conn):
    """cubi_runtime CANNOT delete from lending tables."""
    with pytest.raises(psycopg.errors.InsufficientPrivilege), conn.cursor() as cur:
        cur.execute("DELETE FROM members WHERE 1 = 0")
    conn.rollback()


def test_can_insert_app_state_table(conn):
    """cubi_runtime CAN insert into query_history (audit log)."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO query_history (question, sql) "
            "VALUES ('test_runtime_role', 'SELECT 1') "
            "RETURNING id"
        )
        qid = cur.fetchone()[0]
    assert qid is not None
    conn.rollback()  # don't pollute the table


def test_cannot_delete_app_state_table(conn):
    """cubi_runtime CANNOT delete from app-state tables either.

    Note: query_history also has an append-only trigger, but for `threads`
    the only thing blocking DELETE is the missing GRANT — exactly what we
    want to assert.
    """
    with pytest.raises(psycopg.errors.InsufficientPrivilege), conn.cursor() as cur:
        cur.execute("DELETE FROM threads WHERE 1 = 0")
    conn.rollback()
