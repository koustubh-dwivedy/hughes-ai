"""Read-only psycopg executor with 30-second statement timeout."""

import datetime
from decimal import Decimal
from uuid import UUID

import psycopg


def _normalize(v: object) -> object:
    """Convert psycopg-returned types to JSON-safe primitives."""
    if isinstance(v, UUID):
        return str(v)
    if isinstance(v, datetime.datetime):
        return v.isoformat()
    if isinstance(v, datetime.date):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, datetime.timedelta):
        return str(v)
    return v


def execute_sql(
    sql: str, db_url: str
) -> tuple[list[dict[str, object]], list[str]]:
    """Execute a SELECT and return (rows, column_names)."""
    with psycopg.connect(db_url) as conn:
        conn.execute("SET statement_timeout = 30000")
        with conn.cursor() as cur:
            cur.execute(sql)
            columns = [desc.name for desc in cur.description or []]
            rows = [
                {col: _normalize(val) for col, val in zip(columns, row, strict=False)}
                for row in cur.fetchall()
            ]
    return rows, columns
