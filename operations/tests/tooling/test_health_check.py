from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from operations.scripts.health_check.metrics import (
    CodeQualityMetrics,
    RepositoryHealth,
    RepositoryMetrics,
    TestMetrics,
    assess_health,
    collect_code_quality_metrics,
    collect_git_metrics,
    collect_test_metrics,
)
from operations.scripts.health_check.reporter import generate_report, print_summary


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def _init_repo(root: Path) -> None:
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.name", "Test")
    _git(root, "config", "user.email", "test@example.invalid")
    (root / "a.py").write_text("x = 1\n", encoding="utf-8")
    _git(root, "add", "a.py")
    _git(root, "commit", "-q", "-m", "initial")


class CollectGitMetricsTests(unittest.TestCase):
    def test_reports_real_commit_and_branch_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_repo(root)

            metrics = collect_git_metrics(root)

            self.assertEqual(metrics.total_commits, 1)
            self.assertIn("initial", metrics.last_commits[0])
            self.assertTrue(metrics.working_tree_clean)
            self.assertEqual(metrics.python_files, 1)
            self.assertGreaterEqual(metrics.lines_of_code, 1)

    def test_dirty_working_tree_is_reported_as_not_clean(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_repo(root)
            (root / "a.py").write_text("x = 2\n", encoding="utf-8")

            metrics = collect_git_metrics(root)

            self.assertFalse(metrics.working_tree_clean)

    def test_current_branch_name_has_no_git_marker_prefix(self) -> None:
        # `git branch -a` marks the checked-out branch with a leading "* ",
        # e.g. "* main"; reporter.py renders branches[0] verbatim as the
        # report's "Ветка" value, so a raw "* " prefix would leak into it.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _init_repo(root)

            metrics = collect_git_metrics(root)

            self.assertEqual(metrics.branches, ["main"])


class CollectCodeQualityMetricsTests(unittest.TestCase):
    def test_counts_ruff_issues_from_summary_line_and_flags_noncompliant_formatting(
        self,
    ) -> None:
        def fake_run(cmd: list[str], **_: object) -> subprocess.CompletedProcess[str]:
            if cmd[0] == "mypy":
                # Real mypy --show-error-codes output: one "error:" line per
                # finding, each ending in a bracketed error code.
                stdout = (
                    "operations/scripts/a.py:1: error: bad type [arg-type]\n"
                    "operations/scripts/a.py:2: error: also bad [assignment]\n"
                )
                return subprocess.CompletedProcess(cmd, 1, stdout=stdout, stderr="")
            if cmd[:2] == ["ruff", "check"]:
                # Real ruff output is multi-line per finding (code context,
                # "-->" locations, "|" gutters, each containing ":") with a
                # trailing "Found N error(s)." summary - only that summary
                # line is the real count.
                stdout = (
                    "src/a.py:1:1: F401 [*] `os` imported but unused\n"
                    "  |\n"
                    "1 | import os\n"
                    "  |        ^^\n"
                    "  |\n\n"
                    "Found 1 error.\n"
                    "[*] 1 fixable with the `--fix` option.\n"
                )
                return subprocess.CompletedProcess(cmd, 1, stdout=stdout)
            if cmd[:2] == ["ruff", "format"]:
                return subprocess.CompletedProcess(cmd, 1, stdout="")
            raise AssertionError(f"unexpected command: {cmd}")

        with tempfile.TemporaryDirectory() as tmp, patch("subprocess.run", side_effect=fake_run):
            quality = collect_code_quality_metrics(Path(tmp))

        self.assertFalse(quality.type_safe)
        self.assertEqual(quality.mypy_issues, 2)
        self.assertEqual(quality.ruff_issues, 1)
        self.assertFalse(quality.formatting_compliant)

    def test_ruff_output_with_no_findings_counts_zero(self) -> None:
        def fake_run(cmd: list[str], **_: object) -> subprocess.CompletedProcess[str]:
            if cmd[0] == "mypy":
                return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
            if cmd[:2] == ["ruff", "check"]:
                return subprocess.CompletedProcess(cmd, 0, stdout="All checks passed!\n")
            if cmd[:2] == ["ruff", "format"]:
                return subprocess.CompletedProcess(cmd, 0, stdout="3 files already formatted\n")
            raise AssertionError(f"unexpected command: {cmd}")

        with tempfile.TemporaryDirectory() as tmp, patch("subprocess.run", side_effect=fake_run):
            quality = collect_code_quality_metrics(Path(tmp))

        self.assertTrue(quality.type_safe)
        self.assertEqual(quality.mypy_issues, 0)
        self.assertEqual(quality.ruff_issues, 0)
        self.assertTrue(quality.formatting_compliant)

    def test_missing_tools_leave_safe_defaults(self) -> None:
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch("subprocess.run", side_effect=FileNotFoundError),
        ):
            quality = collect_code_quality_metrics(Path(tmp))

        self.assertTrue(quality.type_safe)
        self.assertEqual(quality.ruff_issues, 0)
        self.assertTrue(quality.formatting_compliant)


