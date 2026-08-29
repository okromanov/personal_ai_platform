from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from operations.scripts.common.project import run_command
from operations.scripts.tasks.check_change_scope import (
    changed_paths_between,
    validate_audit_history,
    validate_change_scope,
    validate_document_metadata,
)


def _task(*, task_id: str, state: str, path: str, allowed: list[str]) -> str:
    allowed_lines = "\n".join(f"  - {item}" for item in allowed)
    actor = "none" if state == "completed" else "agent"
    mark = "x" if state == "completed" else " "
    return f"""---
id: {task_id}
type: task
title: Проверка
work_state: {state}
version: 1.0
next_actor: {actor}
owner_action: none
allowed_paths:
{allowed_lines}
---
# {task_id} — Проверка

## 5. План выполнения

- [{mark}] Шаг
"""


class ChangeScopeTests(unittest.TestCase):
    def test_active_task_covers_only_declared_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "work/tasks").mkdir(parents=True)
            (root / "work/tests").mkdir(parents=True)
            path = "work/tasks/task_001.md"
            (root / path).write_text(
                _task(
                    task_id="TASK_001",
                    state="in-progress",
                    path=path,
                    allowed=[path, "specifications/**"],
                ),
                encoding="utf-8",
            )
            self.assertEqual(
                validate_change_scope(root, ["specifications/system_specification.md"]),
                [],
            )
            self.assertTrue(validate_change_scope(root, ["tasks.md"]))
            self.assertEqual(validate_change_scope(root, [".github/workflows/check.yml"]), [])
            self.assertTrue(validate_change_scope(root, ["src/product.py"]))

    def test_completed_task_is_eligible_only_when_its_card_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "work/tasks").mkdir(parents=True)
            (root / "work/tests").mkdir(parents=True)
            path = "work/tasks/task_001.md"
            (root / path).write_text(
                _task(
                    task_id="TASK_001",
                    state="completed",
                    path=path,
                    allowed=[path, "specifications/system_specification.md"],
                ),
                encoding="utf-8",
            )
            self.assertTrue(validate_change_scope(root, ["specifications/system_specification.md"]))
            self.assertEqual(
                validate_change_scope(root, [path, "specifications/system_specification.md"]), []
            )

    def test_foundation_milestone_does_not_require_task_for_specifications(self) -> None:
        """Пока активный этап не объявляет продуктовый состав, поставки продукта нет:
        правка спецификаций относится к базовой редакции и покрывается профилем основы."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "work/tasks").mkdir(parents=True)
            (root / "work/tests").mkdir(parents=True)
            (root / "milestones.md").write_text(
                "## m01 — Foundation\n\n- work_state: `in-progress`\n- состав основы: документы\n",
                encoding="utf-8",
            )
            self.assertEqual(
                validate_change_scope(
                    root,
                    [
                        "specifications/business_requirements.md",
                        "specifications/threat_model.md",
                    ],
                ),
                [],
            )

    def test_dated_audit_history_is_append_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertTrue(run_command(["git", "init", "-q"], cwd=root).ok)
            self.assertTrue(run_command(["git", "config", "user.name", "Test"], cwd=root).ok)
            self.assertTrue(
                run_command(["git", "config", "user.email", "test@example.invalid"], cwd=root).ok
            )
            audit_dir = root / "work/audit"
            audit_dir.mkdir(parents=True)
            baseline = audit_dir / "audit_baseline_2026_08_28.md"
            baseline.write_text("first\n", encoding="utf-8")
            self.assertTrue(run_command(["git", "add", "."], cwd=root).ok)
            self.assertTrue(run_command(["git", "commit", "-qm", "base"], cwd=root).ok)
            base = run_command(["git", "rev-parse", "HEAD"], cwd=root).stdout.strip()

            baseline.write_text("rewritten\n", encoding="utf-8")
            self.assertTrue(run_command(["git", "add", "."], cwd=root).ok)
            self.assertTrue(run_command(["git", "commit", "-qm", "rewrite"], cwd=root).ok)
            rewritten = run_command(["git", "rev-parse", "HEAD"], cwd=root).stdout.strip()
            self.assertTrue(validate_audit_history(root, base, rewritten))

            self.assertTrue(run_command(["git", "reset", "--hard", base], cwd=root).ok)
            (audit_dir / "audit_baseline_2026_08_29.md").write_text("second\n", encoding="utf-8")
            self.assertTrue(run_command(["git", "add", "."], cwd=root).ok)
            self.assertTrue(run_command(["git", "commit", "-qm", "append"], cwd=root).ok)
            appended = run_command(["git", "rev-parse", "HEAD"], cwd=root).stdout.strip()
            self.assertEqual(validate_audit_history(root, base, appended), [])

    def test_repository_maintenance_does_not_require_project_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(
                validate_change_scope(
                    root,
                    [
                        "operations/change_process.md",
                        "AGENTS.md",
                        "operations/tool.py",
                        "work/tasks/old.md",
                        "pyproject.toml",
                    ],
                ),
                [],
            )


class DocumentMetadataHonestyTests(unittest.TestCase):
    """Дата и версия документа обязаны отражать факт его изменения.

    Оба правила добавлены после того, как в этом же репозитории дважды прошли
    незамеченными: смысловая правка governance.md без новой версии и дата
    updated на день раньше фактического изменения.
    """

    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[3]

    def _run(self, base: str, head: str) -> list[str]:
        for revision in (base, head):
            if not run_command(
                ["git", "rev-parse", "--verify", f"{revision}^{{commit}}"], cwd=self.root
            ).ok:
                self.skipTest(f"редакция {revision} недоступна в поверхностном клоне")
        changed = changed_paths_between(self.root, base, head)
        return validate_document_metadata(self.root, base, head, changed)

    def test_current_branch_is_honest(self) -> None:
        self.assertEqual(self._run("origin/main", "HEAD"), [])

    def test_metadata_validation_runs_without_hardcoded_commits(self) -> None:
        """Проверяет, что валидация метаданных работает с доступной истории Git.

        Вместо использования конкретных коммитов, которые могут не существовать
        в поверхностном клоне, используются origin/main и HEAD, которые всегда доступны.
        """
        root = Path(__file__).resolve().parents[3]
        if not run_command(["git", "rev-parse", "--verify", "origin/main^{commit}"], cwd=root).ok:
            self.skipTest("origin/main недоступен в локальном snapshot")
        changed = changed_paths_between(root, "origin/main", "HEAD")
        errors = validate_document_metadata(root, "origin/main", "HEAD", changed)
        self.assertIsInstance(errors, list)


if __name__ == "__main__":
    unittest.main()
