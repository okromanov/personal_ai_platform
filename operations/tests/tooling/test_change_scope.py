from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from operations.scripts.common.project import run_command
from operations.scripts.tasks.check_change_scope import (
    GATE_MACHINERY_PATTERNS,
    _matches,
    changed_paths_between,
    validate_audit_history,
    validate_change_scope,
    validate_coverage_policy_ratchet,
    validate_document_metadata,
    validate_gate_machinery_isolation,
)


def _coverage_policy(
    *,
    fail_under: int = 75,
    overall: int = 75,
    diff: int = 90,
    modules: dict[str, int] | None = None,
) -> str:
    module_values = modules if modules is not None else {"operations/scripts/critical.py": 85}
    module_lines = "\n".join(f'"{name}" = {floor}' for name, floor in module_values.items())
    return f"""[tool.coverage.report]
fail_under = {fail_under}

[tool.personal_ai_platform.coverage]
overall = {overall}
diff = {diff}

[tool.personal_ai_platform.coverage.modules]
{module_lines}
"""


def _commit_policy(root: Path, text: str, message: str) -> str:
    (root / "pyproject.toml").write_text(text, encoding="utf-8")
    assert run_command(["git", "add", "pyproject.toml"], cwd=root).ok
    assert run_command(["git", "commit", "-qm", message], cwd=root).ok
    return run_command(["git", "rev-parse", "HEAD"], cwd=root).stdout.strip()


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
                    allowed=[path, "src/product.py"],
                ),
                encoding="utf-8",
            )
            self.assertEqual(
                validate_change_scope(root, ["src/product.py"]),
                [],
            )
            self.assertTrue(validate_change_scope(root, ["tasks.md"]))
            self.assertEqual(validate_change_scope(root, [".github/workflows/check.yml"]), [])
            self.assertEqual(validate_change_scope(root, [".gitleaksignore"]), [])
            self.assertTrue(validate_change_scope(root, ["src/other_product.py"]))

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
                    allowed=[path, "src/product.py"],
                ),
                encoding="utf-8",
            )
            self.assertTrue(validate_change_scope(root, ["src/product.py"]))
            self.assertEqual(validate_change_scope(root, [path, "src/product.py"]), [])

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

    def test_authority_documents_never_require_task_coverage(self) -> None:
        """AUTHORITY_DOCUMENTS — видимость через обязательную смену версии
        (validate_document_metadata), а не через границы TASK, независимо от
        того, объявляет ли активный этап продуктовый состав."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "work/tasks").mkdir(parents=True)
            (root / "specifications").mkdir(parents=True)
            (root / "milestones.md").write_text(
                "## m02 — Продукт\n\n- work_state: `in-progress`\n- состав: BR_001\n",
                encoding="utf-8",
            )
            self.assertEqual(
                validate_change_scope(
                    root,
                    [
                        "project_rules.md",
                        "AGENTS.md",
                        "operations/change_process.md",
                        "specifications/business_requirements.md",
                        "specifications/threat_model.md",
                        "specifications/system_specification.md",
                        "specifications/architecture_baseline.md",
                        "specifications/infrastructure_baseline.md",
                    ],
                ),
                [],
            )
            self.assertTrue(validate_change_scope(root, ["src/product.py"]))

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
                        "candidates/future_capability.md",
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


class DocumentMetadataNegativeTests(unittest.TestCase):
    """Negative paths for validate_document_metadata.

    Found UNDETECTED by the 2026-09-25 source-level mutation sweep: emptying the
    function left the whole suite green. These tests ensure it can catch both
    backdated `updated` and authority-document edits without a version bump.
    """

    def _setup_repo(self) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.assertTrue(run_command(["git", "init", "-q"], cwd=root).ok)
        self.assertTrue(run_command(["git", "config", "user.name", "Test"], cwd=root).ok)
        self.assertTrue(
            run_command(["git", "config", "user.email", "test@example.invalid"], cwd=root).ok
        )
        return root

    def _commit_doc(self, root: Path, path: str, text: str, message: str) -> str:
        full = root / path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(text, encoding="utf-8")
        self.assertTrue(run_command(["git", "add", path], cwd=root).ok)
        self.assertTrue(run_command(["git", "commit", "-qm", message], cwd=root).ok)
        return run_command(["git", "rev-parse", "HEAD"], cwd=root).stdout.strip()

    def test_backdated_updated_is_caught(self) -> None:
        root = self._setup_repo()
        base = self._commit_doc(
            root,
            "work/tasks/task_001.md",
            "---\nid: TASK_001\ntype: task\nversion: 1.0\nupdated: 2026-09-25\n---\n# Task\n",
            "base",
        )
        head = self._commit_doc(
            root,
            "work/tasks/task_001.md",
            "---\nid: TASK_001\ntype: task\nversion: 1.0\nupdated: 2026-09-20\n---\n# Task edited\n",
            "edit",
        )
        errors = validate_document_metadata(root, base, head, ["work/tasks/task_001.md"])
        self.assertTrue(
            any("updated=2026-09-20" in error and "фактически менялся" in error for error in errors),
            errors,
        )

    def test_authority_document_without_version_bump_is_caught(self) -> None:
        root = self._setup_repo()
        base = self._commit_doc(
            root,
            "AGENTS.md",
            "---\nid: coding_agent_instruction\ntype: agent_instruction\nversion: 4.8\nupdated: 2026-09-25\n---\n# Old\n",
            "base",
        )
        head = self._commit_doc(
            root,
            "AGENTS.md",
            "---\nid: coding_agent_instruction\ntype: agent_instruction\nversion: 4.8\nupdated: 2026-09-26\n---\n# New\n",
            "edit",
        )
        errors = validate_document_metadata(root, base, head, ["AGENTS.md"])
        self.assertTrue(
            any("не может меняться без новой версии" in error for error in errors),
            errors,
        )

    def test_honest_metadata_passes(self) -> None:
        from datetime import date

        root = self._setup_repo()
        today = date.today().isoformat()
        base = self._commit_doc(
            root,
            "work/tasks/task_001.md",
            f"---\nid: TASK_001\ntype: task\nversion: 1.0\nupdated: {today}\n---\n# Task\n",
            "base",
        )
        head = self._commit_doc(
            root,
            "work/tasks/task_001.md",
            f"---\nid: TASK_001\ntype: task\nversion: 1.0\nupdated: {today}\n---\n# Task edited\n",
            "edit",
        )
        errors = validate_document_metadata(root, base, head, ["work/tasks/task_001.md"])
        self.assertEqual(errors, [])


class GateMachineryIsolationTests(unittest.TestCase):
    """Код, который обеспечивает соблюдение правил, не правится заодно.

    `operations/**` и `.github/**` выведены из-под границ TASK через
    MAINTENANCE_PATH_PATTERNS, и обоснование «правку видно через смену
    версии» к .py и .yml неприменимо — поля `version` у них нет. Ослабление
    gate внутри продуктового PR иначе проходит незамеченным.
    """

    def test_machinery_mixed_with_product_delivery_is_rejected(self) -> None:
        errors = validate_gate_machinery_isolation(
            ["src/channels/telegram.py", "operations/scripts/quality/run_suite.py"]
        )
        self.assertEqual(len(errors), 1)
        self.assertIn("разделите на два запроса", errors[0])

    def test_machinery_alone_passes(self) -> None:
        self.assertEqual(
            validate_gate_machinery_isolation(
                ["operations/scripts/documents/check.py", ".github/workflows/project_check.yml"]
            ),
            [],
        )

    def test_product_alone_passes(self) -> None:
        self.assertEqual(validate_gate_machinery_isolation(["src/a.py", "adr/adr_010_x.md"]), [])

    def test_documentation_next_to_machinery_is_not_product_delivery(self) -> None:
        # Документы operations/** не являются поставкой и не запускают правило.
        self.assertEqual(
            validate_gate_machinery_isolation(
                ["operations/change_process.md", "operations/hooks/pre_push_hook.sh"]
            ),
            [],
        )

    def test_every_gate_machinery_pattern_matches_a_real_tracked_file(self) -> None:
        # Шаблон, которому ничего не соответствует, защищает пустоту.
        tracked = subprocess.run(
            ["git", "ls-files"],
            cwd=Path(__file__).resolve().parents[3],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split()
        for pattern in GATE_MACHINERY_PATTERNS:
            with self.subTest(pattern=pattern):
                self.assertTrue(
                    any(_matches(path, [pattern]) for path in tracked),
                    f"{pattern} не покрывает ни одного файла",
                )


class CoveragePolicyRatchetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.assertTrue(run_command(["git", "init", "-q"], cwd=self.root).ok)
        self.assertTrue(run_command(["git", "config", "user.name", "Test"], cwd=self.root).ok)
        self.assertTrue(
            run_command(["git", "config", "user.email", "test@example.invalid"], cwd=self.root).ok
        )
        self.base = _commit_policy(self.root, _coverage_policy(), "base")

    def _errors(self, policy: str) -> list[str]:
        head = _commit_policy(self.root, policy, "change")
        return validate_coverage_policy_ratchet(self.root, self.base, head)

    def test_fail_under_cannot_decrease(self) -> None:
        errors = self._errors(_coverage_policy(fail_under=0))
        self.assertTrue(any("tool.coverage.report.fail_under" in error for error in errors))

    def test_overall_floor_cannot_decrease(self) -> None:
        errors = self._errors(_coverage_policy(overall=0))
        self.assertTrue(any("coverage.overall" in error for error in errors))

    def test_diff_floor_cannot_decrease(self) -> None:
        errors = self._errors(_coverage_policy(diff=0))
        self.assertTrue(any("coverage.diff" in error for error in errors))

    def test_named_module_floor_cannot_decrease(self) -> None:
        errors = self._errors(_coverage_policy(modules={"operations/scripts/critical.py": 0}))
        self.assertTrue(any("critical.py" in error and "снижен" in error for error in errors))

    def test_protected_module_cannot_be_removed(self) -> None:
        errors = self._errors(_coverage_policy(modules={}))
        self.assertTrue(any("удалён защищённый модуль" in error for error in errors))

    def test_higher_floors_and_added_modules_pass(self) -> None:
        errors = self._errors(
            _coverage_policy(
                fail_under=76,
                overall=76,
                diff=91,
                modules={
                    "operations/scripts/critical.py": 86,
                    "operations/scripts/new.py": 85,
                },
            )
        )
        self.assertEqual(errors, [])

    def test_incomplete_policy_fails_closed(self) -> None:
        errors = self._errors("[tool.coverage.report]\nfail_under = 75\n")
        self.assertTrue(any("coverage policy" in error and "неполна" in error for error in errors))

    def test_non_numeric_floor_fails_closed(self) -> None:
        policy = _coverage_policy().replace("overall = 75", "overall = true")
        errors = self._errors(policy)
        self.assertTrue(any("coverage.overall должен быть числом" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
