from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from operations.scripts.milestones.init_milestone import init_milestone
from operations.scripts.milestones.update_completion_report import (
    update_completion_report,
)


class InitMilestoneTests(unittest.TestCase):
    def test_creates_all_three_milestone_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertTrue(init_milestone("m09", root=root))

            milestone_dir = root / "work" / "m09"
            self.assertTrue((milestone_dir / "owner_checklist.md").exists())
            self.assertTrue((milestone_dir / "semantic_review.md").exists())
            self.assertTrue((milestone_dir / "final_report.md").exists())

    def test_checklist_frontmatter_references_milestone(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_milestone("m03", root=root)

            checklist = (root / "work" / "m03" / "owner_checklist.md").read_text(encoding="utf-8")
            self.assertIn("id: m03_owner_checklist", checklist)
            self.assertIn("milestone: m03", checklist)
            self.assertIn("acceptance_state: pending", checklist)

    def test_final_report_starts_pending(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_milestone("m04", root=root)

            report = (root / "work" / "m04" / "final_report.md").read_text(encoding="utf-8")
            self.assertIn("completion_state: pending", report)
            self.assertIn("Все задачи завершены: нет", report)

    def test_does_not_overwrite_existing_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            init_milestone("m05", root=root)
            checklist_path = root / "work" / "m05" / "owner_checklist.md"
            checklist_path.write_text("custom content", encoding="utf-8")

            init_milestone("m05", root=root)

            self.assertEqual(checklist_path.read_text(encoding="utf-8"), "custom content")


class UpdateCompletionReportTests(unittest.TestCase):
    def _write_pending_report(self, root: Path, milestone_id: str) -> Path:
        report_dir = root / "work" / milestone_id
        report_dir.mkdir(parents=True)
        report_path = report_dir / "final_report.md"
        report_path.write_text(
            "---\n"
            f"id: {milestone_id}_final_report\n"
            "completion_state: pending\n"
            "version: 1.0\n"
            "updated: 2026-01-01\n"
            "---\n\n"
            "## 1. Состояние завершения\n\n"
            "- Статус: в процессе\n"
            "- Дата начала: 2026-01-01\n"
            "- Дата завершения: —\n"
            "- Все задачи завершены: нет\n",
            encoding="utf-8",
        )
        return report_path

    def test_marks_report_completed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_path = self._write_pending_report(root, "m06")

            self.assertTrue(update_completion_report("m06", root=root))

            content = report_path.read_text(encoding="utf-8")
            self.assertIn("completion_state: completed", content)
            self.assertIn("- Статус: завершено", content)
            self.assertIn("- Все задачи завершены: да", content)
            self.assertNotIn("Дата завершения: —", content)

    def test_returns_false_when_report_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertFalse(update_completion_report("m07", root=root))

    def test_updates_metadata_date(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_path = self._write_pending_report(root, "m08")

            update_completion_report("m08", root=root)

            content = report_path.read_text(encoding="utf-8")
            self.assertNotIn("updated: 2026-01-01", content)


if __name__ == "__main__":
    unittest.main()
