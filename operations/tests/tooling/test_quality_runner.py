from __future__ import annotations

import json
import os
import stat
import tempfile
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from operations.scripts.quality import run_suite
from operations.scripts.quality.run_unittests import run_tests


class QualityRunnerTests(unittest.TestCase):
    def test_canonical_unittest_runner_rejects_skips(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tests = root / "tests"
            tests.mkdir()
            (tests / "test_sample.py").write_text(
                "import unittest\n"
                "class Sample(unittest.TestCase):\n"
                "    @unittest.skip('not available')\n"
                "    def test_skip(self): pass\n",
                encoding="utf-8",
            )
            with patch.object(
                unittest.defaultTestLoader,
                "_top_level_dir",
                str(Path(__file__).resolve().parents[3]),
            ):
                self.assertEqual(run_tests(root, start_dir="tests", verbosity=0), 2)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tests = root / "tests"
            tests.mkdir()
            (tests / "test_pass.py").write_text(
                "import unittest\n"
                "class Sample(unittest.TestCase):\n"
                "    def test_pass(self): self.assertTrue(True)\n",
                encoding="utf-8",
            )
            self.assertEqual(run_tests(root, start_dir="tests", verbosity=0), 0)

    def test_canonical_unittest_runner_gives_unexpected_success_its_own_exit_code(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tests = root / "tests"
            tests.mkdir()
            (tests / "test_xpass.py").write_text(
                "import unittest\n"
                "class Sample(unittest.TestCase):\n"
                "    @unittest.expectedFailure\n"
                "    def test_now_passes(self): self.assertTrue(True)\n",
                encoding="utf-8",
            )
            with patch.object(
                unittest.defaultTestLoader,
                "_top_level_dir",
                str(Path(__file__).resolve().parents[3]),
            ):
                self.assertEqual(run_tests(root, start_dir="tests", verbosity=0), 3)

    def test_configuration_and_permission_checks_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text(
                "[tool.quality]\nenabled = true\n", encoding="utf-8"
            )
            requirements = root / run_suite.DEV_REQUIREMENTS_PATH
            requirements.parent.mkdir(parents=True)
            requirements_input = root / run_suite.DEV_REQUIREMENTS_INPUT_PATH
            requirements_input.write_text("ruff==0.16.3\nmypy==2.3.1\n", encoding="utf-8")
            requirements.write_text(
                "ruff==0.16.3 \\\n    --hash=sha256:" + "a" * 64 + "\n"
                "mypy==2.3.1 \\\n    --hash=sha256:" + "b" * 64 + "\n",
                encoding="utf-8",
            )
            audit_baseline = root / run_suite.AUDIT_REGISTER_PATH
            audit_baseline.parent.mkdir(parents=True)
            audit_baseline.write_text(
                "| [AUD-001](audit_adhoc_cards.md#aud-001) | low | resolved | "
                "2026-08-27 | — | none | evidence | done |\n",
                encoding="utf-8",
            )
            (root / "valid.json").write_text(json.dumps({"ok": True}), encoding="utf-8")
            run_suite.validate_configuration_files(root)
            (root / "broken.json").write_text("{", encoding="utf-8")
            with self.assertRaisesRegex(run_suite.QualityFailure, "Invalid JSON"):
                run_suite.validate_json_files(root)
            (root / "broken.json").unlink()

            (root / "broken.toml").write_text("[tool\n", encoding="utf-8")
            with self.assertRaisesRegex(run_suite.QualityFailure, "Invalid TOML"):
                run_suite.validate_toml_files(root)
            (root / "broken.toml").unlink()

            requirements_input.write_text("ruff>=0.16.3\n", encoding="utf-8")
            with self.assertRaisesRegex(run_suite.QualityFailure, "exact name==version"):
                run_suite.validate_development_requirements(root)
            requirements_input.write_text("my_pkg==1.0\nmy-pkg==1.1\n", encoding="utf-8")
            with self.assertRaisesRegex(run_suite.QualityFailure, "duplicate dependency"):
                run_suite.validate_development_requirements(root)
            requirements_input.write_text("# no dependencies\n", encoding="utf-8")
            with self.assertRaisesRegex(run_suite.QualityFailure, "at least one"):
                run_suite.validate_development_requirements(root)
            requirements_input.unlink()
            with self.assertRaisesRegex(run_suite.QualityFailure, "Missing"):
                run_suite.validate_development_requirements(root)

    def test_development_lock_rejects_missing_hash_and_stale_direct_pin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / run_suite.DEV_REQUIREMENTS_INPUT_PATH
            lock_path = root / run_suite.DEV_REQUIREMENTS_PATH
            input_path.parent.mkdir(parents=True)
            input_path.write_text("ruff==0.16.3\n", encoding="utf-8")
            lock_path.write_text("ruff==0.16.3\n", encoding="utf-8")
            with self.assertRaisesRegex(run_suite.QualityFailure, "without SHA-256 hashes"):
                run_suite.validate_development_requirements(root)

            lock_path.write_text(
                "ruff==0.16.2 \\\n    --hash=sha256:" + "a" * 64 + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(run_suite.QualityFailure, "stale"):
                run_suite.validate_development_requirements(root)

    def test_audit_baseline_rejects_duplicate_and_unowned_open_findings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / run_suite.AUDIT_REGISTER_PATH
            path.parent.mkdir(parents=True)
            path.write_text(
                "| AUD-001 | medium | open | 2026-08-27 | — | none | evidence | fix |\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(run_suite.QualityFailure, "requires owner"):
                run_suite.validate_audit_baseline(root)

            row = (
                "| AUD-001 | medium | open | 2026-08-27 | 2026-09-02 | "
                "repository_owner | evidence | fix |\n"
            )
            path.write_text(row + row, encoding="utf-8")
            with self.assertRaisesRegex(run_suite.QualityFailure, "duplicate AUD-001"):
                run_suite.validate_audit_baseline(root)

            script = root / "operations/scripts/a.py"
            script.parent.mkdir(parents=True)
            script.write_text("pass\n", encoding="utf-8")
            tests = root / "operations/tests"
            tests.mkdir(parents=True)
            if os.name != "nt":
                script.chmod(script.stat().st_mode | stat.S_IXUSR)
                with self.assertRaisesRegex(run_suite.QualityFailure, "must not be executable"):
                    run_suite.validate_python_permissions(root)

    def test_audit_baseline_rejects_resolved_while_critical_finding_open(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / run_suite.AUDIT_REGISTER_PATH
            path.parent.mkdir(parents=True)
            path.write_text(
                "| AUD-001 | critical | open | 2026-08-27 | 2026-09-02 | "
                "repository_owner | evidence | fix |\n"
                "| AUD-002 | low | resolved | 2026-08-27 | 2026-09-02 | "
                "repository_owner | evidence | fix |\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(run_suite.QualityFailure, "AUD-002.*resolved"):
                run_suite.validate_audit_baseline(root)

            path.write_text(
                "| AUD-001 | critical | open | 2026-08-27 | 2026-09-02 | "
                "repository_owner | evidence | fix |\n"
                "| AUD-002 | low | remediated_pending_verification | 2026-08-27 | "
                "2026-09-02 | repository_owner | evidence | fix |\n",
                encoding="utf-8",
            )
            run_suite.validate_audit_baseline(root)

    def test_audit_baseline_blocks_an_overdue_unresolved_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / run_suite.AUDIT_REGISTER_PATH
            path.parent.mkdir(parents=True)
            path.write_text(
                "| AUD-001 | medium | open | 2026-08-27 | 2026-09-01 | "
                "repository_owner | evidence | fix |\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(run_suite.QualityFailure, "AUD-001.*overdue"):
                run_suite.validate_audit_baseline(root, today=date(2026, 9, 2))

    def test_audit_baseline_allows_review_due_today(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / run_suite.AUDIT_REGISTER_PATH
            path.parent.mkdir(parents=True)
            path.write_text(
                "| AUD-001 | medium | open | 2026-08-27 | 2026-09-02 | "
                "repository_owner | evidence | fix |\n",
                encoding="utf-8",
            )

            run_suite.validate_audit_baseline(root, today=date(2026, 9, 2))

    def test_run_step_records_combined_output_and_propagates_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            success = SimpleNamespace(returncode=0, stdout="passed\n")
            with patch.object(run_suite.subprocess, "run", return_value=success):
                run_suite.run_step(root, "step", ["command"], artifact="runtime/result.txt")
            self.assertEqual((root / "runtime/result.txt").read_text("utf-8"), "passed\n")

            failure = SimpleNamespace(returncode=7, stdout="failed")
            with patch.object(run_suite.subprocess, "run", return_value=failure):
                with self.assertRaisesRegex(run_suite.QualityFailure, "exit code 7"):
                    run_suite.run_step(root, "step", ["command"])

    def test_run_step_writes_placeholder_for_empty_but_successful_output(self) -> None:
        """A clean tool run (e.g. Vulture finding no dead code) produces empty
        stdout; record_quality_suite.py rejects a zero-byte artifact as
        evidence the step never ran, so the artifact must not be empty."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            clean_run = SimpleNamespace(returncode=0, stdout="")
            with patch.object(run_suite.subprocess, "run", return_value=clean_run):
                run_suite.run_step(
                    root, "Dead code scan", ["command"], artifact="runtime/dead_code.txt"
                )
            content = (root / "runtime/dead_code.txt").read_text("utf-8")
            self.assertTrue(content.strip())

    def test_run_step_fails_with_step_name_after_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            timeout = run_suite.subprocess.TimeoutExpired(
                cmd=["hung-command"], timeout=2, output="partial output\n"
            )
            with patch.object(run_suite.subprocess, "run", side_effect=timeout) as run:
                with self.assertRaisesRegex(
                    run_suite.QualityFailure, "Hung check timed out after 2 seconds"
                ):
                    run_suite.run_step(
                        root,
                        "Hung check",
                        ["hung-command"],
                        artifact="runtime/hung.txt",
                        timeout_seconds=2,
                    )
            self.assertEqual(
                (root / "runtime/hung.txt").read_text(encoding="utf-8"),
                "partial output\n",
            )
            self.assertEqual(run.call_args.kwargs["timeout"], 2)

    def test_fast_and_full_profiles_use_canonical_nonduplicated_steps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "operations/scripts").mkdir(parents=True)
            (root / "operations/tests").mkdir(parents=True)
            calls: list[tuple[str, list[str], str | None]] = []

            def record(
                _root: Path, name: str, command: list[str], *, artifact: str | None = None
            ) -> None:
                calls.append((name, command, artifact))

            with (
                patch.object(run_suite, "validate_configuration_files"),
                patch.object(run_suite, "validate_python_permissions"),
                patch.object(run_suite, "run_step", side_effect=record),
            ):
                run_suite.run_fast(root, "python")
            self.assertEqual([name for name, _, _ in calls].count("Unit tests"), 1)
            self.assertIn("Generated drift", [name for name, _, _ in calls])

            calls.clear()
            with (
                patch.object(run_suite, "validate_configuration_files"),
                patch.object(run_suite, "validate_python_permissions"),
                patch.object(run_suite, "run_step", side_effect=record),
            ):
                run_suite.run_full(root, "python", "base-sha")
            names = [name for name, _, _ in calls]
            self.assertEqual(names.count("Unit tests with branch coverage"), 1)
            coverage = next(command for name, command, _ in calls if name == "Coverage policy")
            self.assertEqual(coverage[-2:], ["--base", "base-sha"])
            self.assertIn("runtime/coverage.json", coverage)

            calls.clear()
            with (
                patch.object(run_suite, "validate_configuration_files"),
                patch.object(run_suite, "validate_python_permissions"),
                patch.object(run_suite, "run_step", side_effect=record),
            ):
                run_suite.run_full(root, "python", None)
            coverage = next(command for name, command, _ in calls if name == "Coverage policy")
            self.assertEqual(coverage[-1], "--skip-diff")

    def test_main_routes_profiles_and_reports_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with (
                patch.object(run_suite, "find_project_root", return_value=root),
                patch.object(run_suite, "run_fast") as fast,
                patch("sys.argv", ["run_suite", "fast"]),
            ):
                self.assertEqual(run_suite.main(), 0)
                fast.assert_called_once()

            with (
                patch.object(run_suite, "find_project_root", return_value=root),
                patch.object(run_suite, "run_full", side_effect=run_suite.QualityFailure("bad")),
                patch("sys.argv", ["run_suite", "full", "--coverage-base", "base"]),
            ):
                self.assertEqual(run_suite.main(), 1)


if __name__ == "__main__":
    unittest.main()
