from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from operations.scripts.quality.check_coverage import evaluate_coverage, load_policy


@dataclass
class RepositoryMetrics:
    """Repository health metrics."""

    total_commits: int
    python_files: int
    lines_of_code: int
    git_size_kb: int
    project_size_mb: float
    branches: list[str]
    remote_url: str
    last_commits: list[str]
    working_tree_clean: bool


@dataclass
class TestMetrics:
    """Test execution metrics."""

    total_passed: int
    total_failed: int
    execution_time_sec: float
    coverage_percent: float


@dataclass
class CodeQualityMetrics:
    """Code quality metrics."""

    mypy_issues: int
    ruff_issues: int
    formatting_compliant: bool
    type_safe: bool


@dataclass
class CoveragePolicyMetrics:
    """Compliance with the tiered coverage gate defined in pyproject.toml.

    Mirrors check_coverage.py's own evaluate_coverage() rather than
    re-implementing the overall/critical-module thresholds, so this can
    never silently diverge from the gate that actually blocks CI (unlike a
    hardcoded percentage floor).
    """

    rows: list[str]
    errors: list[str]
    passed: bool


@dataclass
class RepositoryHealth:
    """Overall repository health status."""

    repository: RepositoryMetrics
    tests: TestMetrics
    code_quality: CodeQualityMetrics
    coverage_policy: CoveragePolicyMetrics
    overall_status: str


