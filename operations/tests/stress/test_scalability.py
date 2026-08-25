"""
Stress and scalability tests: verify that functions which loop over
milestones, tasks, or filesystem trees behave correctly (and reasonably
fast) as the input grows well beyond today's repository size.

These do not assert tight timing SLAs — they assert correctness at scale
and flag gross super-linear blowups (the kind that turns a 1s check into a
10-minute CI hang once the repository grows).
"""

from __future__ import annotations

import sys
import tempfile
import time
import unittest
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from operations.scripts.common.status_types import TaskItem
from operations.scripts.status.generate_project_status import (
    MILESTONE_WORK_STATES,
    collect_milestones,
)
from operations.scripts.tasks.generate import _validate_task_sequence


def _synthetic_milestones_md(count: int) -> str:
    """Build a milestones.md body with `count` well-formed milestone sections."""
    sections = []
    for index in range(1, count + 1):
        state = "completed" if index < count else "in-progress"
        sections.append(
            f"## m{index:02d} — Synthetic milestone {index}\n"
            f"- work_state: `{state}`\n"
            f"- scope: none\n\n"
            f"Body text for milestone {index}.\n"
        )
    return "\n".join(sections)


def _synthetic_task_item(number: int, *, work_state: str, depends_on: list[str]) -> TaskItem:
    return {
        "id": f"TASK_{number:03d}",
        "title": f"Synthetic task {number}",
        "work_state": work_state,
        "version": "1.0",
        "path": f"work/tasks/task_{number:03d}.md",
        "depends_on": depends_on,
        "traces_to": [],
        "implements": [],
        "component": "test",
        "allowed_paths": [],
        "blocker": "",
        "tests": [],
        "next_actor": "agent",
        "owner_action": "none",
        "owner_followups": [],
        "checklist": [],
        "steps_done": 0,
        "steps_total": 0,
        "steps_remaining": 0,
        "body": "",
    }


class MilestoneScalabilityTest(unittest.TestCase):
    """The m\\d{2} heading pattern caps milestones at 99 — verify the
    ceiling is handled correctly and parsing stays fast up to it."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def test_maximum_supported_milestone_count_parses_correctly(self) -> None:
        max_count = 99  # ceiling imposed by the m\d{2} pattern
        (self.root / "milestones.md").write_text(
            _synthetic_milestones_md(max_count), encoding="utf-8"
        )

        start = time.perf_counter()
        report = collect_milestones(self.root)
        duration = time.perf_counter() - start

        self.assertEqual(report["count"], max_count)
        self.assertEqual(report["items"][0]["id"], "m01")
        self.assertEqual(report["items"][-1]["id"], f"m{max_count:02d}")
        for item in report["items"]:
            self.assertIn(item["work_state"], MILESTONE_WORK_STATES)
        self.assertLess(duration, 1.0, f"Parsing {max_count} milestones took {duration:.3f}s")

    def test_scaling_from_10_to_90_milestones_stays_roughly_linear(self) -> None:
        small_root = self.root / "small"
        large_root = self.root / "large"
        small_root.mkdir()
        large_root.mkdir()
        (small_root / "milestones.md").write_text(_synthetic_milestones_md(10), encoding="utf-8")
        (large_root / "milestones.md").write_text(_synthetic_milestones_md(90), encoding="utf-8")

        start = time.perf_counter()
        collect_milestones(small_root)
        small_duration = time.perf_counter() - start

        start = time.perf_counter()
        collect_milestones(large_root)
        large_duration = time.perf_counter() - start

        # 9x the input should not take more than ~50x the time even with
        # process/filesystem noise on a small, fast operation.
        self.assertLess(
            large_duration,
            max(small_duration * 50, 0.2),
            f"9x milestones took {large_duration:.4f}s vs {small_duration:.4f}s for 1x",
        )


class TaskSequenceScalabilityTest(unittest.TestCase):
    """_validate_task_sequence is pure and disk-free, so it can be stress
    tested with far more items than the m\\d{2} milestone ceiling allows."""

    def test_large_valid_chain_validates_without_error(self) -> None:
        count = 5000
        items = []
        previous_id: str | None = None
        for number in range(1, count + 1):
            depends_on = [previous_id] if previous_id else []
            items.append(
                _synthetic_task_item(number, work_state="completed", depends_on=depends_on)
            )
            previous_id = f"TASK_{number:03d}"
        # Last task must be the only non-terminal one to satisfy the
        # "single active task" invariant.
        items[-1]["work_state"] = "in-progress"

        start = time.perf_counter()
        _validate_task_sequence(items)  # must not raise
        duration = time.perf_counter() - start

        self.assertLess(duration, 2.0, f"Validating {count} tasks took {duration:.3f}s")

    def test_large_chain_with_single_broken_link_is_detected(self) -> None:
        count = 2000
        items = []
        previous_id: str | None = None
        for number in range(1, count + 1):
            depends_on = [previous_id] if previous_id else []
            items.append(
                _synthetic_task_item(number, work_state="completed", depends_on=depends_on)
            )
            previous_id = f"TASK_{number:03d}"
        items[-1]["work_state"] = "in-progress"

        # Break a single dependency link deep in the middle of a large chain.
        items[count // 2]["depends_on"] = []

        with self.assertRaises(ValueError):
            _validate_task_sequence(items)

    def test_multiple_active_tasks_detected_even_at_scale(self) -> None:
        count = 3000
        items = []
        previous_id: str | None = None
        for number in range(1, count + 1):
            depends_on = [previous_id] if previous_id else []
            state = "in-progress" if number in (count // 3, count // 2) else "completed"
            items.append(_synthetic_task_item(number, work_state=state, depends_on=depends_on))
            previous_id = f"TASK_{number:03d}"

        with self.assertRaises(ValueError):
            _validate_task_sequence(items)


class DirectoryTreeScalabilityTest(unittest.TestCase):
    """Filesystem-scanning helpers must survive a repository with a much
    larger number of files than exist today without pathological slowdown."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def test_deep_and_wide_tree_traversal_is_fast(self) -> None:
        # 20 directories x 100 files = 2000 files, deeper than today's tree.
        for dir_index in range(20):
            sub = self.root / f"module_{dir_index}"
            sub.mkdir()
            for file_index in range(100):
                (sub / f"item_{file_index}.txt").write_text("x", encoding="utf-8")

        start = time.perf_counter()
        all_paths = list(self.root.rglob("*"))
        duration = time.perf_counter() - start

        self.assertEqual(len(all_paths), 20 + 20 * 100)
        self.assertLess(duration, 2.0, f"Scanning 2000+ paths took {duration:.3f}s")


if __name__ == "__main__":
    unittest.main()
