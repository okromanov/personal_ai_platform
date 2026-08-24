from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))


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
class RepositoryHealth:
    """Overall repository health status."""

    repository: RepositoryMetrics
    tests: TestMetrics
    code_quality: CodeQualityMetrics
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
        branches = [b.strip() for b in result.stdout.split("\n") if b.strip()]

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
    import re

    passed = failed = 0
    exec_time = 0.0

    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "operations/tests/", "-q", "--tb=no"],
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
    """Collect code quality metrics."""
    mypy_issues = 0
    ruff_issues = 0
    formatting_compliant = True
    type_safe = True

    try:
        result = subprocess.run(
            ["mypy", "src", "operations/scripts", "--ignore-missing-imports"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=60,
        )
        mypy_issues = result.stdout.count("error:")
        type_safe = result.returncode == 0

    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    try:
        result = subprocess.run(
            ["ruff", "check", "src", "operations", "--select=E,F,W"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=60,
        )
        ruff_issues = len(
            [line for line in result.stdout.split("\n") if line.strip() and ":" in line]
        )

    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    try:
        result = subprocess.run(
            ["ruff", "format", "--check", "src", "operations"],
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

    if issues:
        return "⚠️ NEEDS ATTENTION"
    if health.tests.total_failed == 0 and health.code_quality.type_safe:
        return "✅ HEALTHY"

    return "⚠️ REVIEW RECOMMENDED"