def collect_git_metrics(root: Path) -> RepositoryMetrics:
    """Collect Git repository metrics."""
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "--all"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        total_commits = len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0

        result = subprocess.run(
            ["git", "log", "--oneline", "-10"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        last_commits = result.stdout.strip().split("\n") if result.stdout.strip() else []

        result = subprocess.run(
            ["git", "branch", "-a"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        branches = [
            b.strip().removeprefix("* ").strip() for b in result.stdout.split("\n") if b.strip()
        ]

        result = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        remote_url = result.stdout.strip()

        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        working_tree_clean = not result.stdout.strip()

    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        raise RuntimeError(f"Git metrics collection failed: {e}") from e

    return RepositoryMetrics(
        total_commits=total_commits,
        python_files=_count_python_files(root),
        lines_of_code=_count_lines_of_code(root),
        git_size_kb=_get_size_kb(root / ".git"),
        project_size_mb=_get_size_mb(root),
        branches=branches,
        remote_url=remote_url,
        last_commits=last_commits[:10],
        working_tree_clean=working_tree_clean,
    )


def collect_test_metrics(root: Path) -> TestMetrics:
    """Collect test execution metrics."""
    passed = failed = 0
    exec_time = 0.0
    coverage_percent = 0.0

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "coverage",
                "run",
                "-m",
                "pytest",
                "operations/tests/",
                "-q",
                "--tb=no",
            ],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = result.stdout + result.stderr

        passed_match = re.search(r"(\d+) passed", output)
        if passed_match:
            passed = int(passed_match.group(1))

        failed_match = re.search(r"(\d+) failed", output)
        if failed_match:
            failed = int(failed_match.group(1))

        time_match = re.search(r"in ([\d.]+)s", output)
        if time_match:
            exec_time = float(time_match.group(1))

        # Export a fresh runtime/coverage.json from the run above instead of
        # trusting whatever (possibly stale, possibly absent) file happens
        # to already be on disk - collect_coverage_policy() depends on this
        # reflecting the coverage this exact invocation just measured.
        (root / "runtime").mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [sys.executable, "-m", "coverage", "json", "-o", "runtime/coverage.json"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=30,
        )
        coverage_percent = _get_coverage_percent(root)

    except subprocess.TimeoutExpired:
        raise RuntimeError("Test execution timed out") from None

    return TestMetrics(
        total_passed=passed,
        total_failed=failed,
        execution_time_sec=exec_time,
        coverage_percent=coverage_percent,
    )


def collect_code_quality_metrics(root: Path) -> CodeQualityMetrics:
    """Collect code quality metrics.

    Scope and rules deliberately mirror the canonical CI gates
    (run_suite.py / run_mypy_baseline.py) rather than an independently
    chosen path list or ruff rule set: a health check that disagrees with
    the gate that actually blocks CI is worse than no health check, since
    it trains readers to distrust (or ignore) whichever one is "wrong".
    """
    mypy_issues = 0
    ruff_issues = 0
    formatting_compliant = True
    type_safe = True

    try:
        result = subprocess.run(
            [
                "mypy",
                "operations/scripts",
                "operations/tests",
                "src",
                "--show-error-codes",
                "--no-error-summary",
            ],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout + result.stderr
        mypy_issues = len(
            re.findall(r"^.+:\d+(?::\d+)?: error:.*\[[^\]]+\]$", output, re.MULTILINE)
        )
        type_safe = mypy_issues == 0

    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    try:
        # No --select override: this must see the same pyproject.toml
        # [tool.ruff.lint] select/ignore (e.g. E501 is intentionally
        # ignored project-wide) that the canonical "Ruff lint" step does,
        # or the two will disagree on what counts as an issue.
        result = subprocess.run(
            ["ruff", "check", "operations/scripts", "operations/tests"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=60,
        )
        # Ruff's default output is multi-line per finding (code context,
        # "-->" locations, "|" gutters); counting lines containing ":"
        # overcounts wildly. Its own summary line is the real count.
        found = re.search(r"^Found (\d+) error", result.stdout, re.MULTILINE)
        ruff_issues = int(found.group(1)) if found else 0

    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    try:
        result = subprocess.run(
            ["ruff", "format", "--check", "operations/scripts", "operations/tests"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=60,
        )
        formatting_compliant = result.returncode == 0

    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return CodeQualityMetrics(
        mypy_issues=mypy_issues,
        ruff_issues=ruff_issues,
        formatting_compliant=formatting_compliant,
        type_safe=type_safe,
    )


def _count_python_files(root: Path) -> int:
    """Count Python files in the repository."""
    return sum(1 for _ in root.rglob("*.py") if ".git" not in _.parts)


def _count_lines_of_code(root: Path) -> int:
    """Count lines of code in Python files."""
    total = 0
    for py_file in root.rglob("*.py"):
        if ".git" in py_file.parts:
            continue
        try:
            total += len(py_file.read_text(encoding="utf-8").splitlines())
        except (OSError, UnicodeDecodeError):
            pass
    return total


def _get_size_kb(path: Path) -> int:
    """Get directory size in KB."""
    if not path.exists():
        return 0
    total = 0
    for item in path.rglob("*"):
        if item.is_file():
            total += item.stat().st_size
    return total // 1024


def _get_size_mb(path: Path) -> float:
    """Get directory size in MB (excluding .git)."""
    total = 0
    for item in path.rglob("*"):
        if item.is_file() and ".git" not in item.parts:
            total += item.stat().st_size
    return round(total / (1024 * 1024), 1)


def _get_coverage_percent(root: Path) -> float:
    """Get coverage percentage from coverage reports."""
    coverage_json = root / "runtime" / "coverage.json"
    if coverage_json.exists():
        try:
            data = json.loads(coverage_json.read_text())
            return round(data.get("totals", {}).get("percent_covered", 0), 1)
        except (json.JSONDecodeError, KeyError):
            pass
    return 0.0


def collect_coverage_policy(root: Path) -> CoveragePolicyMetrics:
    """Evaluate the real tiered coverage gate (overall + critical modules).

    reporter.py used to render coverage against a hardcoded 75% regardless
    of what pyproject.toml actually requires - e.g. it would show a plain
    "82.0% coverage ✅" even if one of the five modules that must stay at
    85% had dropped below its floor. Reading runtime/coverage.json through
    the same evaluate_coverage() the canonical "Coverage policy" CI step
    uses keeps this in lockstep with that gate instead.
    """
    coverage_json = root / "runtime" / "coverage.json"
    if not coverage_json.exists():
        return CoveragePolicyMetrics(
            rows=[], errors=["runtime/coverage.json отсутствует"], passed=False
        )
    try:
        report = json.loads(coverage_json.read_text())
        policy = load_policy(root)
        errors, rows = evaluate_coverage(report, policy)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return CoveragePolicyMetrics(rows=[], errors=[str(exc)], passed=False)
    return CoveragePolicyMetrics(rows=rows, errors=errors, passed=not errors)


def assess_health(health: RepositoryHealth) -> str:
    """Assess overall repository health status."""
    issues = []

    if health.tests.total_failed > 0:
        issues.append(f"Tests failing: {health.tests.total_failed}")
    if not health.code_quality.type_safe:
        issues.append("Type safety issues detected")
    if not health.code_quality.formatting_compliant:
        issues.append("Code formatting issues detected")
    if not health.repository.working_tree_clean:
        issues.append("Working tree has uncommitted changes")
    if not health.coverage_policy.passed:
        issues.append("Coverage policy violations detected")

    if issues:
        return "⚠️ NEEDS ATTENTION"
    if health.tests.total_failed == 0 and health.code_quality.type_safe:
        return "✅ HEALTHY"

    return "⚠️ REVIEW RECOMMENDED"
