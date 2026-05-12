"""Thin Python wrapper around the dbt MetricFlow `mf` CLI (HUG-174).

The conversational agent (HUG-176) calls `query()` with structured args
instead of generating SQL. Catalog (`list_metrics()`) is cached at API
startup and refreshed on demand.
"""

from __future__ import annotations

import csv
import json
import logging
import shutil
import subprocess  # nosec B404 — `mf` CLI is the documented integration path
import tempfile
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[5]
_DBT_PROJECT_DIR = _REPO_ROOT / "packages" / "dbt-models"


@dataclass
class MfMetric:
    name: str
    dimensions: list[str] = field(default_factory=list)


@dataclass
class MfQueryResult:
    metric: str
    dimensions: list[str]
    rows: list[dict[str, Any]]


class MetricFlowError(RuntimeError):
    """Raised when `mf` returns a non-zero exit or unparseable output."""


def _mf_command() -> str:
    """Return the path to the `mf` binary that the parent process can exec.

    Resolves uv-installed CLI; falls back to PATH. When called outside a
    uv-managed venv we still try the bare `mf` so docker / CI workflows
    work uniformly.
    """
    candidate = shutil.which("mf")
    if candidate:
        return candidate
    raise MetricFlowError(
        "`mf` CLI not found on PATH. Install with `uv add dbt-metricflow`."
    )


def _run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run `mf` with the given args. Raises MetricFlowError on non-zero exit."""
    cmd = [_mf_command(), *args]
    proc = subprocess.run(  # noqa: S603  # nosec B603 — mf path resolved, args typed
        cmd,
        cwd=str(cwd or _DBT_PROJECT_DIR),
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if proc.returncode != 0:
        raise MetricFlowError(
            f"`mf {' '.join(args)}` failed (exit {proc.returncode}):\n"
            f"stdout: {proc.stdout[-1000:]}\nstderr: {proc.stderr[-1000:]}"
        )
    return proc


def _parse_metric_names() -> list[str]:
    """Return just the names from `mf list metrics`.

    The output's per-metric dimension list is truncated by the CLI
    ("and N more") at 5 entries, so we only consume the names here and
    fetch each metric's full dimension set via `mf list dimensions
    --metrics <name>` (which is NOT truncated).
    """
    proc = _run(["list", "metrics"])
    names: list[str] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line.startswith("•"):
            continue
        body = line.lstrip("• ").strip()
        if ":" not in body:
            continue
        name, _ = body.split(":", 1)
        names.append(name.strip())
    return names


def _list_dimensions_for(metric: str) -> list[str]:
    proc = _run(["list", "dimensions", "--metrics", metric])
    dims: list[str] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line.startswith("•"):
            continue
        dims.append(line.lstrip("• ").strip())
    return dims


def _list_entities_for(metric: str) -> list[str]:
    """Return the foreign entities a metric can be sliced by.

    `mf list dimensions` does NOT enumerate entities, so for ratio
    metrics with shared foreign entities (e.g., `delinquency_rate`
    sliceable by `product_type`), the agent never sees them as group-by
    candidates. This helper bridges that gap.
    """
    proc = _run(["list", "entities", "--metrics", metric])
    entities: list[str] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line.startswith("•"):
            continue
        body = line.lstrip("• ").strip()
        if not body:
            continue
        entities.append(body.split()[0])
    return entities


@lru_cache(maxsize=1)
def list_metrics() -> list[MfMetric]:
    """Return the metric catalog with each metric's FULL group-by surface.

    PROCESS-LEVEL CACHED (`lru_cache`, size 1). The first call within a
    process pays the full ~65-subprocess cost (~3-4 minutes on the
    32-metric catalog); subsequent calls return the cached catalog in
    microseconds. Safe because every eval invocation runs in a fresh
    Python process and we don't hot-reload semantic models within a
    process. Saves ~96 minutes per 24-question must-pass eval.

    Production note (long-running API workers): the cache lives for the
    worker lifetime. A redeploy / process restart clears it. If you
    ever need a mid-process hot reload, call
    `list_metrics.cache_clear()` (tests do this between cases via an
    autouse fixture in `test_metricflow_list_entities.py`).

    Built in three passes per metric:
      1. `mf list metrics` for names (CLI truncates dim lists with "and
         N more", so we discard its dim suffix).
      2. `mf list dimensions --metrics <name>` for the full dimension
         list (not truncated).
      3. `mf list entities --metrics <name>` for foreign entities,
         which `list dimensions` does not enumerate. Without this the
         agent cannot see e.g. `product_type` as a slice for
         `delinquency_rate`.

    Both helpers fall back to empty on `MetricFlowError` with a
    structured log entry.
    """
    names = _parse_metric_names()
    metrics: list[MfMetric] = []
    for name in names:
        try:
            dims = _list_dimensions_for(name)
        except MetricFlowError:
            log.exception("list_dimensions failed for metric %s", name)
            dims = []
        try:
            ents = _list_entities_for(name)
        except MetricFlowError:
            log.exception("list_entities failed for metric %s", name)
            ents = []
        combined = sorted(set(dims) | set(ents))
        metrics.append(MfMetric(name=name, dimensions=combined))
    return metrics


def query(
    metric: str,
    dimensions: list[str] | None = None,
    where: str | None = None,
    order: str | None = None,
    limit: int = 100,
) -> MfQueryResult:
    """Run a MetricFlow query, parse the CSV output, return rows as dicts.

    `where` is a SQL fragment (MetricFlow's accepted syntax — typically
    `{{ Dimension('semantic_model__dimension') }} = 'value'`). Click's
    --csv flag refuses /dev/stdout; we write to a tempfile then read it.
    """
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        csv_path = Path(tmp.name)
    try:
        args = [
            "query", "--metrics", metric,
            "--csv", str(csv_path), "--limit", str(limit),
        ]
        if dimensions:
            args.extend(["--group-by", ",".join(dimensions)])
        if where:
            args.extend(["--where", where])
        if order:
            args.extend(["--order", order])
        _run(args)
        rows = _parse_csv_file(csv_path)
    finally:
        csv_path.unlink(missing_ok=True)
    return MfQueryResult(metric=metric, dimensions=dimensions or [], rows=rows)


def _parse_csv_file(path: Path) -> list[dict[str, Any]]:
    """Read MetricFlow's CSV output, returning rows as dicts."""
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open() as fh:
        reader = csv.DictReader(fh)
        return [dict(r) for r in reader]


def query_to_json(
    metric: str,
    dimensions: list[str] | None = None,
    where: str | None = None,
    order: str | None = None,
    limit: int = 100,
) -> str:
    """Convenience wrapper returning a JSON string (for tool-call results)."""
    result = query(metric, dimensions, where, order, limit)
    return json.dumps(
        {
            "metric": result.metric,
            "dimensions": result.dimensions,
            "rows": result.rows,
        },
        default=str,
    )
