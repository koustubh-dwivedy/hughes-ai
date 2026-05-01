import re
from pathlib import Path

SRC = Path("packages/frontend/src")


def _feature_imports(feature_name: str) -> list[tuple[str, str]]:
    """Return (file, line) for any cross-feature imports inside a feature dir."""
    violations = []
    feature_dir = SRC / "features" / feature_name
    for f in feature_dir.rglob("*.tsx"):
        for line in f.read_text().splitlines():
            m = re.search(r'from\s+["\']([^"\']*features/([\w-]+))["\']', line)
            if m and m.group(2) != feature_name:
                violations.append((str(f), line.strip()))
    return violations


def test_features_do_not_cross_import() -> None:
    features = SRC / "features"
    if not features.exists():
        return
    all_violations: list[tuple[str, str]] = []
    for feature_dir in features.iterdir():
        if not feature_dir.is_dir():
            continue
        all_violations.extend(_feature_imports(feature_dir.name))
    assert not all_violations, (
        "Cross-feature imports are forbidden:\n"
        + "\n".join(f"  {f}: {line}" for f, line in all_violations)
    )
