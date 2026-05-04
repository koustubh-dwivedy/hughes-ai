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


def list_metrics() -> list[MfMetric]:
    """Return the metric catalog as parsed from `mf list metrics`.

    Output line shape: `• metric_name: dim1, dim2 and N more`. We parse
    everything before " and N more" since the CLI truncates long
    dimension lists.
    """
    proc = _run(["list", "metrics"])
    metrics: list[MfMetric] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line.startswith("•"):
            continue
        body = line.lstrip("• ").strip()
        if ":" not in body:
            continue
        name, dims_text = body.split(":", 1)
        # Strip "and N more" tail
        dims_part = dims_text.strip()
        if " and " in dims_part:
            dims_part = dims_part.split(" and ")[0]
        dimensions = [d.strip() for d in dims_part.split(",") if d.strip()]
        metrics.append(MfMetric(name=name.strip(), dimensions=dimensions))
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
