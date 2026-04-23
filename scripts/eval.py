"""Thin wrapper so `make eval` and CI both resolve to the benchmark runner."""

import sys
from pathlib import Path

benchmarks_dir = Path(__file__).parent.parent / "packages" / "nl-engine" / "benchmarks"
sys.path.insert(0, str(benchmarks_dir))

import run_eval  # noqa: E402

run_eval.main()
