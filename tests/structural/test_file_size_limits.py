import ast
from pathlib import Path

PACKAGES_ROOT = Path(__file__).parents[2] / "packages"
MAX_FILE_LINES = 300
MAX_FUNCTION_LINES = 50


def _py_files() -> list[Path]:
    return [
        p for p in PACKAGES_ROOT.rglob("*.py")
        if "__pycache__" not in p.parts
    ]


def test_file_line_limits() -> None:
    violations = []
    for py_file in _py_files():
        count = len(py_file.read_text().splitlines())
        if count > MAX_FILE_LINES:
            violations.append(
                f"{py_file.relative_to(PACKAGES_ROOT)}: {count} lines (max {MAX_FILE_LINES})"
            )
    assert not violations, "File too long:\n" + "\n".join(violations)


def test_function_line_limits() -> None:
    violations = []
    for py_file in _py_files():
        tree = ast.parse(py_file.read_text())
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.end_lineno and node.lineno:
                    length = node.end_lineno - node.lineno + 1
                    if length > MAX_FUNCTION_LINES:
                        violations.append(
                            f"{py_file.relative_to(PACKAGES_ROOT)}:{node.lineno}: "
                            f"'{node.name}' is {length} lines (max {MAX_FUNCTION_LINES})"
                        )
    assert not violations, "Function too long:\n" + "\n".join(violations)
