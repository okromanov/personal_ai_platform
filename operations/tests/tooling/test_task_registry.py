from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from operations.scripts.tasks.generate import collect_tasks, render_task_index


class TaskRegistryTests(unittest.TestCase):
    @staticmethod
    def _write_task(
        root: Path,
        task_id: str,
        state: str,
        *,
        depends_on: str | None = None,
        suffix: str = "sample",
    ) -> None:
        number = task_id.removeprefix("TASK_").lower()
        dependency = f"depends_on:\n  - {depends_on}\n" if depends_on else ""
        blocker = "blocker: Проверяем порядок\n" if state == "blocked" else ""
        mark = "x" if state in {"completed", "cancelled"} else " "
        actor = "none" if state in {"completed", "cancelled"} else "agent"
        (root / f"work/tasks/task_{number}_{suffix}.md").write_text(
            "---\n"
            f"id: {task_id}\n"
            "type: task\n"
            f"title: {task_id}\n"
            f"work_state: {state}\n"
            "version: 1.0\n"
            f"{dependency}"
            f"{blocker}"
            f"next_actor: {actor}\n"
            "owner_action: none\n"
            f"allowed_paths:\n  - work/tasks/task_{number}_{suffix}.md\n"
            "---\n"
            f"# {task_id}\n\n## 5. План выполнения\n\n- [{mark}] Шаг\n",
            encoding="utf-8",
        )

    def test_test_traces_to_task_and_task_implements_requirements(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "work/tasks").mkdir(parents=True)
            (root / "work/tests").mkdir(parents=True)
            task_text = (
                "---\nid: TASK_0001\ntype: task\ntitle: Sample\nwork_state: in-progress\nversion: 1.0\n"
                "next_actor: agent\nowner_action: none\n"
                "traces_to:\n  - m01\nimplements:\n  - SYS_001\n---\n# TASK_0001 — Sample\n"
                "\n## 5. План выполнения\n\n- [ ] Шаг\n"
            )
            (root / "work/tasks/task_0001_sample.md").write_text(task_text, encoding="utf-8")
            (root / "work/tests/test_0001.md").write_text(
                "---\nid: TEST_0001\ntype: test\nspec_state: current\nversion: 1.0\ntraces_to:\n  - TASK_0001\nverifies:\n  - SYS_001\n---\n# TEST_0001 — Sample\n",
                encoding="utf-8",
            )
            state = collect_tasks(root)
            self.assertEqual(state["tasks"][0]["implements"], ["SYS_001"])
            self.assertEqual(state["tasks"][0]["tests"][0]["id"], "TEST_0001")
            index = render_task_index(root)
            self.assertIn("SYS_001", index)
            self.assertIn("TEST_0001", index)

    def test_duplicate_task_id_is_rejected_before_rendering(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "work/tasks").mkdir(parents=True)
            (root / "work/tests").mkdir(parents=True)
            task = (
                "---\nid: TASK_0001\ntype: task\ntitle: Sample\nwork_state: in-progress\nversion: 1.0\n"
                "next_actor: agent\nowner_action: none\nallowed_paths:\n  - work/tasks/**\n"
                "---\n# TASK_0001 — Sample\n\n## 5. План выполнения\n\n- [ ] Шаг\n"
            )
            (root / "work/tasks/task_0001_first.md").write_text(task, encoding="utf-8")
            (root / "work/tasks/task_0001_second.md").write_text(task, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Дублирующий TASK ID TASK_0001"):
                collect_tasks(root)

    def test_task_ids_must_be_continuous(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "work/tasks").mkdir(parents=True)
            (root / "work/tests").mkdir(parents=True)
            self._write_task(root, "TASK_0001", "completed")
            self._write_task(root, "TASK_0003", "planned", depends_on="TASK_0001")
            with self.assertRaisesRegex(ValueError, "без пропусков"):
                collect_tasks(root)

    def test_each_task_depends_on_immediate_predecessor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "work/tasks").mkdir(parents=True)
            (root / "work/tests").mkdir(parents=True)
            self._write_task(root, "TASK_0001", "completed")
            self._write_task(root, "TASK_0002", "completed", depends_on="TASK_0001")
            self._write_task(root, "TASK_0003", "planned", depends_on="TASK_0001")
            with self.assertRaisesRegex(ValueError, "непосредственно предыдущую TASK_0002"):
                collect_tasks(root)

    def test_completed_tasks_must_form_queue_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "work/tasks").mkdir(parents=True)
            (root / "work/tests").mkdir(parents=True)
            self._write_task(root, "TASK_0001", "planned")
            self._write_task(root, "TASK_0002", "completed", depends_on="TASK_0001")
            with self.assertRaisesRegex(ValueError, "непрерывное начало очереди"):
                collect_tasks(root)

    def test_only_one_task_can_be_active(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "work/tasks").mkdir(parents=True)
            (root / "work/tests").mkdir(parents=True)
            self._write_task(root, "TASK_0001", "in-progress")
            self._write_task(root, "TASK_0002", "blocked", depends_on="TASK_0001")
            with self.assertRaisesRegex(ValueError, "только одна активная TASK"):
                collect_tasks(root)


if __name__ == "__main__":
    unittest.main()
