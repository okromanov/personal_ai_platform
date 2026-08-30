from __future__ import annotations

import re
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from operations.scripts.common.status_types import MilestoneItem, TaskItem
from operations.scripts.documents.check import check_structure
from operations.scripts.documents.metadata import load_document
from operations.scripts.status.generate_project_status import (
    AcceptanceResult,
    CoverageResult,
    ProgressSnapshot,
    build_owner_next_action,
    collect_milestones,
    render_progress_sections,
)
from operations.scripts.status.human_status import (
    _rebase_relative_links,
    render_repository_project_status,
)
from operations.scripts.tasks.generate import _owner_followups, collect_tasks, select_current_task


def _task_item(
    task_id: str, work_state: str, *, traces_to: list[str], owner_action: str
) -> TaskItem:
    return {
        "id": task_id,
        "title": task_id,
        "work_state": work_state,
        "version": "1.0",
        "path": f"work/tasks/{task_id.lower()}.md",
        "depends_on": [],
        "traces_to": traces_to,
        "implements": [],
        "component": "",
        "delivery_role": "component",
        "allowed_paths": [],
        "blocker": "",
        "tests": [],
        "next_actor": "agent",
        "owner_action": owner_action,
        "owner_followups": [],
        "checklist": [],
        "steps_done": 0,
        "steps_total": 0,
        "steps_remaining": 0,
        "body": "",
    }


class OwnerUsabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[2]

    def test_repository_maintenance_does_not_remain_in_project_task_queue(self) -> None:
        raw_tasks = collect_tasks(self.root)["tasks"]
        self.assertIsInstance(raw_tasks, list)
        tasks = (
            [task for task in raw_tasks if isinstance(task, dict)]
            if isinstance(raw_tasks, list)
            else []
        )
        rendered = (self.root / "project_status.md").read_text(encoding="utf-8-sig")
        current = collect_milestones(self.root)["current"]
        self.assertIsInstance(current, dict)
        current_id = str(current["id"]) if isinstance(current, dict) else ""
        if current_id == "m01":
            self.assertEqual(tasks, [])
            self.assertIn("Сейчас проектных TASK нет", rendered)
        for maintenance_title in [
            "Перестроить систему источников истины",
            "Закрепить проверяемые границы изменений",
            "Упорядочить очередь задач",
            "Включить и проверить защиту main",
        ]:
            self.assertNotIn(maintenance_title, rendered)
            self.assertTrue(all(maintenance_title not in str(task["title"]) for task in tasks))

    def test_project_status_is_detailed_without_artificial_percentages(self) -> None:
        rendered = render_repository_project_status(self.root)
        tracked = (self.root / "project_status.md").read_text(encoding="utf-8-sig")
        current_id = str(collect_milestones(self.root)["current"]["id"])
        current_task = select_current_task(collect_tasks(self.root)["tasks"], current_id)
        resume_target = str(current_task["id"]) if current_task else current_id
        tracked_without_generated_at = re.sub(r"(?m)^generated_at: .+\n", "", tracked)
        self.assertEqual(tracked_without_generated_at.strip(), rendered.strip())
        for text in [
            "Ваше действие сейчас",
            f"ПРОДОЛЖАЙ {resume_target}",
            "Следующий исполнитель",
            "Этапы V1",
            "Проектные задачи текущего этапа",
            "Шаги текущей работы",
            "Контроль результатов аудита",
            "Исправлены, ожидают проверки",
            "work/audit/audit_register.md",
            "выполнено",
            "осталось",
            "[x]",
            "[ ]",
        ]:
            self.assertIn(text, rendered)
        for removed_text in [
            "Что произойдёт после вашей команды",
            "Когда потребуется ваше участие",
            "Общая картина V1",
            "Что уже умеет решение",
        ]:
            self.assertNotIn(removed_text, rendered)
        self.assertLess(
            rendered.index(f"ПРОДОЛЖАЙ {resume_target}"), rendered.index("Текущее состояние")
        )
        self.assertIn("Вам не нужно запускать проверки", rendered)
        if current_id == "m01" and current_task is None:
            self.assertIn("откройте новый сеанс агента", rendered)
            self.assertIn("Проектных TASK нет", rendered)
        self.assertNotIn("Сейчас от вас ничего не требуется", rendered)
        self.assertNotIn("%", rendered)
        for internal in [
            "in-review",
            "in-progress",
            "owner_action",
            "PowerShell",
            "Git SHA",
            "evidence bundle",
        ]:
            self.assertNotIn(internal, rendered)
        # Per-file deliverables stay in TASK allowed_paths and composition;
        # project_status.md does not duplicate that inventory.
        self.assertNotIn("Файлы, созданные в рамках задач", rendered)

    def test_first_unfinished_task_is_selected_by_queue_order(self) -> None:
        tasks = [
            _task_item("TASK_001", "planned", traces_to=["m01"], owner_action="none"),
            _task_item("TASK_002", "blocked", traces_to=["m01"], owner_action="none"),
        ]
        current = select_current_task(tasks, "m01")
        assert current is not None
        self.assertEqual(current["id"], "TASK_001")

    def test_technical_status_has_one_russian_owner_action_and_real_foundation_count(self) -> None:
        action = build_owner_next_action(
            "m01",
            resume_target="m01",
            requires_fresh_session=True,
        )
        current: MilestoneItem = {
            "id": "m01",
            "title": "Основа",
            "work_state": "in-progress",
            "scope": [],
            "result": "",
        }
        next_milestone: MilestoneItem = {
            "id": "m02",
            "title": "Следующий этап",
            "work_state": "planned",
            "scope": [],
            "result": "",
        }
        coverage: CoverageResult = {
            "scope_total": 0,
            "scope_covered": 0,
            "scope": [],
            "covered": [],
            "tracked_kind": "foundation_paths",
            "tracked_total": 7,
            "tracked_covered": 7,
            "tracked_targets": [f"path:foundation_{n}" for n in range(7)],
            "blockers": [],
            "modes": ["global_evidence"],
        }
        acceptance: AcceptanceResult = {
            "state": "ready-for-semantic-review",
            "technical_ready": True,
            "accepted": False,
            "pending_gates": ["semantic_review"],
            "owner_action": "none",
            "tasks_total": 3,
            "tasks_verified": 3,
            "tests_total": 3,
            "tests_passed": 3,
            "tests": [],
            "quality": {
                "profiles": [],
                "evidence": [],
                "blockers": [],
                "warnings": [],
                "ready": True,
            },
            "coverage": coverage,
            "evidence_results": {},
            "evidence_context": {},
            "changed_paths": [],
            "coverage_base": {"mode": "tracked_tree", "git_sha": None},
            "uncovered_paths": [],
            "impacted_profiles": ["foundation"],
            "documents_total": 12,
            "documents_current": 12,
            "decisions_proposed": 4,
            "remaining": [],
            "blockers": [],
        }
        snapshot: ProgressSnapshot = {
            "overall": "healthy",
            "milestones": {
                "count": 2,
                "items": [current, next_milestone],
                "current": current,
                "states": {"in-progress": 1, "planned": 1},
            },
            "current": current,
            "next_milestone": next_milestone,
            "tasks": {"count": 0, "states": {}, "tasks": []},
            "tests": {"count": 0, "items": [], "states": {}},
            "checks_passed": 16,
            "checks_total": 16,
            "check_summary": {"ok": True, "checks": []},
            "unit": {
                "ok": True,
                "total": 40,
                "passed": 40,
                "failed": 0,
                "duration": 0.3,
                "label": "40/40 PASS",
                "problems": [],
            },
            "acceptance": acceptance,
            "deviations": [],
            "next_action": action,
            "git": {"commit": "a" * 40},
        }
        rendered = render_progress_sections(snapshot)

        self.assertIn("| Области основы | `7/7` |", rendered)
        self.assertIn("Откройте новый сеанс агента", rendered)
        self.assertIn("`ПРОДОЛЖАЙ m01`", rendered)
        for stale_label in [
            "Scope coverage",
            "Overall",
            "Project checks",
            "Unit tests",
            "- AUTO:",
            "- OWNER:",
            "in-progress",
            "ready-for-semantic-review",
            "semantic_review",
            "`foundation`",
        ]:
            self.assertNotIn(stale_label, rendered)

    def test_project_status_is_the_only_owner_entrypoint(self) -> None:
        root_entry_names = {path.name.lower() for path in self.root.iterdir()}
        self.assertNotIn("readme.md", root_entry_names)
        self.assertIn("agents.md", root_entry_names)
        self.assertIn("project_status.md", root_entry_names)

        project_status = (self.root / "project_status.md").read_text(encoding="utf-8-sig")
        self.assertIn("Это основной экран владельца", project_status)

        with TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            (temporary_root / "README.md").write_text("лишний файл", encoding="utf-8")
            errors = check_structure(temporary_root).errors
            self.assertTrue(any("README запрещён решением владельца" in error for error in errors))

        for forbidden_name, expected_error in [
            ("README", "README запрещён решением владельца"),
        ]:
            with TemporaryDirectory() as temporary_directory:
                temporary_root = Path(temporary_directory)
                (temporary_root / forbidden_name).write_text("лишний файл", encoding="utf-8")
                errors = check_structure(temporary_root).errors
                self.assertTrue(any(expected_error in error for error in errors))

    def test_project_status_shows_exact_decision_when_owner_is_next(self) -> None:
        milestone = {"id": "m01", "title": "Основа", "work_state": "in-progress"}
        task = {
            "id": "TASK_003",
            "title": "Подготовить решение",
            "path": "work/tasks/task_003_finish_m01.md",
            "traces_to": ["m01"],
            "work_state": "in-progress",
            "next_actor": "owner",
            "owner_action": "ПРИНИМАЮ m01",
            "body": "## Что делать сейчас\n\n### Владельцу\n\nПРИНИМАЮ m01",
            "checklist": [{"done": True, "text": "Проверки завершены"}],
            "steps_done": 1,
            "steps_remaining": 0,
        }
        with (
            patch(
                "operations.scripts.status.human_status.collect_milestones",
                return_value={"items": [milestone], "current": milestone},
            ),
            patch(
                "operations.scripts.status.human_status.collect_tasks",
                return_value={"tasks": [task]},
            ),
            patch(
                "operations.scripts.status.human_status._task_context",
                return_value=task,
            ),
        ):
            rendered = render_repository_project_status(self.root)

        self.assertIn("Сейчас требуется ваше решение", rendered)
        self.assertIn("ПРИНИМАЮ m01", rendered)
        self.assertIn("ВОЗВРАЩАЮ m01: <что исправить>", rendered)
        self.assertNotIn("Сейчас от вас ничего не требуется", rendered)

    def test_test_specs_keep_owner_steps_safe_and_only_when_manual(self) -> None:
        for path in sorted((self.root / "work/tests").glob("test_*.md")):
            doc = load_document(path)
            self.assertNotIn("Пошаговая инструкция", doc.body)
            if doc.metadata.get("execution") == "automated":
                self.assertIn("Автоматический запуск", doc.body)
                self.assertIn("Действия владельца не требуются", doc.body)
                self.assertNotIn("## 3. Действия владельца", doc.body)
            else:
                self.assertEqual(doc.metadata.get("execution"), "manual")
                self.assertTrue(doc.metadata.get("manual_evidence"))
                self.assertIn("## 3. Действия владельца", doc.body)
                owner_steps = doc.body.split("## 3. Действия владельца", 1)[1].split("## 4.", 1)[0]
                for forbidden in [" git ", "powershell", "pwsh", "operations/scripts", ".ps1"]:
                    self.assertNotIn(forbidden, owner_steps.lower())


