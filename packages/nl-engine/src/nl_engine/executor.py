"""Read-only psycopg executor with 30-second statement timeout."""

import psycopg


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
                dict(zip(columns, row, strict=False))
                for row in cur.fetchall()
            ]
    return rows, columns
