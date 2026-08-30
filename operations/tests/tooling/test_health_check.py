from __future__ import annotations

import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from operations.scripts.health_check import generate as health_generate
from operations.scripts.health_check.metrics import (
    CodeQualityMetrics,
    CoveragePolicyMetrics,
    RepositoryHealth,
    RepositoryMetrics,
    UnitTestMetrics,
    assess_health,
    collect_code_quality_metrics,
    collect_coverage_policy,
    collect_git_metrics,
    collect_test_metrics,
)
from operations.scripts.health_check.reporter import generate_report, print_summary


def _install_health_contract(root: Path) -> None:
    source_root = Path(__file__).resolve().parents[3]
    (root / "operations/templates").mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_root / "operations/template_registry.json", root / "operations")
    shutil.copy2(
        source_root / "operations/templates/health_check_report_template.md",
        root / "operations/templates",
    )


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
            self.assertEqual(metrics.branch_name, "main")
            self.assertRegex(metrics.head_sha, r"^[0-9a-f]{40}$")

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
            if cmd[:3] == [sys.executable, "-m", "mypy"]:
                # Real mypy --show-error-codes output: one "error:" line per
                # finding, each ending in a bracketed error code.
                stdout = (
                    "operations/scripts/a.py:1: error: bad type [arg-type]\n"
                    "operations/scripts/a.py:2: error: also bad [assignment]\n"
                )
                return subprocess.CompletedProcess(cmd, 1, stdout=stdout, stderr="")
            if cmd[2:4] == ["ruff", "check"]:
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
            if cmd[2:4] == ["ruff", "format"]:
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
            if cmd[:3] == [sys.executable, "-m", "mypy"]:
                return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
            if cmd[2:4] == ["ruff", "check"]:
                return subprocess.CompletedProcess(cmd, 0, stdout="All checks passed!\n")
            if cmd[2:4] == ["ruff", "format"]:
                return subprocess.CompletedProcess(cmd, 0, stdout="3 files already formatted\n")
            raise AssertionError(f"unexpected command: {cmd}")

        with tempfile.TemporaryDirectory() as tmp, patch("subprocess.run", side_effect=fake_run):
            quality = collect_code_quality_metrics(Path(tmp))

        self.assertTrue(quality.type_safe)
        self.assertEqual(quality.mypy_issues, 0)
        self.assertEqual(quality.ruff_issues, 0)
        self.assertTrue(quality.formatting_compliant)

    def test_missing_tools_fail_closed(self) -> None:
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch("subprocess.run", side_effect=FileNotFoundError),
        ):
            quality = collect_code_quality_metrics(Path(tmp))

        self.assertFalse(quality.type_safe)
        self.assertEqual(quality.ruff_issues, 0)
        self.assertFalse(quality.formatting_compliant)
        self.assertEqual(len(quality.collection_errors), 3)


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


def _write_coverage_policy(
    root: Path, overall: int = 75, modules: dict[str, int] | None = None
) -> None:
    module_lines = "\n".join(f'"{path}" = {floor}' for path, floor in (modules or {}).items())
    (root / "pyproject.toml").write_text(
        "[tool.personal_ai_platform.coverage]\n"
        f"overall = {overall}\n"
        "[tool.personal_ai_platform.coverage.modules]\n"
        f"{module_lines}\n",
        encoding="utf-8",
    )


class CollectCoveragePolicyTests(unittest.TestCase):
    def test_missing_coverage_json_is_reported_as_not_passed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_coverage_policy(root)

            policy = collect_coverage_policy(root)

        self.assertFalse(policy.passed)
        self.assertTrue(policy.errors)

    def test_passes_when_overall_coverage_meets_the_configured_floor(self) -> None:
        # This is the 85%-vs-75% question in practice: the report must
        # evaluate against pyproject.toml's real policy, not a hardcoded
        # number baked into reporter.py.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_coverage_policy(root, overall=75)
            (root / "runtime").mkdir()
            (root / "runtime" / "coverage.json").write_text(
                json.dumps({"totals": {"percent_covered": 80.0}, "files": {}}),
                encoding="utf-8",
            )

            policy = collect_coverage_policy(root)

        self.assertTrue(policy.passed)
        self.assertIn("overall: 80.00% (minimum 75.00%)", policy.rows)

    def test_fails_when_a_critical_module_is_below_its_own_higher_floor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_coverage_policy(root, overall=75, modules={"pkg/critical.py": 85})
            (root / "runtime").mkdir()
            (root / "runtime" / "coverage.json").write_text(
                json.dumps(
                    {
                        "totals": {"percent_covered": 90.0},
                        "files": {"pkg/critical.py": {"summary": {"percent_covered": 80.0}}},
                    }
                ),
                encoding="utf-8",
            )

            policy = collect_coverage_policy(root)

        self.assertFalse(policy.passed)
        self.assertTrue(any("pkg/critical.py" in error for error in policy.errors))


