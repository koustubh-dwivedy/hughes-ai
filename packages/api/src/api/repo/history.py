"""Append-only query history repository.

`save_query` (which inserted the Surface 1 / `kind='ask'` row) is gone
along with Surface 1 itself (HUG-193). Threads writes its own rows via
`packages/api/src/api/repo/threads.py`. Reads still serve historical
`'ask'` rows so the HistoryRail keeps displaying past data.
"""

import json
import uuid

import psycopg


def get_history_by_id(
    record_id: uuid.UUID, db_url: str
) -> dict[str, object] | None:
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, question, sql, answer_json, assumptions, caveats, "
            "lineage_json, token_usage, created_at, kind "
            "FROM query_history WHERE id = %s",
            (record_id,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        cols = [d.name for d in cur.description or []]
        return dict(zip(cols, row, strict=False))


def save_dashboard_audit(
    endpoint: str,
    params: dict[str, str],
    audit_id: uuid.UUID,
    db_url: str,
) -> None:
    """Audit-log a dashboard request in query_history."""
    canonical = "dashboard:" + endpoint + ":" + ":".join(
        f"{k}={v}" for k, v in sorted(params.items())
    )
    with psycopg.connect(db_url) as conn:
        conn.execute(
            "INSERT INTO query_history "
            "(id, question, sql, answer_json, assumptions, caveats,"
            " lineage_json, token_usage, kind) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                audit_id,
                canonical,
                "",
                json.dumps({}),
                json.dumps([]),
                json.dumps([]),
                json.dumps({}),
                json.dumps({}),
                "dashboard_audit",
            ),
        )


def get_history(
    limit: int, db_url: str, kind: str | None = None
) -> list[dict[str, object]]:
    """Return recent history entries.

    When ``kind`` is provided, results are filtered to that discriminator
    (e.g. ``"ask"``) so the chat HistoryRail can hide dashboard audit rows.
    """
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        if kind is None:
            cur.execute(
                "SELECT id, question, sql, created_at, kind "
                "FROM query_history ORDER BY created_at DESC LIMIT %s",
                (limit,),
            )
        else:
            cur.execute(
                "SELECT id, question, sql, created_at, kind "
                "FROM query_history WHERE kind = %s "
                "ORDER BY created_at DESC LIMIT %s",
                (kind, limit),
            )
        cols = [d.name for d in cur.description or []]
        return [
            dict(zip(cols, row, strict=False)) for row in cur.fetchall()
        ]