class CollectTestMetricsTests(unittest.TestCase):
    def test_parses_pytest_summary_line(self) -> None:
        completed = subprocess.CompletedProcess(
            ["pytest"], 0, stdout="10 passed, 2 failed in 3.45s\n", stderr=""
        )
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch("subprocess.run", return_value=completed),
        ):
            metrics = collect_test_metrics(Path(tmp))

        self.assertEqual(metrics.total_passed, 10)
        self.assertEqual(metrics.total_failed, 2)
        self.assertAlmostEqual(metrics.execution_time_sec, 3.45)

    def test_runs_pytest_under_the_current_interpreter(self) -> None:
        # A bare "python" on PATH can resolve to a different interpreter
        # than the one running this script (e.g. one without pytest/coverage
        # installed), which silently yields "0 passed" instead of real
        # results. The command must pin sys.executable instead.
        completed = subprocess.CompletedProcess(
            ["pytest"], 0, stdout="1 passed in 0.1s\n", stderr=""
        )
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch("subprocess.run", return_value=completed) as mock_run,
        ):
            collect_test_metrics(Path(tmp))

        called_cmd = mock_run.call_args[0][0]
        self.assertEqual(called_cmd[0], sys.executable)

    def test_reads_coverage_percent_from_runtime_coverage_json(self) -> None:
        completed = subprocess.CompletedProcess(
            ["pytest"], 0, stdout="1 passed in 0.1s\n", stderr=""
        )
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch("subprocess.run", return_value=completed),
        ):
            root = Path(tmp)
            coverage_dir = root / "runtime"
            coverage_dir.mkdir()
            (coverage_dir / "coverage.json").write_text(
                json.dumps({"totals": {"percent_covered": 87.654}}), encoding="utf-8"
            )

            metrics = collect_test_metrics(root)

        self.assertEqual(metrics.coverage_percent, 87.7)


def _make_health(
    repo: RepositoryMetrics | None = None,
    tests: TestMetrics | None = None,
    quality: CodeQualityMetrics | None = None,
) -> RepositoryHealth:
    return RepositoryHealth(
        repository=repo
        or RepositoryMetrics(
            total_commits=1,
            python_files=1,
            lines_of_code=10,
            git_size_kb=1,
            project_size_mb=0.1,
            branches=["main"],
            remote_url="origin",
            last_commits=["abc initial"],
            working_tree_clean=True,
        ),
        tests=tests
        or TestMetrics(
            total_passed=1, total_failed=0, execution_time_sec=0.1, coverage_percent=100.0
        ),
        code_quality=quality
        or CodeQualityMetrics(
            mypy_issues=0, ruff_issues=0, formatting_compliant=True, type_safe=True
        ),
        overall_status="",
    )


class AssessHealthTests(unittest.TestCase):
    def test_healthy_when_everything_clean(self) -> None:
        health = _make_health()
        self.assertEqual(assess_health(health), "✅ HEALTHY")

    def test_needs_attention_when_tests_fail(self) -> None:
        health = _make_health(
            tests=TestMetrics(
                total_passed=1, total_failed=1, execution_time_sec=0.1, coverage_percent=100.0
            )
        )
        self.assertEqual(assess_health(health), "⚠️ NEEDS ATTENTION")

    def test_needs_attention_when_working_tree_dirty(self) -> None:
        repo = RepositoryMetrics(
            total_commits=1,
            python_files=1,
            lines_of_code=10,
            git_size_kb=1,
            project_size_mb=0.1,
            branches=["main"],
            remote_url="origin",
            last_commits=["abc initial"],
            working_tree_clean=False,
        )
        health = _make_health(repo=repo)
        self.assertEqual(assess_health(health), "⚠️ NEEDS ATTENTION")


class ReportRenderingTests(unittest.TestCase):
    def _health(self) -> RepositoryHealth:
        repo = RepositoryMetrics(
            total_commits=71,
            python_files=108,
            lines_of_code=18662,
            git_size_kb=793,
            project_size_mb=21.7,
            branches=["main"],
            remote_url="https://github.com/okromanov/personal_ai_platform",
            last_commits=["abc123 initial commit"],
            working_tree_clean=True,
        )
        tests = TestMetrics(
            total_passed=284, total_failed=0, execution_time_sec=11.6, coverage_percent=80.0
        )
        quality = CodeQualityMetrics(
            mypy_issues=0, ruff_issues=0, formatting_compliant=True, type_safe=True
        )
        health = RepositoryHealth(
            repository=repo, tests=tests, code_quality=quality, overall_status=""
        )
        health.overall_status = assess_health(health)
        return health

    def test_generate_report_includes_key_metrics(self) -> None:
        report = generate_report(self._health())

        self.assertIn("284", report)
        self.assertIn("okromanov/personal_ai_platform", report)
        self.assertIn("✅ HEALTHY", report)
        self.assertIn("<!-- generated file: do not edit manually -->", report)

    def test_print_summary_writes_key_lines_to_stdout(self) -> None:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            print_summary(self._health())

        output = buffer.getvalue()
        self.assertIn("REPOSITORY HEALTH CHECK SUMMARY", output)
        self.assertIn("Commits: 71", output)
        self.assertIn("Passed: 284", output)
        self.assertIn("Type safe: ✅ Yes", output)
        self.assertIn("Working Tree: ✅ Clean", output)


if __name__ == "__main__":
    unittest.main()
