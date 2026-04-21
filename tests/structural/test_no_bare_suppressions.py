import re
from pathlib import Path

PACKAGES_ROOT = Path(__file__).parents[2] / "packages"

_BARE_TYPE_IGNORE = re.compile(r"#\s*type:\s*ignore\s*$")
_BARE_NOQA = re.compile(r"#\s*noqa\s*$")


def test_no_bare_suppressions() -> None:
    violations = []
    for py_file in PACKAGES_ROOT.rglob("*.py"):
        if "__pycache__" in py_file.parts:
            continue
        for i, line in enumerate(py_file.read_text().splitlines(), 1):
            if _BARE_TYPE_IGNORE.search(line):
                violations.append(
                    f"{py_file.relative_to(PACKAGES_ROOT)}:{i}: "
                    "bare '# type: ignore' — add reason, e.g. '# type: ignore[assignment]  # reason'"
                )
            elif _BARE_NOQA.search(line):
                violations.append(
                    f"{py_file.relative_to(PACKAGES_ROOT)}:{i}: "
                    "bare '# noqa' — add rule and reason, e.g. '# noqa: E501  # reason'"
                )
    assert not violations, "Bare suppressions:\n" + "\n".join(violations)
