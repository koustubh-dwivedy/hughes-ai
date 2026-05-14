"""Per-package coverage gate (HUG-234).

Reads `tests/coverage_baselines.toml`, compares each package's
measured coverage to its baseline, fails (exit 1) if any drops more
than `tolerance_pp` percentage points below baseline.

Usage:
    python scripts/check_coverage.py \
        --xml coverage.xml \
        --vitest-json packages/frontend/coverage/coverage-summary.json

Either source can be omitted; missing sources are skipped (a CI
job that didn't run frontend tests just doesn't grade frontend).
"""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_BASELINES = _REPO / "tests" / "coverage_baselines.toml"


def _load_baselines() -> tuple[dict[str, int], int]:
    data = tomllib.loads(_BASELINES.read_text())
    return data["baselines"], data["thresholds"]["tolerance_pp"]


def _python_coverage_pct(xml_path: Path) -> dict[str, float]:
    """Parse coverage.py's XML output, split api vs nl-engine.

    coverage.xml has one <package> per source root. We map by the
    `name` attribute which is the dotted package path.
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()
    by_pkg: dict[str, tuple[int, int]] = {"api": (0, 0), "nl-engine": (0, 0)}
    for cls in root.iter("class"):
        filename = cls.attrib.get("filename", "")
        is_api = (
            "/api/src/api/" in filename or filename.startswith("api/")
        )
        is_nle = (
            "/nl-engine/src/nl_engine/" in filename
            or filename.startswith("nl_engine/")
        )
        if is_api:
            key = "api"
        elif is_nle:
            key = "nl-engine"
        else:
            continue
        for line in cls.iter("line"):
            covered = int(line.attrib.get("hits", "0")) > 0
            tot, cov = by_pkg[key]
            by_pkg[key] = (tot + 1, cov + (1 if covered else 0))
    out: dict[str, float] = {}
    for k, (tot, cov) in by_pkg.items():
        if tot:
            out[k] = round(100.0 * cov / tot, 2)
    return out


def _vitest_coverage_pct(json_path: Path) -> dict[str, float]:
    """Vitest --coverage with `json-summary` writes coverage-summary.json
    where `total.lines.pct` is the overall percent."""
    data = json.loads(json_path.read_text())
    pct = data.get("total", {}).get("lines", {}).get("pct")
    if pct is None:
        return {}
    return {"frontend": round(float(pct), 2)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--xml", type=Path, help="coverage.py XML report")
    parser.add_argument(
        "--vitest-json", type=Path, help="vitest coverage-summary.json"
    )
    args = parser.parse_args()

    baselines, tolerance = _load_baselines()
    measured: dict[str, float] = {}
    if args.xml and args.xml.exists():
        measured.update(_python_coverage_pct(args.xml))
    if args.vitest_json and args.vitest_json.exists():
        measured.update(_vitest_coverage_pct(args.vitest_json))

    if not measured:
        print("⚠️  No coverage reports provided / found; skipping check.")
        return 0

    failed: list[str] = []
    print(f"{'Package':<12} {'Measured':>10} {'Baseline':>10} {'Floor':>8}")
    for pkg, baseline in baselines.items():
        m = measured.get(pkg)
        if m is None:
            continue
        floor = baseline - tolerance
        status = "ok" if m >= floor else "FAIL"
        print(f"{pkg:<12} {m:>9.2f}% {baseline:>9d}% {floor:>7d}%  {status}")
        if m < floor:
            failed.append(
                f"  {pkg}: measured {m:.2f}% < floor {floor}% "
                f"(baseline {baseline}% − {tolerance}pp tolerance). "
                f"Raise the baseline in tests/coverage_baselines.toml or add tests."
            )

    if failed:
        print("\n❌ Coverage gate failed:")
        for line in failed:
            print(line)
        return 1
    print("\n✅ Coverage gate passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
