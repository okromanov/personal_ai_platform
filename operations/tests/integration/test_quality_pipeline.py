"""
Integration tests for quality check pipeline.

Verifies that multiple quality checks work together correctly.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


class QualityPipelineIntegrationTest(unittest.TestCase):
    """Test the full quality pipeline works end-to-end."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.project_root = Path(__file__).resolve().parents[3]
        cls.runtime_dir = cls.project_root / "runtime"
        cls.runtime_dir.mkdir(exist_ok=True)

    def test_code_analyzer_produces_valid_json(self) -> None:
        """Verify code_analyzer.py produces valid JSON output."""
        result = subprocess.run(
            [
                sys.executable,
                "operations/scripts/quality/code_analyzer.py",
            ],
            cwd=self.project_root,
            capture_output=True,
            text=True,
        )

        # Should produce valid JSON
        report = json.loads(result.stdout)
        self.assertIn("summary", report)
        self.assertIn("files_analyzed", report["summary"])
        self.assertIn("critical_issues", report["summary"])
        self.assertIn("findings", report)

    def test_code_analyzer_finds_issues_or_clean(self) -> None:
        """Verify code_analyzer runs without exceptions."""
        result = subprocess.run(
            [
                sys.executable,
                "operations/scripts/quality/code_analyzer.py",
            ],
            cwd=self.project_root,
            capture_output=True,
            text=True,
        )

        # Exit code 0 = no critical issues, 1 = critical issues found
        self.assertIn(result.returncode, [0, 1])
        self.assertEqual(result.stderr, "")

    def test_ruff_integration(self) -> None:
        """Verify Ruff linter works with project configuration."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "ruff",
                "check",
                "operations/scripts",
                "--select=E,F,I,W",
            ],
            cwd=self.project_root,
            capture_output=True,
            text=True,
        )

        # Ruff should run successfully
        self.assertIn(result.returncode, [0, 1])

    def test_bandit_runs_without_errors(self) -> None:
        """Verify Bandit SAST scanner is functional."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "bandit",
                "-r",
                "operations/scripts",
                "--severity-level",
                "high",
                "-f",
                "json",
            ],
            cwd=self.project_root,
            capture_output=True,
            text=True,
        )

        # Exit code 0 = no issues, 1 = issues found
        self.assertIn(result.returncode, [0, 1])

        # Should produce valid JSON
        if result.stdout:
            report = json.loads(result.stdout)
            self.assertIn("results", report)

    def test_vulture_runs_without_errors(self) -> None:
        """Verify Vulture dead code detection works."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "vulture",
                "operations/scripts",
                "--min-confidence",
                "80",
            ],
            cwd=self.project_root,
            capture_output=True,
            text=True,
        )

        # Vulture should run (exit code indicates found/not found)
        self.assertIn(result.returncode, [0, 1])

    def test_mypy_type_checking_integration(self) -> None:
        """Verify mypy baseline checking works."""
        result = subprocess.run(
            [
                sys.executable,
                "operations/scripts/quality/run_mypy_baseline.py",
            ],
            cwd=self.project_root,
            capture_output=True,
            text=True,
        )

        # Exit code 0 = no regression, 1 = regression found, 2+ = tool error
        self.assertIn(result.returncode, [0, 1])


if __name__ == "__main__":
    unittest.main()
