from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from operations.scripts.documents.check import run_all_checks
from operations.scripts.documents.generate import generate_all


class GenerationSafetyTests(unittest.TestCase):
    def test_renderer_failure_does_not_partially_write_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            real_root = Path(__file__).resolve().parents[2]
            # Copy required source files to temp directory
            (root / "milestones.md").write_text(
                (real_root / "milestones.md").read_text(encoding="utf-8-sig"), encoding="utf-8"
            )
            (root / "tasks.md").write_text("old tasks\n", encoding="utf-8")
            (root / "project_status.md").write_text("old status\n", encoding="utf-8")
            (root / "generated").mkdir(parents=True, exist_ok=True)
            with (
                patch(
                    "operations.scripts.documents.generate.render_task_index",
                    return_value="new tasks\n",
                ),
                patch(
                    "operations.scripts.documents.generate.render_repository_project_status",
                    return_value="new status\n",
                ),
                patch(
                    "operations.scripts.documents.generate.render_index", return_value="new index\n"
                ),
                patch(
                    "operations.scripts.documents.generate.render_traceability",
                    side_effect=ValueError("duplicate"),
                ),
            ):
                with self.assertRaisesRegex(ValueError, "duplicate"):
                    generate_all(root)
            self.assertEqual((root / "tasks.md").read_text(encoding="utf-8"), "old tasks\n")
            self.assertEqual(
                (root / "project_status.md").read_text(encoding="utf-8"), "old status\n"
            )

    def test_checker_exception_is_localized_and_other_checks_continue(self) -> None:
        root = Path(__file__).resolve().parents[2]
        with patch(
            "operations.scripts.documents.check.check_structure", side_effect=RuntimeError("boom")
        ):
            results = run_all_checks(root)
        by_name = {result.name: result for result in results}
        self.assertIn("structure", by_name)
        self.assertIn("secrets", by_name)
        self.assertFalse(by_name["structure"].ok)
        self.assertIn("RuntimeError: boom", by_name["structure"].errors[0])


if __name__ == "__main__":
    unittest.main()
