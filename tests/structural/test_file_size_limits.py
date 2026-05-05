import ast
from pathlib import Path

PACKAGES_ROOT = Path(__file__).parents[2] / "packages"
MAX_FILE_LINES = 300
MAX_FUNCTION_LINES = 50


_EXCLUDED_DIRS = frozenset({"__pycache__", "node_modules"})


def _py_files() -> list[Path]:
    return [
        p for p in PACKAGES_ROOT.rglob("*.py")
        if not (_EXCLUDED_DIRS & set(p.parts))
    ]


def test_file_line_limits() -> None:
    violations = []
    for py_file in _py_files():
        count = len(py_file.read_text().splitlines())
        if count > MAX_FILE_LINES:
            rel = py_file.relative_to(PACKAGES_ROOT)
            violations.append(f"{rel}: {count} lines (max {MAX_FILE_LINES})")
    assert not violations, "File too long:\n" + "\n".join(violations)


def test_function_line_limits() -> None:
    violations = []
    for py_file in _py_files():
        tree = ast.parse(py_file.read_text())
        for node in ast.walk(tree):
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.end_lineno
                and node.lineno
            ):
                length = node.end_lineno - node.lineno + 1
                if length > MAX_FUNCTION_LINES:
                    rel = py_file.relative_to(PACKAGES_ROOT)
                    msg = f"'{node.name}' is {length} lines (max {MAX_FUNCTION_LINES})"
                    violations.append(f"{rel}:{node.lineno}: {msg}")
    assert not violations, "Function too long:\n" + "\n".join(violations)
