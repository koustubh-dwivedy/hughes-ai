import ast
from pathlib import Path

PACKAGES_ROOT = Path(__file__).parents[2] / "packages"

LAYER_RULES: dict[str, list[str]] = {
    "synth_data": ["nl_engine", "api"],
    "nl_engine": ["api"],
    "api": [],
}


def _get_imports(filepath: Path) -> list[str]:
    tree = ast.parse(filepath.read_text())
    result = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                result.append(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            result.append(node.module.split(".")[0])
    return result


def test_no_forbidden_imports() -> None:
    violations = []
    for package_name, forbidden in LAYER_RULES.items():
        src_dir = PACKAGES_ROOT / package_name.replace("_", "-") / "src" / package_name
        if not src_dir.exists():
            continue
        for py_file in src_dir.rglob("*.py"):
            if "__pycache__" in py_file.parts:
                continue
            for imp in _get_imports(py_file):
                if imp in forbidden:
                    violations.append(
                        f"{py_file.relative_to(PACKAGES_ROOT)}: "
                        f"'{package_name}' must not import from '{imp}'"
                    )
    assert not violations, "Import boundary violations:\n" + "\n".join(violations)


def test_no_circular_imports() -> None:
    graph: dict[str, set[str]] = {pkg: set() for pkg in LAYER_RULES}
    for package_name in LAYER_RULES:
        src_dir = PACKAGES_ROOT / package_name.replace("_", "-") / "src" / package_name
        if not src_dir.exists():
            continue
        for py_file in src_dir.rglob("*.py"):
            if "__pycache__" in py_file.parts:
                continue
            for imp in _get_imports(py_file):
                if imp in graph and imp != package_name:
                    graph[package_name].add(imp)

    cycles = []
    for pkg_a, deps in graph.items():
        for pkg_b in deps:
            if pkg_a in graph.get(pkg_b, set()):
                pair = tuple(sorted([pkg_a, pkg_b]))
                if pair not in [tuple(sorted(c)) for c in cycles]:
                    cycles.append([pkg_a, pkg_b])

    assert not cycles, "Circular imports: " + ", ".join(f"{a}↔{b}" for a, b in cycles)
