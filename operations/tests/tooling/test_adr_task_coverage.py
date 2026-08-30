from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from operations.scripts.traceability.adr_task_coverage import (
    validate_adr_decision_tasks,
)


class AdrDecisionTaskCoverageTests(unittest.TestCase):
    def _root(self) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        (root / "adr").mkdir()
        (root / "work" / "tasks").mkdir(parents=True)
        return root

    @staticmethod
    def _milestones(
        root: Path,
        m02_state: str = "in-progress",
        m04_state: str = "planned",
    ) -> None:
        (root / "milestones.md").write_text(
            f"## m02 — Current\n\n- work_state: `{m02_state}`\n"
            f"\n## m04 — Future\n\n- work_state: `{m04_state}`\n",
            encoding="utf-8",
        )

    @staticmethod
    def _adr(root: Path, adr_id: str, milestone: str, state: str = "proposed") -> None:
        number = adr_id.removeprefix("ADR_").lower()
        (root / "adr" / f"adr_{number}.md").write_text(
            "---\n"
            f"id: {adr_id}\n"
            "type: adr\n"
            f"decision_state: {state}\n"
            "version: 1.0\n"
            "updated: 2026-08-29\n"
            "traces_to:\n"
            f"  - {milestone}\n"
            "---\n"
            f"# {adr_id} — Decision\n",
            encoding="utf-8",
        )

    @staticmethod
    def _task(
        root: Path,
        task_id: str,
        milestone: str,
        *,
        state: str = "planned",
        decides: tuple[str, ...] = (),
    ) -> None:
        number = task_id.removeprefix("TASK_").lower()
        decision_block = "decides:\n" + "".join(f"  - {item}\n" for item in decides)
        (root / "work" / "tasks" / f"task_{number}.md").write_text(
            "---\n"
            f"id: {task_id}\n"
            "type: task\n"
            f"work_state: {state}\n"
            "traces_to:\n"
            f"  - {milestone}\n"
            f"{decision_block}"
            "---\n"
            f"# {task_id} — Work\n",
            encoding="utf-8",
        )

    def test_active_proposed_adr_requires_one_unfinished_decision_task(self) -> None:
        root = self._root()
        self._milestones(root)
        self._adr(root, "ADR_006", "m02")
        self.assertRegex(
            validate_adr_decision_tasks(root)[0],
            "ровно одну незавершённую TASK",
        )

    def test_active_proposed_adr_with_one_matching_task_passes(self) -> None:
        root = self._root()
        self._milestones(root)
        self._adr(root, "ADR_006", "m02")
        self._task(root, "TASK_014", "m02", decides=("ADR_006",))
        self.assertEqual(validate_adr_decision_tasks(root), [])

    def test_completed_task_cannot_leave_adr_proposed(self) -> None:
        root = self._root()
        self._milestones(root)
        self._adr(root, "ADR_006", "m02")
        self._task(root, "TASK_014", "m02", state="completed", decides=("ADR_006",))
        errors = validate_adr_decision_tasks(root)
        self.assertTrue(any("ровно одну незавершённую TASK" in error for error in errors))
        self.assertTrue(any("не может оставлять ADR_006" in error for error in errors))

    def test_duplicate_decision_owners_are_rejected(self) -> None:
        root = self._root()
        self._milestones(root)
        self._adr(root, "ADR_006", "m02")
        self._task(root, "TASK_014", "m02", decides=("ADR_006",))
        self._task(root, "TASK_015", "m02", decides=("ADR_006",))
        self.assertRegex(validate_adr_decision_tasks(root)[0], "ровно одну незавершённую TASK")

    def test_task_must_share_active_milestone_with_adr(self) -> None:
        root = self._root()
        self._milestones(root, m04_state="in-progress")
        self._adr(root, "ADR_008", "m04")
        self._task(root, "TASK_018", "m02", decides=("ADR_008",))
        self.assertRegex(validate_adr_decision_tasks(root)[0], "должна traces_to")

    def test_future_planned_milestone_is_deferred_until_decomposition(self) -> None:
        root = self._root()
        self._milestones(root)
        self._adr(root, "ADR_008", "m04")
        self.assertEqual(validate_adr_decision_tasks(root), [])

    def test_unknown_adr_reference_is_rejected(self) -> None:
        root = self._root()
        self._milestones(root)
        self._task(root, "TASK_014", "m02", decides=("ADR_999",))
        self.assertEqual(
            validate_adr_decision_tasks(root),
            ["TASK_014: decides ссылается на неизвестный ADR_999"],
        )


if __name__ == "__main__":
    unittest.main()
