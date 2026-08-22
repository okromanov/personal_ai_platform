from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from operations.scripts.common.project import CommandResult
from operations.scripts.quality import check_coverage


def report(percent: float = 95.0) -> dict[str, object]:
    return {
        "totals": {"percent_covered": percent},
        "files": {
            "operations/scripts/critical.py": {
                "summary": {"percent_covered": 90.0},
                "executed_lines": [1, 2, 4],
                "missing_lines": [3],
            }
        },
    }


class CoveragePolicyTests(unittest.TestCase):
    def test_parse_changed_lines_handles_new_modified_empty_and_deleted_hunks(self) -> None:
        diff = """diff --git a/operations/scripts/a.py b/operations/scripts/a.py
--- a/operations/scripts/a.py
+++ b/operations/scripts/a.py
@@ -1,2 +1,3 @@
+line
diff --git a/operations/scripts/new.py b/operations/scripts/new.py
--- /dev/null
+++ b/operations/scripts/new.py
@@ -0,0 +10,2 @@
+one
+two
diff --git a/deleted.py b/deleted.py
--- a/deleted.py
+++ /dev/null
@@ -1 +0,0 @@
"""
        self.assertEqual(
            check_coverage.parse_changed_lines(diff),
            {
                "operations/scripts/a.py": {1, 2, 3},
                "operations/scripts/new.py": {10, 11},
            },
        )

    def test_evaluate_passes_aggregate_module_and_diff_thresholds(self) -> None:
        errors, rows = check_coverage.evaluate_coverage(
            report(),
            {"overall": 75, "diff": 60, "modules": {"operations/scripts/critical.py": 85}},
            {"operations/scripts/critical.py": {1, 2, 3, 100}},
        )
        self.assertEqual(errors, [])
        self.assertTrue(any("2/3" in row for row in rows))

    def test_evaluate_fails_missing_schema_modules_and_uncovered_diff(self) -> None:
        errors, _ = check_coverage.evaluate_coverage(
            {"totals": {"percent_covered": 50}, "files": {}},
            {
                "overall": 75,
                "diff": 90,
                "modules": {"operations/scripts/missing.py": 85},
            },
            {"operations/scripts/new.py": {1}},
        )
        joined = "\n".join(errors)
        self.assertIn("Общее покрытие", joined)
        self.assertIn("Критический модуль отсутствует", joined)
        self.assertIn("Изменённый Python-модуль отсутствует", joined)

        errors, _ = check_coverage.evaluate_coverage(
            report(),
            {"modules": []},
            None,
        )
        self.assertIn("modules должна", "\n".join(errors))
        errors, _ = check_coverage.evaluate_coverage({}, {}, None)
        self.assertIn("totals/files", errors[0])

    def test_changed_lines_fails_closed_when_git_diff_fails(self) -> None:
        failure = CommandResult(("git",), 1, "", "bad revision")
        with patch.object(check_coverage, "run_command", return_value=failure):
            with self.assertRaisesRegex(ValueError, "bad revision"):
                check_coverage.changed_lines(Path("."), "missing")

    def test_load_policy_and_main_success_and_failure_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text(
                "[tool.personal_ai_platform.coverage]\n"
                "overall = 75\n"
                "diff = 90\n"
                "[tool.personal_ai_platform.coverage.modules]\n"
                '"operations/scripts/critical.py" = 85\n',
                encoding="utf-8",
            )
            coverage_path = root / "coverage.json"
            coverage_path.write_text(json.dumps(report()), encoding="utf-8")
            self.assertEqual(check_coverage.load_policy(root)["overall"], 75)

            with (
                patch.object(check_coverage, "find_project_root", return_value=root),
                patch(
                    "sys.argv",
                    ["check_coverage", "--coverage-json", "coverage.json", "--skip-diff"],
                ),
            ):
                self.assertEqual(check_coverage.main(), 0)

            coverage_path.write_text("{", encoding="utf-8")
            with (
                patch.object(check_coverage, "find_project_root", return_value=root),
                patch(
                    "sys.argv",
                    ["check_coverage", "--coverage-json", "coverage.json", "--skip-diff"],
                ),
            ):
                self.assertEqual(check_coverage.main(), 1)

            with (
                patch.object(check_coverage, "find_project_root", return_value=root),
                patch("sys.argv", ["check_coverage", "--coverage-json", "missing.json"]),
            ):
                self.assertEqual(check_coverage.main(), 1)

            (root / "pyproject.toml").write_text("[tool]\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Отсутствует"):
                check_coverage.load_policy(root)


if __name__ == "__main__":
    unittest.main()
