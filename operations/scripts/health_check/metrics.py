from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from operations.scripts.quality.check_coverage import evaluate_coverage, load_policy
from operations.scripts.quality.scope import PYTHON_QUALITY_PATHS


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
    branch_name: str
    head_sha: str
    collected_at_utc: str


@dataclass
class UnitTestMetrics:
    """Test execution metrics."""

    total_passed: int
    total_failed: int
    execution_time_sec: float
    coverage_percent: float
    collection_error: str | None = None


@dataclass
class CodeQualityMetrics:
    """Code quality metrics."""

    mypy_issues: int
    ruff_issues: int
    formatting_compliant: bool
    type_safe: bool
    collection_errors: list[str] = field(default_factory=list)


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
    tests: UnitTestMetrics
    code_quality: CodeQualityMetrics
    coverage_policy: CoveragePolicyMetrics
    overall_status: str


def _run_git(root: Path, *args: str, required: bool = True) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        raise RuntimeError(f"Git metrics collection failed: {exc}") from exc
    if required and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown git error"
        raise RuntimeError(f"Git metrics collection failed: git {' '.join(args)}: {detail}")
    return result


def collect_git_metrics(root: Path) -> RepositoryMetrics:
    """Collect Git repository metrics tied to one exact revision."""
    result = _run_git(root, "log", "--oneline", "--all")
    total_commits = len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0

    result = _run_git(root, "log", "--oneline", "-10")
    last_commits = result.stdout.strip().split("\n") if result.stdout.strip() else []

    result = _run_git(root, "branch", "-a")
    branches = [
        branch.strip().removeprefix("* ").strip()
        for branch in result.stdout.split("\n")
        if branch.strip()
    ]
    branch_name = _run_git(root, "branch", "--show-current").stdout.strip() or "detached"
    head_sha = _run_git(root, "rev-parse", "HEAD").stdout.strip()
    if not re.fullmatch(r"[0-9a-f]{40}", head_sha):
        raise RuntimeError("Git metrics collection failed: HEAD is not a full commit SHA")

    remote_url = _run_git(
        root, "config", "--get", "remote.origin.url", required=False
    ).stdout.strip()
    working_tree_clean = not _run_git(root, "status", "--porcelain").stdout.strip()

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
        branch_name=branch_name,
        head_sha=head_sha,
        collected_at_utc=datetime.now(UTC).isoformat(),
    )


def collect_test_metrics(root: Path) -> UnitTestMetrics:
    """Collect test execution metrics."""
    passed = failed = 0
    exec_time = 0.0
    coverage_percent = 0.0
    collection_error: str | None = None

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
        output = (result.stdout or "") + (result.stderr or "")

        passed_match = re.search(r"(\d+) passed", output)
        if passed_match:
            passed = int(passed_match.group(1))

        failed_match = re.search(r"(\d+) failed", output)
        if failed_match:
            failed = int(failed_match.group(1))

        time_match = re.search(r"in ([\d.]+)s", output)
        if time_match:
            exec_time = float(time_match.group(1))

        if result.returncode != 0 and failed == 0:
            collection_error = (
                f"pytest exited with {result.returncode} without a parseable failure summary"
            )
        elif passed == 0 and failed == 0:
            collection_error = "pytest produced no parseable test result"

        # Export a fresh runtime/coverage.json from the run above instead of
        # trusting whatever (possibly stale, possibly absent) file happens
        # to already be on disk - collect_coverage_policy() depends on this
        # reflecting the coverage this exact invocation just measured.
        (root / "runtime").mkdir(parents=True, exist_ok=True)
        coverage_result = subprocess.run(
            [sys.executable, "-m", "coverage", "json", "-o", "runtime/coverage.json"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if coverage_result.returncode != 0:
            collection_error = collection_error or (
                f"coverage json exited with {coverage_result.returncode}"
            )
        else:
            coverage_percent = _get_coverage_percent(root)

    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        collection_error = f"test metrics unavailable: {type(exc).__name__}"

    return UnitTestMetrics(
        total_passed=passed,
        total_failed=failed,
        execution_time_sec=exec_time,
        coverage_percent=coverage_percent,
        collection_error=collection_error,
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
    formatting_compliant = False
    type_safe = False
    collection_errors: list[str] = []

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "mypy",
                *PYTHON_QUALITY_PATHS,
                "--show-error-codes",
                "--no-error-summary",
            ],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = (result.stdout or "") + (result.stderr or "")
        mypy_issues = len(
            re.findall(r"^.+:\d+(?::\d+)?: error:.*\[[^\]]+\]$", output, re.MULTILINE)
        )
        type_safe = mypy_issues == 0
        if result.returncode not in {0, 1} or (result.returncode == 1 and mypy_issues == 0):
            type_safe = False
            collection_errors.append(f"mypy failed with exit code {result.returncode}")

    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        collection_errors.append(f"mypy unavailable: {type(exc).__name__}")

    try:
        # No --select override: this must see the same pyproject.toml
        # [tool.ruff.lint] select/ignore (e.g. E501 is intentionally
        # ignored project-wide) that the canonical "Ruff lint" step does,
        # or the two will disagree on what counts as an issue.
        result = subprocess.run(
            [sys.executable, "-m", "ruff", "check", *PYTHON_QUALITY_PATHS],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=60,
        )
        # Ruff's default output is multi-line per finding (code context,
        # "-->" locations, "|" gutters); counting lines containing ":"
        # overcounts wildly. Its own summary line is the real count.
        output = (result.stdout or "") + (result.stderr or "")
        found = re.search(r"^Found (\d+) error", output, re.MULTILINE)
        ruff_issues = int(found.group(1)) if found else 0
        if result.returncode not in {0, 1} or (result.returncode == 1 and found is None):
            collection_errors.append(f"ruff check failed with exit code {result.returncode}")

    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        collection_errors.append(f"ruff check unavailable: {type(exc).__name__}")

    try:
        result = subprocess.run(
            [sys.executable, "-m", "ruff", "format", "--check", *PYTHON_QUALITY_PATHS],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=60,
        )
        formatting_compliant = result.returncode == 0

    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        collection_errors.append(f"ruff format unavailable: {type(exc).__name__}")

    return CodeQualityMetrics(
        mypy_issues=mypy_issues,
        ruff_issues=ruff_issues,
        formatting_compliant=formatting_compliant,
        type_safe=type_safe,
        collection_errors=collection_errors,
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

    if health.tests.collection_error or health.code_quality.collection_errors:
        return "❌ INCOMPLETE"

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
