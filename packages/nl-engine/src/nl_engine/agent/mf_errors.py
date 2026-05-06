"""MetricFlow error classification + hint extraction for `mf_query`
(HUG-190 Phase B).

Lifted out of `tools.py` to keep that file under the 300-line cap.
"""

from __future__ import annotations

import re

# Substring markers in a MetricFlow error message indicating the caller's
# args are wrong (column doesn't exist, dimension mismatch, join-path
# failure). Retrying identical args wastes step-cap budget; surface the
# error to the agent so it reads MetricFlow's "did you mean: [...]"
# hint and corrects on the next LLM call.
STRUCTURAL_MARKERS: tuple[str, ...] = (
    "does not match exactly one of the query items",
    "no valid join paths exist",
    "did you mean",
    "column does not exist",
    "column not found",
    "unknown metric",
    "validation error",
    "does not exist",
    "got error(s) during query resolution",
)

# Substring markers indicating a transient process / network failure
# worth one quick retry.
TRANSIENT_MARKERS: tuple[str, ...] = (
    "timed out",
    "timeout",
    "connection refused",
    "broken pipe",
    "resource temporarily unavailable",
    "exit -9",
    "exit 137",
)


def classify_mf_error(exc: Exception) -> str:
    """Return 'structural' or 'transient' based on the exception text.

    Default: 'structural'. We'd rather surface a possibly-fixable error
    to the agent than retry it 3 times and waste budget.
    """
    msg = str(exc).lower()
    for marker in TRANSIENT_MARKERS:
        if marker in msg:
            return "transient"
    return "structural"


def extract_mf_hint(msg: str) -> str | None:
    """Pull the suggestion list out of a MetricFlow error message so the
    agent sees it as a structured hint, not just free-form prose.

    MetricFlow surfaces these in two phrasings: 'did you mean: [...]'
    and 'with suggestions: [...]'.
    """
    match = re.search(
        r"(?:did you mean|with suggestions?)[^:]*:\s*(\[.*?\])",
        msg,
        re.IGNORECASE | re.DOTALL,
    )
    if match:
        return match.group(1)
    return None
