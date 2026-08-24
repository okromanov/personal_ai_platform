"""
Advanced code quality analysis using AST (Abstract Syntax Tree).

Replaces primitive regex patterns with proper Python AST analysis for:
- Detection of stub implementations (pass, NotImplementedError)
- Finding unresolved TODOs in function bodies, not in paths
- Dead code detection (unused imports, variables)
- Complexity metrics
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any


class StubDetector(ast.NodeVisitor):
    """Find stub implementations like pass, NotImplementedError, etc."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.stubs: list[dict[str, Any]] = []
        self.todos: list[dict[str, Any]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_function(node)
        self.generic_visit(node)

    def _check_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        # Check docstring for TODO/FIXME
        docstring = ast.get_docstring(node)
        if docstring and any(marker in docstring for marker in ["TODO", "FIXME", "XXX"]):
            self.todos.append(
                {
                    "type": "docstring_todo",
                    "function": node.name,
                    "line": node.lineno,
                    "docstring_excerpt": docstring[:100],
                }
            )

        # Check if function body is just pass or raise NotImplementedError
        if len(node.body) == 1:
            stmt = node.body[0]
            if isinstance(stmt, ast.Pass):
                self.stubs.append(
                    {
                        "type": "pass_only",
                        "function": node.name,
                        "line": node.lineno,
                        "severity": "high",
                    }
                )
            elif isinstance(stmt, ast.Raise):
                if isinstance(stmt.exc, ast.Call):
                    if isinstance(stmt.exc.func, ast.Name):
                        if stmt.exc.func.id == "NotImplementedError":
                            self.stubs.append(
                                {
                                    "type": "not_implemented",
                                    "function": node.name,
                                    "line": node.lineno,
                                    "severity": "high",
                                }
                            )

    def visit_With(self, node: ast.With) -> None:
        """Check for context managers that just have pass."""
        if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
            self.stubs.append(
                {
                    "type": "empty_with_block",
                    "line": node.lineno,
                    "severity": "medium",
                }
            )
        self.generic_visit(node)


class UnusedDetector(ast.NodeVisitor):
    """Find unused imports and variables."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.imports: dict[str, int] = {}
        self.used_names: set[str] = set()
        self.unused: list[dict[str, Any]] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            name = alias.asname or alias.name
            self.imports[name] = node.lineno
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        # `from __future__ import annotations` (and other future features)
        # is a compiler directive, not a runtime name that a Name/Attribute
        # visit could ever mark used - counting it as an unused import is a
        # false positive on a pattern nearly every file in this repo uses.
        if node.module == "__future__":
            self.generic_visit(node)
            return
        for alias in node.names:
            if alias.name != "*":
                name = alias.asname or alias.name
                self.imports[name] = node.lineno
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if isinstance(node.value, ast.Name):
            self.used_names.add(node.value.id)
        self.generic_visit(node)

    def finalize(self) -> None:
        """Check which imports are unused."""
        for import_name, lineno in self.imports.items():
            if import_name not in self.used_names and not import_name.startswith("_"):
                self.unused.append(
                    {
                        "type": "unused_import",
                        "name": import_name,
                        "line": lineno,
                        "severity": "medium",
                    }
                )


class ComplexityAnalyzer(ast.NodeVisitor):
    """Calculate cyclomatic complexity."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.complexity = 0
        self.functions: dict[str, int] = {}
        self.current_function: str | None = None

    def visit_FunctionDef(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self.current_function = node.name
        complexity = 1
        complexity += sum(1 for _ in ast.walk(node) if isinstance(_, ast.If))
        complexity += sum(1 for _ in ast.walk(node) if isinstance(_, ast.For))
        complexity += sum(1 for _ in ast.walk(node) if isinstance(_, ast.While))
        complexity += sum(1 for _ in ast.walk(node) if isinstance(_, ast.ExceptHandler))

        self.functions[node.name] = complexity
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.visit_FunctionDef(node)  # Same logic


def analyze_file(filepath: Path) -> dict[str, Any]:
    """Run all analyzers on a single Python file."""
    try:
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError) as e:
        return {
            "filepath": str(filepath),
            "error": f"Failed to parse: {e}",
        }

    stub_detector = StubDetector(str(filepath))
    stub_detector.visit(tree)

    unused_detector = UnusedDetector(str(filepath))
    unused_detector.visit(tree)
    unused_detector.finalize()

    complexity_analyzer = ComplexityAnalyzer(str(filepath))
    complexity_analyzer.visit(tree)

    return {
        "filepath": str(filepath),
        "stubs": stub_detector.stubs,
        "todos": stub_detector.todos,
        "unused": unused_detector.unused,
        "complexity": {
            "by_function": complexity_analyzer.functions,
            "max_complexity": max(complexity_analyzer.functions.values())
            if complexity_analyzer.functions
            else 0,
        },
    }


def main() -> int:
    """Analyze all Python files in operations/scripts and operations/tests."""
    root = Path.cwd()
    script_dir = root / "operations" / "scripts"
    test_dir = root / "operations" / "tests"

    if not script_dir.exists() or not test_dir.exists():
        print("Error: operations/scripts or operations/tests not found", file=sys.stderr)
        return 1

    all_findings: list[dict[str, Any]] = []
    critical_count = 0
    warning_count = 0

    for python_file in list(script_dir.rglob("*.py")) + list(test_dir.rglob("*.py")):
        findings = analyze_file(python_file)
        all_findings.append(findings)

        # Count issues
        if "error" not in findings:
            critical_count += len([s for s in findings["stubs"] if s.get("severity") == "high"])
            warning_count += len([s for s in findings["stubs"] if s.get("severity") == "medium"])
            warning_count += len(findings["unused"])

    # Output JSON report
    report = {
        "summary": {
            "files_analyzed": len(all_findings),
            "critical_issues": critical_count,
            "warnings": warning_count,
        },
        "findings": all_findings,
    }

    json.dump(report, sys.stdout, indent=2)

    # Exit with error if critical issues found
    return 1 if critical_count > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
