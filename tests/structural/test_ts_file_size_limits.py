from pathlib import Path

FRONTEND_SRC = Path(__file__).parents[2] / "packages" / "frontend" / "src"
MAX_FILE_LINES = 300
_EXCLUDE = {"vite-env.d.ts"}


def _ts_files() -> list[Path]:
    return [
        p
        for p in FRONTEND_SRC.rglob("*")
        if p.suffix in {".ts", ".tsx"} and p.name not in _EXCLUDE
    ]


def _check_lines(files: list[Path]) -> list[str]:
    violations = []
    for f in files:
        count = len(f.read_text().splitlines())
        if count > MAX_FILE_LINES:
            try:
                rel = f.relative_to(FRONTEND_SRC.parent.parent)
            except ValueError:
                rel = f.name  # fallback for tmp_path fixtures
            violations.append(f"{rel}: {count} lines (max {MAX_FILE_LINES})")
    return violations


def test_ts_file_line_limits() -> None:
    violations = _check_lines(_ts_files())
    assert not violations, "TS file too long:\n" + "\n".join(violations)


def test_ts_file_limit_check_catches_violation(tmp_path: Path) -> None:
    long_file = tmp_path / "too_long.tsx"
    long_file.write_text("x\n" * 301)  # 301 lines > MAX_FILE_LINES
    violations = _check_lines([long_file])
    assert violations, "Validator must flag a 301-line file"
    assert "301 lines" in violations[0]
