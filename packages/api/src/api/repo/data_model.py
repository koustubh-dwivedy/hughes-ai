"""Read-only loaders for the Data Model lineage endpoints.

Sources of truth:
- packages/dbt-models/target/manifest.json (lineage + SQL + materialization)
- packages/api/src/api/repo/data_model_dashboards.yaml (dashboard → marts)
- packages/dbt-models/target/run_results.json (last-run timestamps; optional)
- query_history table (NL-query usage counts per table; last 30d)
"""

from __future__ import annotations

import json
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import psycopg
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[5]
_DBT_TARGET = _REPO_ROOT / "packages" / "dbt-models" / "target"
MANIFEST_PATH = _DBT_TARGET / "manifest.json"
RUN_RESULTS_PATH = _DBT_TARGET / "run_results.json"
DASHBOARDS_YAML_PATH = Path(__file__).with_name("data_model_dashboards.yaml")


@lru_cache(maxsize=8)
def _load_json_cached(path_str: str, mtime_ns: int) -> dict[str, Any]:
    """Cache parsed JSON keyed by (path, mtime) so a regenerated file invalidates."""
    del mtime_ns  # used only for cache keying
    with open(path_str) as fh:
        data: dict[str, Any] = json.load(fh)
    return data


def load_manifest(path: Path = MANIFEST_PATH) -> dict[str, Any]:
    """Load packages/dbt-models/target/manifest.json. Auto-refreshes on file change."""
    if not path.exists():
        raise FileNotFoundError(
            f"dbt manifest not found at {path}. Run `dbt parse` (or `make dbt-build`)."
        )
    return _load_json_cached(str(path), path.stat().st_mtime_ns)


def load_run_results(path: Path = RUN_RESULTS_PATH) -> dict[str, datetime]:
    """Map unique_id -> completed_at from dbt run_results.json. Empty if absent."""
    if not path.exists():
        return {}
    raw = _load_json_cached(str(path), path.stat().st_mtime_ns)
    out: dict[str, datetime] = {}
    for r in raw.get("results", []):
        uid = r.get("unique_id")
        ts_str = (r.get("timing") or [{}])[-1].get("completed_at")
        if uid and ts_str:
            try:
                out[uid] = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            except ValueError:
                continue
    return out


@lru_cache(maxsize=2)
def _load_dashboards_cached(path_str: str, mtime_ns: int) -> dict[str, Any]:
    del mtime_ns
    with open(path_str) as fh:
        data: dict[str, Any] = yaml.safe_load(fh) or {}
    return data


def load_dashboard_mapping(
    path: Path = DASHBOARDS_YAML_PATH,
) -> list[dict[str, Any]]:
    """Return the list of dashboard entries from data_model_dashboards.yaml."""
    raw = _load_dashboards_cached(str(path), path.stat().st_mtime_ns)
    entries = raw.get("dashboards", []) if isinstance(raw, dict) else []
    return [dict(e) for e in entries]


# ── NL usage counts ───────────────────────────────────────────────────────────


def _fetch_nl_lineage_rows(db_url: str, days: int) -> list[list[str]]:
    """Return one list-of-table-names per recent NL ask query in last `days` days."""
    sql = (
        "SELECT lineage_json::text "
        "FROM query_history "
        "WHERE kind = 'ask' "
        "AND created_at >= now() - (%s || ' days')::interval"
    )
    with psycopg.connect(db_url) as conn, conn.cursor() as cur:
        cur.execute(sql, (str(days),))
        rows = cur.fetchall()
    out: list[list[str]] = []
    for (raw,) in rows:
        try:
            payload = json.loads(raw) if isinstance(raw, str) else raw
        except (TypeError, json.JSONDecodeError):
            continue
        tables = payload.get("tables_used") if isinstance(payload, dict) else None
        if isinstance(tables, list):
            out.append([t for t in tables if isinstance(t, str)])
    return out


def aggregate_nl_counts(query_lineages: list[list[str]]) -> dict[str, int]:
    """Pure: for each table, count distinct queries that referenced it."""
    counts: dict[str, int] = {}
    for tables in query_lineages:
        for t in set(tables):  # one per query, not per occurrence
            counts[t] = counts.get(t, 0) + 1
    return counts


def count_nl_queries_per_table(db_url: str, days: int = 30) -> dict[str, int]:
    """Count distinct NL queries (last `days` days) that referenced each table name."""
    return aggregate_nl_counts(_fetch_nl_lineage_rows(db_url, days))