def _make_health(
    repo: RepositoryMetrics | None = None,
    tests: UnitTestMetrics | None = None,
    quality: CodeQualityMetrics | None = None,
    coverage: CoveragePolicyMetrics | None = None,
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
            branch_name="main",
            head_sha="a" * 40,
            collected_at_utc="2026-08-26T06:00:00+00:00",
        ),
        tests=tests
        or UnitTestMetrics(
            total_passed=1, total_failed=0, execution_time_sec=0.1, coverage_percent=100.0
        ),
        code_quality=quality
        or CodeQualityMetrics(
            mypy_issues=0, ruff_issues=0, formatting_compliant=True, type_safe=True
        ),
        coverage_policy=coverage
        or CoveragePolicyMetrics(
            rows=["overall: 100.00% (minimum 75.00%)"], errors=[], passed=True
        ),
        overall_status="",
    )


class HealthCheckCliTests(unittest.TestCase):
    def test_main_writes_revision_bound_report_and_json_to_runtime_paths(self) -> None:
        health = _make_health()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _install_health_contract(root)
            report_path = root / "runtime" / "health.md"
            json_path = root / "runtime" / "health.json"
            with (
                patch.object(health_generate, "find_project_root", return_value=root),
                patch.object(
                    health_generate, "collect_git_metrics", return_value=health.repository
                ),
                patch.object(health_generate, "collect_test_metrics", return_value=health.tests),
                patch.object(
                    health_generate,
                    "collect_code_quality_metrics",
                    return_value=health.code_quality,
                ),
                patch.object(
                    health_generate,
                    "collect_coverage_policy",
                    return_value=health.coverage_policy,
                ),
                patch.object(
                    sys,
                    "argv",
                    [
                        "generate.py",
                        "--output",
                        str(report_path),
                        "--json",
                        str(json_path),
                    ],
                ),
            ):
                result = health_generate.main()

            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(result, 0)
            self.assertEqual(payload["repository"]["head_sha"], "a" * 40)
            self.assertEqual(payload["repository"]["branch_name"], "main")
            self.assertEqual(payload["overall_status"], "✅ HEALTHY")
            self.assertIn("`" + "a" * 40 + "`", report_path.read_text(encoding="utf-8"))

    def test_main_defaults_to_uncommitted_runtime_report(self) -> None:
        health = _make_health()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _install_health_contract(root)
            with (
                patch.object(health_generate, "find_project_root", return_value=root),
                patch.object(
                    health_generate, "collect_git_metrics", return_value=health.repository
                ),
                patch.object(health_generate, "collect_test_metrics", return_value=health.tests),
                patch.object(
                    health_generate,
                    "collect_code_quality_metrics",
                    return_value=health.code_quality,
                ),
                patch.object(
                    health_generate,
                    "collect_coverage_policy",
                    return_value=health.coverage_policy,
                ),
                patch.object(sys, "argv", ["generate.py"]),
            ):
                result = health_generate.main()

            report_path = root / "runtime" / "health_check_report.md"
            self.assertEqual(result, 0)
            self.assertTrue(report_path.is_file())
            self.assertIn("✅ HEALTHY", report_path.read_text(encoding="utf-8"))

    def test_main_resolves_relative_runtime_paths_against_repository_root(self) -> None:
        health = _make_health()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _install_health_contract(root)
            with (
                patch.object(health_generate, "find_project_root", return_value=root),
                patch.object(
                    health_generate, "collect_git_metrics", return_value=health.repository
                ),
                patch.object(health_generate, "collect_test_metrics", return_value=health.tests),
                patch.object(
                    health_generate,
                    "collect_code_quality_metrics",
                    return_value=health.code_quality,
                ),
                patch.object(
                    health_generate,
                    "collect_coverage_policy",
                    return_value=health.coverage_policy,
                ),
                patch.object(
                    sys,
                    "argv",
                    [
                        "generate.py",
                        "--output",
                        "runtime/health_check_report.md",
                        "--json",
                        "runtime/health_check.json",
                    ],
                ),
            ):
                result = health_generate.main()

            self.assertEqual(result, 0)
            self.assertTrue((root / "runtime/health_check_report.md").is_file())
            self.assertTrue((root / "runtime/health_check.json").is_file())

    def test_main_fails_closed_when_repository_metrics_are_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with (
                patch.object(health_generate, "find_project_root", return_value=Path(tmp)),
                patch.object(
                    health_generate,
                    "collect_git_metrics",
                    side_effect=RuntimeError("missing git history"),
                ),
                patch.object(sys, "argv", ["generate.py"]),
            ):
                self.assertEqual(health_generate.main(), 1)


