"""Audit: every dimension/measure/entity expression in a semantic model
references a real column in the underlying ref()'d table (HUG-198).

Catches the class of bug where a semantic model declares a measure named
``ytd_loan_growth`` whose ``expr`` resolves to a column that doesn't exist
on the mart. Two such bugs (``event_month``, ``delinquency_bucket``,
``avg_balance``, ``ytd_loan_growth``, ``ytd_deposit_growth``) all silently
broke the LangGraph agent during HUG-190's eval — every retry hit the same
``column "X" does not exist`` error from Postgres.

Read-only: requires DATABASE_URL pointing at the seeded local Postgres.
Skipped if the DB isn't reachable (CI sets it via the postgres service).
"""
from __future__ import annotations

import os
import re
from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SEMANTIC_DIR = _REPO_ROOT / "packages" / "dbt-models" / "models" / "semantic"


def _connect():
    try:
        import psycopg2
    except ImportError:
        pytest.skip("psycopg2 not installed; skipping DB-backed audit")
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        pytest.skip("DATABASE_URL not set; skipping DB-backed audit")
    try:
        return psycopg2.connect(db_url)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Postgres not reachable ({exc}); skipping audit")


def _columns_for(cur, table: str) -> set[str]:
    cur.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = %s AND table_schema = 'public'",
        (table,),
    )
    return {r[0] for r in cur.fetchall()}


def _iter_field_exprs(sm: dict) -> Iterator[tuple[str, str, str]]:
    """Yield (kind, name, expr) for every entity/dimension/measure with an
    expr (or implicit expr equal to its name)."""
    for kind in ("entities", "dimensions", "measures"):
        for field in sm.get(kind) or []:
            expr = field.get("expr") or field["name"]
            yield kind.rstrip("s"), field["name"], expr


def test_semantic_model_exprs_resolve_to_real_columns() -> None:
    conn = _connect()
    cur = conn.cursor()
    problems: list[str] = []
    for path in sorted(_SEMANTIC_DIR.glob("*.yml")):
        doc = yaml.safe_load(path.read_text())
        for sm in (doc.get("semantic_models") or []):
            ref_match = re.search(r"ref\(['\"](\w+)['\"]\)", sm.get("model", ""))
            if not ref_match:
                continue
            table = ref_match.group(1)
            cols = _columns_for(cur, table)
            if not cols:
                problems.append(
                    f"{path.name}::{sm['name']}: underlying table "
                    f"{table!r} has no columns (table missing or empty)"
                )
                continue
            for kind, name, expr in _iter_field_exprs(sm):
                # Strip the most common cast suffix (e.g., ``is_core::TEXT``).
                base = expr.split("::", 1)[0].strip()
                # Only check bare-identifier exprs — skip composite SQL
                # expressions like ``date_trunc('month', x)`` (those are
                # validated by MetricFlow at query time anyway).
                if not re.match(r"^\w+$", base):
                    continue
                if base not in cols:
                    problems.append(
                        f"{path.name}::{sm['name']}.{kind}.{name} "
                        f"expr={expr!r} not in {table} "
                        f"(table cols: {sorted(cols)})"
                    )
    conn.close()
    assert not problems, (
        "Semantic-model column drift detected (HUG-198 class of bug):\n  - "
        + "\n  - ".join(problems)
    )
