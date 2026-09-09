"""AST-based detection of stub implementations and unresolved TODOs.

Only `stubs` gates: main() exits 1 when a function body is nothing but
`pass` or `raise NotImplementedError`, which regex-based scanning cannot
tell apart from a legitimate `pass` inside a branch. `todos` is reported
for the evidence artifact and does not fail the run.

Removed in the 2026-09-02 checker review, deliberately and not because it
was failing: an `UnusedDetector` that re-implemented Ruff's F401 (which is
selected in pyproject.toml and *does* block the gate) while itself only
ever incrementing an advisory warning counter, and a `ComplexityAnalyzer`
whose numbers had no threshold and no consumer anywhere in the repository.
Neither could turn the gate red, so neither is missed by deleting it.
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from operations.scripts.quality.scope import PYTHON_QUALITY_PATHS


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

        # A docstring is metadata, not an implementation.  Ignore it before
        # deciding whether the executable body is only a stub marker.
        body = node.body
        if body and isinstance(body[0], ast.Expr):
            value = body[0].value
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                body = body[1:]

        # Check if executable body is just pass or either spelling of
        # raise NotImplementedError.
        if len(body) == 1:
            stmt = body[0]
            if isinstance(stmt, ast.Pass):
                self.stubs.append(
                    {
                        "type": "pass_only",
                        "function": node.name,
                        "line": node.lineno,
                        "severity": "high",
                    }
                )
            elif isinstance(stmt, ast.Raise) and self._raises_not_implemented(stmt):
                self.stubs.append(
                    {
                        "type": "not_implemented",
                        "function": node.name,
                        "line": node.lineno,
                        "severity": "high",
                    }
                )

    @staticmethod
    def _raises_not_implemented(stmt: ast.Raise) -> bool:
        exception = stmt.exc
        if isinstance(exception, ast.Name):
            return exception.id == "NotImplementedError"
        return (
            isinstance(exception, ast.Call)
            and isinstance(exception.func, ast.Name)
            and exception.func.id == "NotImplementedError"
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

    return {
        "filepath": str(filepath),
        "stubs": stub_detector.stubs,
        "todos": stub_detector.todos,
    }


def main() -> int:
    """Analyze every Python file in the canonical quality scope."""
    root = Path.cwd()
    scope_dirs = [root / relative for relative in PYTHON_QUALITY_PATHS]

    missing = [str(path.relative_to(root)) for path in scope_dirs if not path.exists()]
    if missing:
        print(f"Error: quality scope paths not found: {', '.join(missing)}", file=sys.stderr)
        return 1

    all_findings: list[dict[str, Any]] = []
    critical_count = 0
    warning_count = 0

    for python_file in [path for directory in scope_dirs for path in directory.rglob("*.py")]:
        findings = analyze_file(python_file)
        all_findings.append(findings)

        # Count issues
        if "error" not in findings:
            critical_count += len([s for s in findings["stubs"] if s.get("severity") == "high"])
            warning_count += len([s for s in findings["stubs"] if s.get("severity") == "medium"])

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