class RebaseRelativeLinksTests(unittest.TestCase):
    def test_leaves_external_and_anchor_only_links_unchanged(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_dir = root / "work" / "tasks"
            source_dir.mkdir(parents=True)
            text = (
                "[внешняя](https://example.com/x) [почта](mailto:a@b.c) [якорь](#раздел) [пусто]()"
            )
            self.assertEqual(_rebase_relative_links(text, source_dir, root), text)

    def test_leaves_link_escaping_repository_root_unchanged(self) -> None:
        with TemporaryDirectory() as outer:
            outer_path = Path(outer)
            root = outer_path / "repo"
            source_dir = root / "work" / "tasks"
            source_dir.mkdir(parents=True)
            text = "[вне репозитория](../../../outside.md)"
            self.assertEqual(_rebase_relative_links(text, source_dir, root), text)

    def test_queue_position_counts_the_entire_milestone_backlog(self) -> None:
        root = Path(__file__).resolve().parents[2]
        milestones = [
            {"id": "m01", "title": "Основа", "work_state": "completed", "scope": []},
            {"id": "m02", "title": "Живой помощник", "work_state": "in-progress", "scope": []},
        ]
        tasks = [
            _task_item(
                f"TASK_{number:03d}",
                "completed" if number < 13 else "planned",
                traces_to=["m02"],
                owner_action="none",
            )
            for number in range(1, 18)
        ]
        with (
            patch(
                "operations.scripts.status.human_status.collect_milestones",
                return_value={"items": milestones, "current": milestones[1]},
            ),
            patch(
                "operations.scripts.status.human_status.collect_tasks",
                return_value={"tasks": tasks},
            ),
            patch(
                "operations.scripts.status.human_status._technical_coverage",
                return_value="| — | — | — | — |",
            ),
        ):
            rendered = render_repository_project_status(root)

        self.assertIn("| Место в очереди проекта | **13 из 17** |", rendered)


class OwnerFollowupParsingTests(unittest.TestCase):
    def test_absent_field_parses_to_empty_list(self) -> None:
        self.assertEqual(_owner_followups(None, "task.md"), [])

    def test_open_and_done_entries_parse_status_and_action(self) -> None:
        parsed = _owner_followups(
            ["[open] Собрать образ", "[done]  Уже сделано  "],
            "task.md",
        )
        self.assertEqual(
            parsed,
            [
                {"status": "open", "action": "Собрать образ"},
                {"status": "done", "action": "Уже сделано"},
            ],
        )

    def test_non_list_value_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            _owner_followups("[open] not a list", "task.md")

    def test_entry_missing_the_status_prefix_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            _owner_followups(["Собрать образ без префикса"], "task.md")


if __name__ == "__main__":
    unittest.main()
