from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from operations.scripts.quality.registry import uncovered_paths
from operations.scripts.status.generate_project_status import _change_scope, _coverage


class ScopeCoverageTests(unittest.TestCase):
    def test_m01_scope_uses_entire_tracked_tree_not_only_last_commit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def git(*args: str) -> None:
                subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)

            git("init", "-b", "main")
            git("config", "user.name", "Test")
            git("config", "user.email", "test@example.invalid")
            (root / "allowed.md").write_text("baseline\n", encoding="utf-8")
            git("add", "allowed.md")
            git("commit", "-m", "baseline")
            (root / "rogue.py").write_text("print('outside profile')\n", encoding="utf-8")
            git("add", "rogue.py")
            git("commit", "-m", "unprofiled file")
            (root / "allowed.md").write_text("final\n", encoding="utf-8")
            git("add", "allowed.md")
            git("commit", "-m", "allowed final change")

            scope = _change_scope(root, "m01")
            gaps = uncovered_paths([("foundation", {"paths": ["*.md"]})], list(scope["paths"]))

            self.assertEqual(scope["mode"], "tracked_tree")
            self.assertIn("rogue.py", scope["paths"])
            self.assertEqual(gaps, ["rogue.py"])

    def test_task_test_mode_blocks_uncovered_scope_and_task_implements(self) -> None:
        current = {"scope": ["SYS_001"]}
        profiles = [("feature", {"scope_coverage": "task_test"})]
        missing = _coverage(
            current=current,
            current_tasks=[],
            effective_tests=[],
            profiles=profiles,
            evidence={},
        )
        self.assertEqual(missing["scope_covered"], 0)
        self.assertTrue(any("SYS_001" in item for item in missing["blockers"]))

        tasks = [{"id": "TASK_0001", "implements": ["SYS_001"]}]
        tests = [
            {
                "id": "TEST_0001",
                "effective_result": "passed",
                "traces_to": ["TASK_0001"],
                "verifies": ["SYS_001"],
            }
        ]
        covered = _coverage(
            current=current,
            current_tasks=tasks,
            effective_tests=tests,
            profiles=profiles,
            evidence={},
        )
        self.assertEqual(covered["scope_covered"], 1)
        self.assertEqual(covered["blockers"], [])

    def test_global_evidence_covers_scope_only_when_passed(self) -> None:
        current = {"scope": ["SYS_001", "SYS_002"]}
        profiles = [
            (
                "foundation",
                {"scope_coverage": "global_evidence", "scope_evidence": ["project_checks"]},
            )
        ]
        failed = _coverage(
            current=current,
            current_tasks=[],
            effective_tests=[],
            profiles=profiles,
            evidence={"project_checks": {"result": "failed"}},
        )
        self.assertEqual(failed["scope_covered"], 0)
        self.assertTrue(failed["blockers"])

        passed = _coverage(
            current=current,
            current_tasks=[],
            effective_tests=[],
            profiles=profiles,
            evidence={"project_checks": {"result": "passed"}},
        )
        self.assertEqual(passed["scope_covered"], 2)
        self.assertEqual(passed["blockers"], [])

    def test_foundation_paths_replace_empty_product_scope_in_status_counts(self) -> None:
        profiles = [
            (
                "foundation",
                {
                    "paths": ["*.md", "operations/**"],
                    "scope_coverage": "global_evidence",
                    "scope_evidence": ["project_checks"],
                },
            )
        ]
        result = _coverage(
            current={"scope": []},
            current_tasks=[],
            effective_tests=[],
            profiles=profiles,
            evidence={"project_checks": {"result": "passed"}},
        )

        self.assertEqual(result["scope_total"], 0)
        self.assertEqual(result["tracked_kind"], "foundation_paths")
        self.assertEqual(result["tracked_targets"], ["path:*.md", "path:operations/**"])
        self.assertEqual(result["tracked_covered"], 2)
        self.assertEqual(result["tracked_total"], 2)


if __name__ == "__main__":
    unittest.main()
