"""Append-only query history repository."""

import json
import uuid

import psycopg
from nl_engine.engine import AnswerResponse


def save_query(
    question: str,
    result: AnswerResponse,
    request_id: str,
    db_url: str,
) -> uuid.UUID:
    record_id = uuid.UUID(request_id)
    with psycopg.connect(db_url) as conn:
        conn.execute(
            "INSERT INTO query_history "
            "(id, question, sql, answer_json, assumptions, caveats,"
            " lineage_json, token_usage) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                record_id,
                question,
                result.sql,
                json.dumps(
                    {
                        "rows": result.rows,
                        "columns": result.columns,
                        "explanation": result.explanation,
                    }
                ),
                json.dumps(result.assumptions),
                json.dumps(result.caveats),
                json.dumps({"tables_used": result.tables_used}),
                json.dumps({}),
            ),
        )
    return record_id


def get_history_by_id(
    record_id: uuid.UUID, db_url: str
) -> dict[str, object] | None:
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, question, sql, answer_json, assumptions, caveats, "
            "lineage_json, token_usage, created_at "
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
            " lineage_json, token_usage) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                audit_id,
                canonical,
                "",
                json.dumps({}),
                json.dumps([]),
                json.dumps([]),
                json.dumps({}),
                json.dumps({}),
            ),
        )


def get_history(limit: int, db_url: str) -> list[dict[str, object]]:
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, question, sql, created_at "
            "FROM query_history ORDER BY created_at DESC LIMIT %s",
            (limit,),
        )
        cols = [d.name for d in cur.description or []]
        return [
            dict(zip(cols, row, strict=False)) for row in cur.fetchall()
        ]
