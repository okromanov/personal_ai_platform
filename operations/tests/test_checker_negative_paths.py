from __future__ import annotations

import tempfile
import unittest
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from unittest.mock import patch

from operations.scripts.documents.check import (
    _known_reference_ids,
    _task_test_plan_item_errors,
    check_acceptance_adr_transitions,
    check_acceptance_model,
    check_architecture_diagrams,
    check_audit_register_cards,
    check_authority_graph,
    check_automation_policy,
    check_business_requirements_coverage,
    check_document_policy,
    check_markdown_section_order,
    check_metadata,
    check_tasks,
    check_terminal_outcome_delivery_role,
    check_test_specs,
    check_traceability,
)
from operations.scripts.documents.metadata import MarkdownDocument


class CheckerNegativePathTests(unittest.TestCase):
    def test_metadata_rejects_status_and_duplicate_identifiers(self) -> None:
        metadata: dict[str, Any] = {
            "id": "DOC_001",
            "type": "guide",
            "version": "1.0",
            "updated": "2026-08-20",
            "document_state": "current",
            "status": "current",
        }
        documents = [
            ("one.md", MarkdownDocument(Path("one.md"), metadata, "", "One")),
            ("two.md", MarkdownDocument(Path("two.md"), metadata, "", "Two")),
        ]
        with (
            patch("operations.scripts.documents.check._primary_documents", return_value=documents),
            patch("operations.scripts.documents.check._known_reference_ids", return_value=set()),
        ):
            result = check_metadata(Path("."))
        self.assertIn("универсальное поле 'status'", "\n".join(result.errors))
        self.assertIn("Дублирующий document id", "\n".join(result.errors))

    def test_traceability_rejects_gaps_unknown_edges_and_incomplete_records(self) -> None:
        records: dict[str, dict[str, Any]] = {
            "BR_001": {"family": "BR", "relations": {}},
            "BR_003": {"family": "BR", "relations": {"traces_to": ["UNKNOWN"]}},
            "SEC_CTL_001": {"family": "SEC_CTL", "relations": {}},
            "TEST_001": {
                "family": "TEST",
                "relations": {"accepts": [], "verifies": []},
            },
        }
        with patch(
            "operations.scripts.documents.check.collect_traceable_elements",
            return_value=records,
        ):
            result = check_traceability(Path("."))
        joined = "\n".join(result.errors)
        self.assertIn("без пропусков", joined)
        self.assertIn("неизвестный трассируемый id", joined)
        self.assertIn("на SEC_CTL должна ссылаться", joined)
        self.assertIn("TEST должен verifies", joined)

    def test_authority_graph_rejects_lower_layer_dependency_and_m01_scope(self) -> None:
        specification = MarkdownDocument(
            Path("system.md"),
            {
                "id": "system",
                "type": "system_specification",
                "depends_on": ["architecture_baseline"],
            },
            "",
            "System",
        )
        architecture = MarkdownDocument(
            Path("architecture.md"),
            {"id": "architecture_baseline", "type": "architecture_specification"},
            "",
            "Architecture",
        )
        documents = [("system.md", specification), ("architecture.md", architecture)]
        with (
            patch("operations.scripts.documents.check._primary_documents", return_value=documents),
            patch(
                "operations.scripts.documents.check.collect_milestones",
                return_value={"items": [{"id": "m01", "scope": ["BR_001"]}]},
            ),
            patch("operations.scripts.documents.check.read_text", return_value=""),
        ):
            result = check_authority_graph(Path("."))
        joined = "\n".join(result.errors)
        self.assertIn("не может depends_on нижний слой", joined)
        self.assertIn("foundation milestone", joined)

    def test_task_policy_reports_conflicting_lifecycle_fields(self) -> None:
        task: dict[str, Any] = {
            "id": "TASK_001",
            "path": "work/tasks/task_001.md",
            "body": "### Владельцу\n50%",
            "next_actor": "agent",
            "owner_action": "approve",
            "work_state": "completed",
            "checklist": [],
            "steps_remaining": 1,
            "allowed_paths": [],
            "blocker": "stale",
            "owner_followups": [
                {"status": "bogus", "action": "Do X"},
                {"status": "open", "action": ""},
                {"status": "open", "action": "Собрать образ"},
            ],
        }
        planned = dict(task, id="TASK_002", next_actor="none", owner_action="none")
        planned["work_state"] = "planned"
        planned["owner_followups"] = []
        planned["body"] = "### Владельцу\n50%\n\n## Незакрытые действия владельца\n\nстарый текст"
        with (
            patch(
                "operations.scripts.documents.check.collect_tasks",
                return_value={"tasks": [task, planned]},
            ),
            patch("operations.scripts.documents.check.read_text", return_value="index"),
            patch.object(Path, "exists", return_value=True),
        ):
            result = check_tasks(Path("."))
        joined = "\n".join(result.errors)
        for fragment in (
            "owner_action задано",
            "дословно присутствовать",
            "должна иметь next_actor=none",
            "одного следующего исполнителя",
            "пустой раздел владельца",
            "искусственные проценты",
            "status должен быть 'open' или 'done'",
            "action не может быть пустым",
            "открытое действие должно дословно",
            "есть открытые owner_followups, но нет раздела",
            "но нет ни одного открытого owner_followups",
        ):
            self.assertIn(fragment, joined)

    def test_markdown_section_order_rejects_gap_and_ignores_examples(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bad = root / "bad.md"
            good = root / "good.md"
            bad.write_text(
                "# Bad\n\n## 1. One\n\n## 3. Three\n",
                encoding="utf-8",
            )
            good.write_text(
                "# Good\n\n## 1. One\n\n"
                "## 2. Two\n\n## 2.5 Decimal subsection\n\n"
                "```markdown\n## 9. Example only\n```\n",
                encoding="utf-8",
            )
            result = check_markdown_section_order(root)
        joined = "\n".join(result.errors)
        self.assertIn("bad.md", joined)
        self.assertIn("после 1", joined)
        self.assertNotIn("good.md", joined)

    def test_task_section_contract_rejects_extra_and_reordered_h2(self) -> None:
        core = [
            (1, "Зачем это делаем"),
            (2, "Результат"),
            (3, "Где мы сейчас"),
            (4, "Что делать сейчас"),
            (5, "План выполнения"),
            (6, "Состав"),
            (7, "Проверки и доказательства"),
            (8, "Готово когда"),
            (9, "Что будет дальше"),
            (10, "Что это даёт владельцу"),
        ]

        def body(
            task_id: str,
            sections: Sequence[tuple[int | None, str]],
            *,
            followup_action: str = "",
        ) -> str:
            rendered = [f"# {task_id} — Test"]
            for number, title in sections:
                heading = f"{number}. {title}" if number is not None else title
                rendered.extend([f"## {heading}", followup_action or "Content"])
            return "\n\n".join(rendered) + "\n"

        def task(task_id: str, task_body: str, *, open_followup: bool = False) -> dict[str, Any]:
            return {
                "id": task_id,
                "path": f"work/tasks/{task_id.lower()}.md",
                "body": task_body,
                "next_actor": "agent",
                "owner_action": "none",
                "work_state": "planned",
                "checklist": [],
                "steps_remaining": 1,
                "allowed_paths": [],
                "blocker": "",
                "owner_followups": (
                    [{"status": "open", "action": "Собрать evidence"}] if open_followup else []
                ),
            }

        reordered = core[:-1] + [(11, "Подтверждение владельца"), core[-1]]
        unknown = core + [(11, "Произвольное расширение")]
        allowed = core + [(None, "Незакрытые действия владельца")]
        tasks = [
            task("TASK_001", body("TASK_001", reordered)),
            task("TASK_002", body("TASK_002", unknown)),
            task(
                "TASK_003",
                body("TASK_003", allowed, followup_action="Собрать evidence"),
                open_followup=True,
            ),
        ]
        with patch(
            "operations.scripts.documents.check.collect_tasks",
            return_value={"tasks": tasks},
        ):
            result = check_tasks(Path("."))
        joined = "\n".join(result.errors)
        self.assertIn("TASK_001: верхнеуровневые разделы", joined)
        self.assertIn("TASK_002: верхнеуровневые разделы", joined)
        self.assertNotIn("TASK_003: верхнеуровневые разделы", joined)

    def test_completed_task_rejects_unfilled_auto_generated_result_placeholder(self) -> None:
        def _task(body: str) -> dict[str, Any]:
            return {
                "id": "TASK_001",
                "path": "work/tasks/task_001.md",
                "body": body,
                "next_actor": "none",
                "owner_action": "none",
                "work_state": "completed",
                "component": "ARC_CMP_001",
                "checklist": [],
                "steps_remaining": 0,
                "allowed_paths": [],
                "blocker": "",
            }

        placeholder_body = (
            "## 2. Результат\n\n"
            "Компонент `ARC_CMP_001` полностью реализован, протестирован и интегрирован.\n\n"
            "## 3. Где мы сейчас\n"
        )
        filled_body = (
            "## 2. Результат\n\n"
            "Стабильный контракт Channel и симулированная реализация TelegramChannel "
            "(очередь вместо реального Bot API).\n\n"
            "## 3. Где мы сейчас\n"
        )

        with (
            patch(
                "operations.scripts.documents.check.collect_tasks",
                return_value={"tasks": [_task(placeholder_body)]},
            ),
            patch("operations.scripts.documents.check.read_text", return_value="index"),
            patch.object(Path, "exists", return_value=True),
        ):
            placeholder_result = check_tasks(Path("."))
        self.assertIn("шаблонной заглушкой", "\n".join(placeholder_result.errors))

        with (
            patch(
                "operations.scripts.documents.check.collect_tasks",
                return_value={"tasks": [_task(filled_body)]},
            ),
            patch("operations.scripts.documents.check.read_text", return_value="index"),
            patch.object(Path, "exists", return_value=True),
        ):
            filled_result = check_tasks(Path("."))
        self.assertNotIn("шаблонной заглушкой", "\n".join(filled_result.errors))

    def test_completed_task_requires_real_owner_capability_section(self) -> None:
        def _task(body: str) -> dict[str, Any]:
            return {
                "id": "TASK_001",
                "path": "work/tasks/task_001.md",
                "body": body,
                "next_actor": "none",
                "owner_action": "none",
                "work_state": "completed",
                "component": "ARC_CMP_001",
                "checklist": [],
                "steps_remaining": 0,
                "allowed_paths": [],
                "blocker": "",
            }

        base_body = "## 2. Результат\n\nСтабильный контракт Channel.\n\n## 3. Где мы сейчас\n"

        def _run(body: str) -> str:
            with (
                patch(
                    "operations.scripts.documents.check.collect_tasks",
                    return_value={"tasks": [_task(body)]},
                ),
                patch("operations.scripts.documents.check.read_text", return_value="index"),
                patch.object(Path, "exists", return_value=True),
            ):
                return "\n".join(check_tasks(Path(".")).errors)

        missing_result = _run(base_body)
        self.assertIn("должна содержать раздел", missing_result)

        placeholder_result = _run(
            base_body + "## 10. Что это даёт владельцу\n\n"
            "Функционал появится после завершения этой TASK.\n"
        )
        self.assertIn("не может оставаться шаблонной заглушкой", placeholder_result)

        filled_result = _run(
            base_body + "## 10. Что это даёт владельцу\n\n"
            "Можно написать боту и получить отслеживаемую задачу.\n"
        )
        self.assertNotIn("Что это даёт владельцу", filled_result)

    def test_test_spec_policy_rejects_unsafe_and_unlinked_tests(self) -> None:
        automated: dict[str, Any] = {
            "id": "TEST_001",
            "spec_state": "current",
            "traces_to": [],
            "verifies": ["UNKNOWN"],
            "accepts": ["m99"],
            "execution": "automated",
            "automated_evidence": "unknown",
            "manual_evidence": "manual",
        }
        manual = dict(automated, id="TEST_002", execution="manual")
        manual["automated_evidence"] = "automated"
        manual["manual_evidence"] = "unknown"
        documents = {
            "test_001.md": MarkdownDocument(
                Path("test_001.md"), automated, "## Действия владельца\nRun git status", "A"
            ),
            "test_002.md": MarkdownDocument(Path("test_002.md"), manual, "", "B"),
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tests_dir = root / "work/tests"
            tests_dir.mkdir(parents=True)
            for name in documents:
                (tests_dir / name).touch()
            with (
                patch(
                    "operations.scripts.documents.check.collect_traceable_elements",
                    return_value={},
                ),
                patch(
                    "operations.scripts.documents.check.collect_milestones",
                    return_value={"items": [{"id": "m02"}]},
                ),
                patch(
                    "operations.scripts.documents.check.load_quality_registry",
                    return_value={"evidence_catalog": {}},
                ),
                patch(
                    "operations.scripts.documents.check.load_document",
                    side_effect=lambda path: documents[path.name],
                ),
            ):
                result = check_test_specs(root)
        joined = "\n".join(result.errors)
        for fragment in (
            "Автоматический запуск",
            "не должен содержать инструкции владельцу",
            "Действия владельца",
            "неизвестный трассируемый id",
            "неизвестный milestone",
        ):
            self.assertIn(fragment, joined)

    def test_document_and_requirement_policies_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stable = root / "specifications/system_specification.md"
            stable.parent.mkdir(parents=True)
            stable.write_text("# нижний заголовок\nm07 roadmap\n", encoding="utf-8")

            def fake_read(path: Path) -> str:
                relative = path.relative_to(root).as_posix()
                values = {
                    "specifications/architecture_baseline.md": "## Граница с инфраструктурой",
                    "specifications/infrastructure_baseline.md": "",
                    "specifications/threat_model.md": "",
                    "operations/change_process.md": "",
                    "specifications/system_specification.md": (
                        "### SEC_CTL_002 — Control\n### SYS_001 — Requirement"
                    ),
                }
                return values.get(relative, "")

            with (
                patch("operations.scripts.documents.check.iter_files", return_value=[stable]),
                patch("operations.scripts.documents.check.read_text", side_effect=fake_read),
                patch(
                    "operations.scripts.documents.check.collect_traceable_elements",
                    return_value={},
                ),
            ):
                document_result = check_document_policy(root)
            joined = "\n".join(document_result.errors)
            self.assertIn("roadmap/implementation token", joined)
            self.assertIn("русский заголовок", joined)
            self.assertIn("процессный раздел", joined)
            self.assertIn("канонический раздел", joined)
            self.assertIn("расположены по порядку", joined)

            with patch(
                "operations.scripts.documents.check.read_text",
                side_effect=lambda path: "" if path.name == "business_requirements.md" else "",
            ):
                requirement_result = check_business_requirements_coverage(root)
            self.assertIn("не найдено ни одного BR", "\n".join(requirement_result.errors))

            with (
                patch(
                    "operations.scripts.documents.check.read_text",
                    side_effect=lambda path: (
                        "### BR_001 — Core\n- priority: `core`"
                        if path.name == "business_requirements.md"
                        else "Обязательный состав продукта: BR_001"
                    ),
                ),
                patch("operations.scripts.documents.check.v1_milestone_ids", return_value=[]),
            ):
                missing_candidates = check_business_requirements_coverage(root)
            self.assertIn("Кандидатные направления", "\n".join(missing_candidates.errors))

    def test_acceptance_policy_covers_planned_warning_and_missing_links(self) -> None:
        planned = {"current": {"id": "m02", "work_state": "planned"}}
        with (
            patch("operations.scripts.documents.check.collect_milestones", return_value=planned),
            patch("operations.scripts.documents.check.collect_tasks", return_value={"tasks": []}),
            patch(
                "operations.scripts.documents.check.collect_test_specs", return_value={"items": []}
            ),
            patch("operations.scripts.documents.check.load_quality_registry", return_value={}),
            patch("operations.scripts.documents.check.profiles_for_milestone", return_value=[]),
        ):
            warning = check_acceptance_model(Path("."))
        self.assertIn("станет обязательным", "\n".join(warning.warnings))

        active = {"current": {"id": "m02", "work_state": "in-progress", "scope": ["SYS_001"]}}
        tasks = {
            "tasks": [
                {
                    "id": "TASK_001",
                    "traces_to": ["m02"],
                    "implements": ["SYS_001"],
                }
            ]
        }
        with (
            patch("operations.scripts.documents.check.collect_milestones", return_value=active),
            patch("operations.scripts.documents.check.collect_tasks", return_value=tasks),
            patch(
                "operations.scripts.documents.check.collect_test_specs", return_value={"items": []}
            ),
            patch("operations.scripts.documents.check.load_quality_registry", return_value={}),
            patch(
                "operations.scripts.documents.check.profiles_for_milestone",
                return_value=[("m02", {"scope_coverage": "task_test"})],
            ),
            patch(
                "operations.scripts.documents.check.validate_task_semantics",
                return_value=[
                    "m02: scope не покрыт TASK→component→TEST: SYS_001",
                    "TASK_001: component не связан ни с одним TEST",
                ],
            ),
        ):
            missing = check_acceptance_model(Path("."))
        self.assertIn("scope не покрыт", "\n".join(missing.errors))
        self.assertIn("не связан ни с одним TEST", "\n".join(missing.errors))

    def test_acceptance_adr_transitions_rejects_unmatched_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "adr").mkdir()
            (root / "adr" / "adr_001_x.md").write_text(
                "---\nid: ADR_001\ntype: adr\ndecision_state: proposed\n"
                "version: 1.0\nupdated: 2026-08-22\ntraces_to:\n  - m01\n---\n\n# ADR_001\n",
                encoding="utf-8",
            )
            (root / "work" / "acceptance").mkdir(parents=True)
            (root / "work" / "acceptance" / "m01.json").write_text(
                '{"adr_transitions": [{"adr_id": "ADR_001", '
                '"state_change": "proposed → accepted"}]}',
                encoding="utf-8",
            )

            mismatch = check_acceptance_adr_transitions(root)
            self.assertIn(
                "заявляет переход ADR_001 → accepted, но decision_state в adr/ остаётся 'proposed'",
                "\n".join(mismatch.errors),
            )

            (root / "adr" / "adr_001_x.md").write_text(
                "---\nid: ADR_001\ntype: adr\ndecision_state: accepted\n"
                "version: 1.0\nupdated: 2026-08-29\ntraces_to:\n  - m01\n---\n\n# ADR_001\n",
                encoding="utf-8",
            )
            matching = check_acceptance_adr_transitions(root)
            self.assertEqual(matching.errors, [])

    def test_acceptance_adr_transitions_rejects_unknown_adr_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "adr").mkdir()
            (root / "work" / "acceptance").mkdir(parents=True)
            (root / "work" / "acceptance" / "m01.json").write_text(
                '{"adr_transitions": [{"adr_id": "ADR_999", '
                '"state_change": "proposed → accepted"}]}',
                encoding="utf-8",
            )
            result = check_acceptance_adr_transitions(root)
            self.assertIn(
                "work/acceptance/m01.json: заявляет переход ADR_999, но такого ADR нет в adr/",
                result.errors,
            )

    def test_terminal_outcome_delivery_role_rejects_mismatched_queue_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "milestones.md").write_text(
                "## m02 — Пример\n\n"
                "### Очередь, закрывающая пользовательский результат\n\n"
                "Затем обязательны: [`TASK_001`](work/tasks/task_001_x.md) — пример.\n",
                encoding="utf-8",
            )
            (root / "work" / "tasks").mkdir(parents=True)
            (root / "work" / "tasks" / "task_001_x.md").write_text(
                "---\nid: TASK_001\ntype: task\ntitle: X\ncomponent: ARC_CMP_001\n"
                "work_state: planned\nversion: 1.0\nupdated: 2026-08-29\ndepends_on: []\n"
                "next_actor: agent\nowner_action: none\nallowed_paths:\n  - a\n"
                "traces_to:\n  - m02\nimplements:\n  - ARC_CMP_001\n---\n\n# TASK_001\n",
                encoding="utf-8",
            )
            mismatch = check_terminal_outcome_delivery_role(root)
            self.assertIn(
                "TASK_001: указана в очереди, закрывающей пользовательский результат, "
                "но delivery_role не terminal_outcome",
                mismatch.errors,
            )

            (root / "work" / "tasks" / "task_001_x.md").write_text(
                "---\nid: TASK_001\ntype: task\ntitle: X\ncomponent: ARC_CMP_001\n"
                "delivery_role: terminal_outcome\nwork_state: planned\nversion: 1.0\n"
                "updated: 2026-08-29\ndepends_on: []\nnext_actor: agent\nowner_action: none\n"
                "allowed_paths:\n  - a\ntraces_to:\n  - m02\nimplements:\n  - ARC_CMP_001\n"
                "---\n\n# TASK_001\n",
                encoding="utf-8",
            )
            matching = check_terminal_outcome_delivery_role(root)
            self.assertEqual(matching.errors, [])

    def test_terminal_outcome_delivery_role_ignores_prerequisite_mentions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "milestones.md").write_text(
                "## m02 — Пример\n\n"
                "### Очередь, закрывающая пользовательский результат\n\n"
                "[`TASK_001`](work/tasks/task_001_x.md) завершает подготовку. "
                "Затем обязателен: [`TASK_002`](work/tasks/task_002_x.md) — пример.\n",
                encoding="utf-8",
            )
            (root / "work" / "tasks").mkdir(parents=True)
            for task_id, num, depends_on in (
                ("TASK_001", "001", "[]"),
                ("TASK_002", "002", "\n  - TASK_001"),
            ):
                (root / "work" / "tasks" / f"task_{num}_x.md").write_text(
                    f"---\nid: {task_id}\ntype: task\ntitle: X\ncomponent: ARC_CMP_001\n"
                    f"work_state: planned\nversion: 1.0\nupdated: 2026-08-29\n"
                    f"depends_on: {depends_on}\n"
                    "next_actor: agent\nowner_action: none\nallowed_paths:\n  - a\n"
                    "traces_to:\n  - m02\nimplements:\n  - ARC_CMP_001\n"
                    f"---\n\n# {task_id}\n",
                    encoding="utf-8",
                )
            result = check_terminal_outcome_delivery_role(root)
            self.assertIn(
                "TASK_002: указана в очереди, закрывающей пользовательский результат, "
                "но delivery_role не terminal_outcome",
                result.errors,
            )
            self.assertFalse(any("TASK_001" in error for error in result.errors))

    def test_known_reference_ids_still_swallows_expected_input_errors(self) -> None:
        with (
            patch(
                "operations.scripts.documents.check.collect_traceable_elements",
                side_effect=ValueError("malformed document"),
            ),
            patch(
                "operations.scripts.documents.check.collect_milestones",
                side_effect=ValueError("malformed document"),
            ),
        ):
            self.assertEqual(_known_reference_ids(Path("."), {}), set())

    def test_known_reference_ids_no_longer_swallows_a_real_bug(self) -> None:
        with patch(
            "operations.scripts.documents.check.collect_traceable_elements",
            side_effect=TypeError("real bug in the collector"),
        ):
            with self.assertRaises(TypeError):
                _known_reference_ids(Path("."), {})

    def test_check_test_specs_no_longer_swallows_a_real_bug(self) -> None:
        with patch(
            "operations.scripts.documents.check.collect_traceable_elements",
            side_effect=AttributeError("real bug in the collector"),
        ):
            with self.assertRaises(AttributeError):
                check_test_specs(Path("."))

    def test_automation_policy_rejects_bypasses_and_mutating_workflows(self) -> None:
        workflow = """\
on:
  pull_request:
    paths:
      - docs/**
  push:
    branches:
      - main
permissions:
  issues: write
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - name: Mutable action
        uses: actions/checkout@main
      - name: Mutation
        run: git push
"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflows = root / ".github/workflows"
            workflows.mkdir(parents=True)
            (workflows / "project_check.yml").write_text(workflow, encoding="utf-8")
            acceptance = root / "operations/scripts/acceptance/apply.py"
            acceptance.parent.mkdir(parents=True)
            acceptance.write_text("--semantic-review validate_semantic_review", encoding="utf-8")
            result = check_automation_policy(root)
        joined = "\n".join(result.errors)
        for fragment in (
            "contents: read",
            "каждом PR",
            "merged pull request",
            "repository mutation primitive git push",
            "immutable 40-char commit SHA",
        ):
            self.assertIn(fragment, joined)


class TaskTestPlanItemWordingTests(unittest.TestCase):
    def test_pre_creation_wording_passes(self) -> None:
        checklist = [{"text": "Написать TEST, связанный с TASK и требованиями компонента"}]
        self.assertEqual(_task_test_plan_item_errors("TASK_099", checklist), [])

    def test_linked_wording_passes(self) -> None:
        checklist = [
            {
                "text": (
                    "Написать [`TEST_015`](../tests/test_015.md), связанный с TASK "
                    "и требованиями компонента"
                )
            }
        ]
        self.assertEqual(_task_test_plan_item_errors("TASK_099", checklist), [])

    def test_free_form_variants_are_rejected(self) -> None:
        for bad_text in (
            "Создать TEST и evidence",
            "Создать TEST/evidence и проверить точный SHA",
            "Создать [`TEST_015`](../tests/test_015.md), связанный с TASK и требованиями компонента",
            "Написать TEST с реальным evidence",
        ):
            with self.subTest(bad_text=bad_text):
                errors = _task_test_plan_item_errors("TASK_099", [{"text": bad_text}])
                self.assertTrue(errors, f"expected an error for {bad_text!r}")
                self.assertIn(bad_text, errors[0])

    def test_unrelated_plan_items_mentioning_test_are_ignored(self) -> None:
        checklist = [{"text": "Дополнить allowed_paths реальными путями реализации и TEST"}]
        self.assertEqual(_task_test_plan_item_errors("TASK_099", checklist), [])


class AuditRegisterCardFormatTests(unittest.TestCase):
    REGISTER = (
        "---\nid: audit_register\ntype: audit_register\ndocument_state: current\n"
        "version: 1.0\nupdated: 2026-08-30\ndepends_on: []\n---\n\n"
        "# Реестр\n\n## 3. Реестр\n\n"
        "| ID | Severity | State | First seen | Review date | Owner | Evidence | Resolution |\n"
        "|---|---|---|---|---|---|---|---|\n"
        "| [AUD-001](audit_adhoc_cards.md#aud-001) | low | open | 2026-08-30 | "
        "2026-09-30 | owner | proof | fix |\n"
    )
    ARCHIVE_HEADER = (
        "---\nid: audit_archive\ntype: audit_archive\ndocument_state: current\n"
        "version: 1.0\nupdated: 2026-08-30\ndepends_on: []\n---\n\n"
        "# Архив\n\n"
    )

    def _write(self, root: Path, card_body: str) -> None:
        audit_dir = root / "work/audit"
        audit_dir.mkdir(parents=True)
        (audit_dir / "audit_register.md").write_text(self.REGISTER, encoding="utf-8")
        (audit_dir / "audit_adhoc_cards.md").write_text(
            self.ARCHIVE_HEADER + card_body, encoding="utf-8"
        )

    def test_unknown_field_name_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root,
                '<a id="aud-001"></a>\n### AUD-001 — title\n\n'
                "- **Severity/Confidence/Evidence state:** low / high / CONFIRMED\n"
                "- **Baseline:** pre-existing\n"
                "- **Файл:** x.py\n"
                "- **Наблюдаемое поведение:** что-то.\n"
                "- **Статус:** придуманное на месте поле.\n",
            )
            result = check_audit_register_cards(root)
        self.assertFalse(result.ok)
        self.assertTrue(any("неизвестное название поля «Статус»" in e for e in result.errors))

    def test_reordered_required_fields_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root,
                '<a id="aud-001"></a>\n### AUD-001 — title\n\n'
                "- **Baseline:** pre-existing\n"
                "- **Severity/Confidence/Evidence state:** low / high / CONFIRMED\n"
                "- **Файл:** x.py\n"
                "- **Наблюдаемое поведение:** что-то.\n",
            )
            result = check_audit_register_cards(root)
        self.assertFalse(result.ok)
        self.assertTrue(any("первые три поля карточки должны быть" in e for e in result.errors))

    def test_missing_observed_behavior_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root,
                '<a id="aud-001"></a>\n### AUD-001 — title\n\n'
                "- **Severity/Confidence/Evidence state:** low / high / CONFIRMED\n"
                "- **Baseline:** pre-existing\n"
                "- **Файл:** x.py\n",
            )
            result = check_audit_register_cards(root)
        self.assertFalse(result.ok)
        self.assertTrue(any("Наблюдаемое поведение" in e for e in result.errors))

    def test_dated_resolution_labels_and_optional_fields_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root,
                '<a id="aud-001"></a>\n### AUD-001 — title\n\n'
                "- **Severity/Confidence/Evidence state:** low / high / CONFIRMED\n"
                "- **Baseline:** pre-existing\n"
                "- **Файл:** x.py\n"
                "- **Наблюдаемое поведение:** что-то.\n"
                "- **Рекомендованное исправление:** сделать X.\n"
                "- **Как проверить исправление:** запустить Y.\n"
                "- **Исправлено (2026-08-30):** сделано.\n"
                "- **Уточнение (2026-08-31):** дополнено.\n"
                "- **Критерий закрытия:** зелёный CI.\n",
            )
            result = check_audit_register_cards(root)
        self.assertEqual(result.errors, [])

    def test_missing_register_file_is_not_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = check_audit_register_cards(Path(tmp))
        self.assertEqual(result.errors, [])

    def test_missing_archival_card_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audit_dir = root / "work/audit"
            audit_dir.mkdir(parents=True)
            (audit_dir / "audit_register.md").write_text(self.REGISTER, encoding="utf-8")

            result = check_audit_register_cards(root)

        self.assertFalse(result.ok)
        self.assertTrue(any("отсутствует карточка" in error for error in result.errors))

    def test_duplicate_archival_card_is_rejected(self) -> None:
        card = (
            '<a id="aud-001"></a>\n### AUD-001 — title\n\n'
            "- **Severity/Confidence/Evidence state:** low / high / CONFIRMED\n"
            "- **Baseline:** pre-existing\n"
            "- **Файл:** x.py\n"
            "- **Наблюдаемое поведение:** что-то.\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(root, card)
            (root / "work/audit/audit_baseline_2026_08_29.md").write_text(
                self.ARCHIVE_HEADER + card, encoding="utf-8"
            )

            result = check_audit_register_cards(root)

        self.assertFalse(result.ok)
        self.assertTrue(any("карточка дублируется" in error for error in result.errors))

    def test_archival_card_without_register_row_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audit_dir = root / "work/audit"
            audit_dir.mkdir(parents=True)
            (audit_dir / "audit_register.md").write_text(
                self.REGISTER.replace(
                    "| [AUD-001](audit_adhoc_cards.md#aud-001) | low | open | "
                    "2026-08-30 | 2026-09-30 | owner | proof | fix |\n",
                    "",
                ),
                encoding="utf-8",
            )
            (audit_dir / "audit_adhoc_cards.md").write_text(
                self.ARCHIVE_HEADER
                + '<a id="aud-001"></a>\n### AUD-001 — title\n\n'
                + "- **Severity/Confidence/Evidence state:** low / high / CONFIRMED\n"
                + "- **Baseline:** pre-existing\n"
                + "- **Файл:** x.py\n"
                + "- **Наблюдаемое поведение:** что-то.\n",
                encoding="utf-8",
            )

            result = check_audit_register_cards(root)

        self.assertFalse(result.ok)
        self.assertTrue(any("отсутствует в реестре" in error for error in result.errors))

    def test_bare_register_id_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root,
                '<a id="aud-001"></a>\n### AUD-001 — title\n\n'
                "- **Severity/Confidence/Evidence state:** low / high / CONFIRMED\n"
                "- **Baseline:** pre-existing\n"
                "- **Файл:** x.py\n"
                "- **Наблюдаемое поведение:** что-то.\n",
            )
            register = root / "work/audit/audit_register.md"
            register.write_text(
                register.read_text(encoding="utf-8").replace(
                    "[AUD-001](audit_adhoc_cards.md#aud-001)", "AUD-001"
                ),
                encoding="utf-8",
            )

            result = check_audit_register_cards(root)

        self.assertTrue(any("ID в реестре должен быть ссылкой" in error for error in result.errors))

    def test_wrong_register_id_target_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root,
                '<a id="aud-001"></a>\n### AUD-001 — title\n\n'
                "- **Severity/Confidence/Evidence state:** low / high / CONFIRMED\n"
                "- **Baseline:** pre-existing\n"
                "- **Файл:** x.py\n"
                "- **Наблюдаемое поведение:** что-то.\n",
            )
            register = root / "work/audit/audit_register.md"
            register.write_text(
                register.read_text(encoding="utf-8").replace(
                    "audit_adhoc_cards.md#aud-001", "audit_baseline_2026_08_30.md#aud-001"
                ),
                encoding="utf-8",
            )

            result = check_audit_register_cards(root)

        self.assertTrue(any("ожидалась карточка" in error for error in result.errors))

    def test_card_link_in_evidence_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root,
                '<a id="aud-001"></a>\n### AUD-001 — title\n\n'
                "- **Severity/Confidence/Evidence state:** low / high / CONFIRMED\n"
                "- **Baseline:** pre-existing\n"
                "- **Файл:** x.py\n"
                "- **Наблюдаемое поведение:** что-то.\n",
            )
            register = root / "work/audit/audit_register.md"
            register.write_text(
                register.read_text(encoding="utf-8").replace(
                    "| proof |", "| [card](audit_adhoc_cards.md#aud-001) |"
                ),
                encoding="utf-8",
            )

            result = check_audit_register_cards(root)

        self.assertTrue(any("Evidence не должен" in error for error in result.errors))

    def test_compatibility_index_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write(
                root,
                '<a id="aud-001"></a>\n### AUD-001 — title\n\n'
                "- **Severity/Confidence/Evidence state:** low / high / CONFIRMED\n"
                "- **Baseline:** pre-existing\n"
                "- **Файл:** x.py\n"
                "- **Наблюдаемое поведение:** что-то.\n",
            )
            register = root / "work/audit/audit_register.md"
            register.write_text(
                register.read_text(encoding="utf-8") + "\n## 4. Индекс совместимости\n",
                encoding="utf-8",
            )

            result = check_audit_register_cards(root)

        self.assertTrue(any("индекс совместимости запрещён" in error for error in result.errors))


class ArchitectureDiagramCheckTests(unittest.TestCase):
    def test_no_targets_is_not_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = check_architecture_diagrams(Path(tmp))
        self.assertEqual(result.errors, [])
        self.assertEqual(result.warnings, [])

    def test_aggregates_lint_errors_and_warnings_across_targets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artefacts = root / "work" / "artefacts"
            artefacts.mkdir(parents=True)
            (artefacts / "broken.svg").write_text(
                '<svg width="10" height="10"></svg>', encoding="utf-8"
            )
            result = check_architecture_diagrams(root)
        self.assertFalse(result.ok)
        self.assertTrue(any("broken.svg" in error for error in result.errors))

    def test_passes_on_well_formed_diagram(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec = root / "specifications" / "example.md"
            spec.parent.mkdir(parents=True)
            spec.write_text(
                "---\nversion: 1.0\n---\n\n### ARC_CMP_001 — Test\n\nBody.\n",
                encoding="utf-8",
            )
            artefacts = root / "work" / "artefacts"
            artefacts.mkdir(parents=True)
            (artefacts / "diagram.svg").write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" '
                'viewBox="0 0 10 10" role="img" aria-labelledby="title desc">\n'
                '  <title id="title">Title</title>\n'
                '  <desc id="desc">Desc</desc>\n'
                "  <!-- diagram-metadata\n"
                "diagram_id: test\n"
                "diagram_version: 1.0\n"
                "generated_at: 2026-09-01\n"
                "status: current\n"
                "source: specifications/example.md@1.0\n"
                "id: ARC_CMP_001\n"
                "end-diagram-metadata -->\n"
                '  <g data-spec-id="ARC_CMP_001"></g>\n'
                "</svg>\n",
                encoding="utf-8",
            )
            result = check_architecture_diagrams(root)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.warnings, [])


if __name__ == "__main__":
    unittest.main()
