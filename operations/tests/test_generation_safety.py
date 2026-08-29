from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from operations.scripts.common.project import atomic_write_generated, read_text
from operations.scripts.documents.check import run_all_checks
from operations.scripts.documents.generate import generate_all


class GenerationSafetyTests(unittest.TestCase):
    def test_renderer_failure_does_not_partially_write_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "project_status.md").write_text("old status\n", encoding="utf-8")
            with patch(
                "operations.scripts.documents.generate.render_repository_project_status",
                side_effect=ValueError("duplicate"),
            ):
                with self.assertRaisesRegex(ValueError, "duplicate"):
                    generate_all(root)
            self.assertEqual(
                (root / "project_status.md").read_text(encoding="utf-8"), "old status\n"
            )
            self.assertFalse((root / "generated").exists())

    def test_generated_snapshot_is_stable_until_content_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "generated.md"
            rendered = "---\ngeneration_state: generated\n---\n\n# Report\n"
            self.assertTrue(atomic_write_generated(path, rendered))
            first = read_text(path)
            self.assertRegex(first, r"(?m)^generated_at: .+$")
            self.assertFalse(atomic_write_generated(path, rendered))
            self.assertEqual(read_text(path), first)
            self.assertTrue(atomic_write_generated(path, rendered + "\nChanged.\n"))
            self.assertNotEqual(read_text(path), first)

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