class AssessHealthTests(unittest.TestCase):
    def test_healthy_when_everything_clean(self) -> None:
        health = _make_health()
        self.assertEqual(assess_health(health), "✅ HEALTHY")

    def test_needs_attention_when_tests_fail(self) -> None:
        health = _make_health(
            tests=UnitTestMetrics(
                total_passed=1, total_failed=1, execution_time_sec=0.1, coverage_percent=100.0
            )
        )
        self.assertEqual(assess_health(health), "⚠️ NEEDS ATTENTION")

    def test_incomplete_when_required_tool_is_unavailable(self) -> None:
        health = _make_health(
            quality=CodeQualityMetrics(
                mypy_issues=0,
                ruff_issues=0,
                formatting_compliant=False,
                type_safe=False,
                collection_errors=["mypy unavailable"],
            )
        )
        self.assertEqual(assess_health(health), "❌ INCOMPLETE")

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
            branch_name="main",
            head_sha="a" * 40,
            collected_at_utc="2026-08-26T06:00:00+00:00",
        )
        health = _make_health(repo=repo)
        self.assertEqual(assess_health(health), "⚠️ NEEDS ATTENTION")

    def test_needs_attention_when_coverage_policy_fails(self) -> None:
        health = _make_health(
            coverage=CoveragePolicyMetrics(
                rows=["operations/scripts/critical.py: 80.00% (minimum 85.00%)"],
                errors=["operations/scripts/critical.py: покрытие 80.00% ниже 85.00%"],
                passed=False,
            )
        )
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
            branch_name="main",
            head_sha="a" * 40,
            collected_at_utc="2026-08-26T06:00:00+00:00",
        )
        tests = UnitTestMetrics(
            total_passed=284, total_failed=0, execution_time_sec=11.6, coverage_percent=80.0
        )
        quality = CodeQualityMetrics(
            mypy_issues=0, ruff_issues=0, formatting_compliant=True, type_safe=True
        )
        coverage = CoveragePolicyMetrics(
            rows=["overall: 80.00% (minimum 75.00%)"], errors=[], passed=True
        )
        health = RepositoryHealth(
            repository=repo,
            tests=tests,
            code_quality=quality,
            coverage_policy=coverage,
            overall_status="",
        )
        health.overall_status = assess_health(health)
        return health

    def test_generate_report_includes_key_metrics(self) -> None:
        report = generate_report(self._health())

        self.assertIn("284", report)
        self.assertIn("okromanov/personal_ai_platform", report)
        self.assertIn("✅ HEALTHY", report)
        self.assertIn("`" + "a" * 40 + "`", report)
        self.assertIn("<!-- generated file: do not edit manually -->", report)

    def test_generate_report_recommends_nothing_critical_when_healthy(self) -> None:
        report = generate_report(self._health())

        self.assertIn("Критичных проблем не обнаружено", report)

    def test_generate_report_flags_real_problems_in_recommendations(self) -> None:
        health = self._health()
        health.code_quality = CodeQualityMetrics(
            mypy_issues=3, ruff_issues=0, formatting_compliant=True, type_safe=False
        )
        health.coverage_policy = CoveragePolicyMetrics(
            rows=["operations/scripts/critical.py: 80.00% (minimum 85.00%)"],
            errors=["operations/scripts/critical.py: покрытие 80.00% ниже 85.00%"],
            passed=False,
        )
        health.overall_status = assess_health(health)

        report = generate_report(health)

        self.assertIn("Устранить ошибки типов MyPy (3)", report)
        self.assertIn("покрытие 80.00% ниже 85.00%", report)
        self.assertNotIn("Критичных проблем не обнаружено", report)

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
