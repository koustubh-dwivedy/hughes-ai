"""Read-only access helpers for dashboard mart tables."""

import psycopg


def fetch_mart_rows(
    sql: str,
    params: tuple[object, ...],
    db_url: str,
) -> list[dict[str, object]]:
    """Execute a parameterised read-only query and return rows as dicts."""
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        cols = [d.name for d in cur.description or []]
        return [dict(zip(cols, row, strict=False)) for row in cur.fetchall()]
