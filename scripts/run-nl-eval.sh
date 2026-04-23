#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
make seed
uv run python scripts/eval.py --fail-under "${1:-85}"
