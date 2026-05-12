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


def _docstring_lines(node: ast.AST) -> int:
    """Return the line count of a function's leading docstring, or 0 if
    none. Docstrings on @tool functions in the agent are production
    prompts (ADR-0006); they must not count against the function-size
    cap, which is intended to police code logic."""
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return 0
    body = node.body
    if not body:
        return 0
    first = body[0]
    if (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str)
        and first.end_lineno is not None
        and first.lineno is not None
    ):
        return first.end_lineno - first.lineno + 1
    return 0


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
                total = node.end_lineno - node.lineno + 1
                length = total - _docstring_lines(node)
                if length > MAX_FUNCTION_LINES:
                    rel = py_file.relative_to(PACKAGES_ROOT)
                    msg = (
                        f"'{node.name}' is {length} code lines "
                        f"(max {MAX_FUNCTION_LINES}; docstring excluded)"
                    )
                    violations.append(f"{rel}:{node.lineno}: {msg}")
    assert not violations, "Function too long:\n" + "\n".join(violations)
