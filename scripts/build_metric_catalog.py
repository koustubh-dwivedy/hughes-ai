"""Pre-compute the MetricFlow catalog at image build time (HUG-260).

Runs the 65 `mf` subprocess calls that `nl_engine.repo.metricflow.list_metrics()`
would otherwise run on the first agent request. Writes the result to
`packages/dbt-models/target/metric_catalog.json` for the runtime to read in
microseconds. Eliminates the ~4-min cold start that was 502'ing every first
chat through Firebase Hosting's 60s rewrite ceiling.

Idempotent: re-running just rewrites the JSON.

Build-context expectation: the dbt manifest must exist at
`packages/dbt-models/target/semantic_manifest.json` (produced by `dbt parse`
earlier in the Dockerfile). Without it the `mf` CLI exits non-zero and this
script fails — by design; it'd be worse to ship a stale catalog.
"""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

# Import the workspace member by relative path resolution.
_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "packages" / "nl-engine" / "src"))

from nl_engine.repo.metricflow import (  # noqa: E402
    _CATALOG_CACHE_FILE,
    _compute_catalog_via_subprocess,
)


def main() -> int:
    print(f"Computing MetricFlow catalog → {_CATALOG_CACHE_FILE}", flush=True)
    metrics = _compute_catalog_via_subprocess()
    payload = [dataclasses.asdict(m) for m in metrics]
    _CATALOG_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _CATALOG_CACHE_FILE.write_text(json.dumps(payload, indent=2, sort_keys=True))
    print(
        f"Wrote {len(metrics)} metrics ({_CATALOG_CACHE_FILE.stat().st_size} bytes) "
        f"to {_CATALOG_CACHE_FILE}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
