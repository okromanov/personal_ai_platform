from __future__ import annotations

import tempfile
import unittest
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from unittest.mock import patch

from operations.scripts.documents.check import (
    _branch_cleanup_errors,
    _known_reference_ids,
    _task_test_plan_item_errors,
    check_acceptance_adr_transitions,
    check_acceptance_model,
    check_architecture_diagrams,
    check_audit_register_cards,
    check_authority_graph,
    check_automation_policy,
    check_business_requirements_coverage,
    check_document_discoverability,
    check_document_policy,
    check_document_readability,
    check_instruction_consistency,
    check_markdown_section_order,
    check_metadata,
    check_secrets,
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

    def test_metadata_rejects_invalid_applicability_and_active_superseded_doc(self) -> None:
        documents = [
            (
                "one.md",
                MarkdownDocument(
                    Path("one.md"),
                    {
                        "id": "DOC_001",
                        "type": "guide",
                        "version": "1.0",
                        "updated": "2026-09-03",
                        "document_state": "superseded",
                        "applicability": "normative",
                    },
                    "",
                    "One",
                ),
            ),
            (
                "two.md",
                MarkdownDocument(
                    Path("two.md"),
                    {
                        "id": "DOC_002",
                        "type": "guide",
                        "version": "1.0",
                        "updated": "2026-09-03",
                        "document_state": "current",
                        "applicability": "sometimes",
                    },
                    "",
                    "Two",
                ),
            ),
        ]
        with (
            patch("operations.scripts.documents.check._primary_documents", return_value=documents),
            patch("operations.scripts.documents.check._known_reference_ids", return_value=set()),
        ):
            result = check_metadata(Path("."))
        joined = "\n".join(result.errors)
        self.assertIn("неизвестный applicability 'sometimes'", joined)
        self.assertIn("superseded-документ должен иметь applicability=historical", joined)

    def test_instruction_consistency_rejects_known_drift_and_launchers(self) -> None:
        document = MarkdownDocument(
            Path("guide.md"),
            {
                "id": "guide",
                "type": "guide",
                "version": "1.0",
                "updated": "2026-09-03",
                "document_state": "current",
                "applicability": "normative",
            },
            "AskUserQuestion\nПрочитать только нужные части.\n"
            "python3 -m operations.example\npy operations\\tool.py\n",
            "Guide",
        )

        def fake_read(path: Path) -> str:
            if path.name == "record_quality_suite.py":
                return '"command": ["python3.12",'
            return "{}"

        with (
            patch(
                "operations.scripts.documents.check._primary_documents",
                return_value=[("operations/guide.md", document)],
            ),
            patch("operations.scripts.documents.check.read_text", side_effect=fake_read),
        ):
            result = check_instruction_consistency(Path("."))
        joined = "\n".join(result.errors)
        self.assertIn("AskUserQuestion", joined)
        self.assertIn("выборочным чтением", joined)
        self.assertIn("POSIX-команда", joined)
        self.assertIn("Windows-команда", joined)

    def test_instruction_consistency_covers_inactive_playbook_and_registry_drift(self) -> None:
        metadata = {
            "id": "guide",
            "type": "guide",
            "version": "1.0",
            "updated": "2026-09-03",
            "document_state": "current",
            "applicability": "normative",
        }
        documents = [
            (
                "operations/inactive.md",
                MarkdownDocument(
                    Path("inactive.md"),
                    dict(metadata, id="inactive", applicability="proposed"),
                    "AskUserQuestion",
                    "Inactive",
                ),
            ),
            (
                "operations/quality/playbooks/tool.md",
                MarkdownDocument(Path("tool.md"), dict(metadata, id="tool"), "Run Pylint.", "Tool"),
            ),
            (
                "operations/quality/playbooks/readme.md",
                MarkdownDocument(
                    Path("readme.md"),
                    dict(metadata, id="readme"),
                    "**Version:** 1.0",
                    "Readme",
                ),
            ),
        ]

        def fake_read(path: Path) -> str:
            if path.name == "non_markdown_index.py":
                return "проверяется и еженедельно"
            if path.name == "record_quality_suite.py":
                return '"command": ["python",'
            return '{"command": "python3 -m operations.tool"}'

        with (
            patch("operations.scripts.documents.check._primary_documents", return_value=documents),
            patch("operations.scripts.documents.check.read_text", side_effect=fake_read),
        ):
            result = check_instruction_consistency(Path("."))
        joined = "\n".join(result.errors)
        self.assertNotIn("inactive.md", joined)
        self.assertIn("canonical gate", joined)
        self.assertIn("front matter", joined)
        self.assertIn("weekly workflow", joined)
        self.assertIn("canonical launcher", joined)
        self.assertIn("quality_registry.json", joined)

    def test_instruction_consistency_requires_branch_cleanup_after_merge(self) -> None:
        document = MarkdownDocument(
            Path("AGENTS.md"),
            {
                "id": "coding_agent_instruction",
                "type": "agent_instruction",
                "version": "4.2",
                "updated": "2026-09-04",
                "document_state": "current",
                "applicability": "normative",
            },
            "Открыть PR, дождаться серверной проверки и слить.",
            "Инструкция агенту разработки",
        )

        def fake_read(path: Path) -> str:
            if path.name == "record_quality_suite.py":
                return '"command": ["python3.12",'
            return "{}"

        with (
            patch(
                "operations.scripts.documents.check._primary_documents",
                return_value=[("AGENTS.md", document)],
            ),
            patch("operations.scripts.documents.check.read_text", side_effect=fake_read),
        ):
            result = check_instruction_consistency(Path("."))
        self.assertIn("после merge требуется удалять рабочую ветку", "\n".join(result.errors))

    def test_readability_and_discoverability_only_apply_to_active_instructions(self) -> None:
        metadata = {
            "id": "hidden_guide",
            "type": "guide",
            "version": "1.0",
            "updated": "2026-09-03",
            "document_state": "current",
            "applicability": "normative",
        }
        active = MarkdownDocument(Path("hidden.md"), metadata, "x" * 601, "Hidden")
        with (
            patch(
                "operations.scripts.documents.check._primary_documents",
                return_value=[("operations/hidden.md", active)],
            ),
            patch("operations.scripts.documents.check.read_text", return_value="{}"),
        ):
            readability = check_document_readability(Path("."))
            discoverability = check_document_discoverability(Path("."))
        self.assertTrue(readability.warnings)
        self.assertIn("недоступен из навигации", "\n".join(discoverability.errors))

        proposed = MarkdownDocument(
            Path("hidden.md"), dict(metadata, applicability="proposed"), "x" * 601, "Hidden"
        )
        with (
            patch(
                "operations.scripts.documents.check._primary_documents",
                return_value=[("operations/hidden.md", proposed)],
            ),
            patch("operations.scripts.documents.check.read_text", return_value="{}"),
        ):
            self.assertEqual(check_document_readability(Path(".")).warnings, [])
            self.assertEqual(check_document_discoverability(Path(".")).errors, [])

    def test_readability_skips_exclusions_fences_and_tables(self) -> None:
        metadata = {
            "id": "guide",
            "type": "guide",
            "version": "1.0",
            "updated": "2026-09-03",
            "document_state": "current",
            "applicability": "normative",
        }
        documents = [
            (
                "work/tests/test_999.md",
                MarkdownDocument(Path("test_999.md"), metadata, "x" * 601, "Excluded"),
            ),
            (
                "operations/guide.md",
                MarkdownDocument(
                    Path("guide.md"),
                    metadata,
                    "```text\n" + "x" * 601 + "\n```\n| " + "x" * 601,
                    "Guide",
                ),
            ),
        ]
        with patch("operations.scripts.documents.check._primary_documents", return_value=documents):
            self.assertEqual(check_document_readability(Path(".")).warnings, [])

    def test_discoverability_counts_links_metadata_and_skips_exempt_documents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "operations").mkdir()
            metadata = {
                "type": "guide",
                "version": "1.0",
                "updated": "2026-09-03",
                "document_state": "current",
                "applicability": "normative",
            }
            documents = [
                (
                    "operations/a.md",
                    MarkdownDocument(
                        root / "operations/a.md",
                        dict(metadata, id="a", depends_on=["c"]),
                        "[B](b.md) [Web](https://example.com) [Outside](../../outside.md)",
                        "A",
                    ),
                ),
                (
                    "operations/b.md",
                    MarkdownDocument(root / "operations/b.md", dict(metadata, id="b"), "", "B"),
                ),
                (
                    "operations/c.md",
                    MarkdownDocument(root / "operations/c.md", dict(metadata, id="c"), "", "C"),
                ),
                (
                    "work/tasks/task_999.md",
                    MarkdownDocument(
                        root / "work/tasks/task_999.md", dict(metadata, id="task"), "", "Task"
                    ),
                ),
            ]
            with (
                patch(
                    "operations.scripts.documents.check._primary_documents", return_value=documents
                ),
                patch(
                    "operations.scripts.documents.check.read_text", return_value="operations/a.md"
                ),
            ):
                result = check_document_discoverability(root)
        self.assertEqual(result.errors, [])

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
            "next_actor": "robot",
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
            "next_actor должен быть одним из",
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
        self.assertIn("разделы TEST должны быть ровно", joined)

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
                '  <text data-diagram-meta="version">Версия 1.0 · Обновлено 2026-09-01</text>\n'
                '  <g data-spec-id="ARC_CMP_001"></g>\n'
                "</svg>\n",
                encoding="utf-8",
            )
            result = check_architecture_diagrams(root)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.warnings, [])


class SecretScanTests(unittest.TestCase):
    """check_secrets — единственный контроль секретов в профиле `--fast`,
    то есть в pre-commit. До этих тестов весь SECRET_PATTERNS можно было
    обезвредить, не уронив ни одного из 636 тестов.

    Секретоподобные строки собираются из кусков: check_secrets сканирует в
    том числе `operations/tests/**/*.py`, поэтому цельный литерал сделал бы
    проверку самого репозитория красной.
    """

    def _scan(self, name: str, body: str = "") -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding="utf-8")
            return check_secrets(root).errors

    def test_forbidden_file_names_are_reported_regardless_of_content(self) -> None:
        for name in (".env", "id_rsa", "id_ed25519", "credentials.json"):
            with self.subTest(name=name):
                errors = self._scan(name, "harmless\n")
                self.assertTrue(
                    any(name in error for error in errors),
                    f"{name} должен считаться потенциальным секретом",
                )

    def test_private_key_suffixes_are_reported_regardless_of_content(self) -> None:
        for name in ("server.pem", "bundle.p12", "bundle.pfx"):
            with self.subTest(name=name):
                errors = self._scan(name, "harmless\n")
                self.assertTrue(any(name in error for error in errors), name)

    def test_each_secret_pattern_is_detected_in_a_scanned_text_file(self) -> None:
        cases = {
            "assignment": "api" + "_key = " + "A" * 24,
            "colon_form": "secret" + ": " + "b" * 20,
            "private_key_header": "-----BEGIN RSA PRIVATE" + " KEY-----",
            "provider_token": "gh" + "p_" + "0123456789abcdefghij",
        }
        for label, payload in cases.items():
            with self.subTest(case=label):
                errors = self._scan("notes.md", f"prefix\n{payload}\nsuffix\n")
                self.assertTrue(
                    any("похожий на секрет" in error for error in errors),
                    f"{label} не обнаружен",
                )

    def test_clean_scanned_file_produces_no_finding(self) -> None:
        self.assertEqual(self._scan("notes.md", "обычный текст без секретов\n"), [])

    def test_unscanned_suffix_is_skipped(self) -> None:
        payload = "gh" + "p_" + "0123456789abcdefghij"
        self.assertEqual(self._scan("blob.bin", payload), [])


class BranchCleanupWorkflowTests(unittest.TestCase):
    """Единственный workflow с `contents: write` проверяется по смыслу.

    Раньше его ограничения проверялись присутствием четырёх подстрок: добавленный
    `PUT /repos/{repo}/contents/...` при всех сохранённых гардах проходил проверку
    без единой ошибки. Теперь `on`, `permissions` и условие job читаются как YAML,
    то есть проверяются фактические значения, а обращения к API сверяются с
    белым списком.
    """

    WORKFLOW = """name: Delete merged branches

on:
  pull_request:
    types:
      - closed

permissions:
  contents: write
  pull-requests: read

jobs:
  cleanup:
    if: >-
      github.event.pull_request.merged == true &&
      github.event.pull_request.head.repo.full_name == github.repository
    runs-on: ubuntu-latest
    steps:
      - name: Delete
        shell: python
        run: |
          batch = request("GET", f"/repos/{repository}/branches")
          for branch in branches:
              if not name.startswith("codex/"):
                  continue
              request("DELETE", f"/repos/{repository}/git/refs/{encoded_ref}")
"""

    def _errors(self, text: str) -> list[str]:
        return _branch_cleanup_errors("delete_merged_branches.yml", text)

    def test_reference_shape_passes(self) -> None:
        self.assertEqual(self._errors(self.WORKFLOW), [])

    def test_write_call_outside_the_allowlist_is_rejected(self) -> None:
        mutated = self.WORKFLOW.replace(
            '          batch = request("GET"',
            '          request("PUT", f"/repos/{repository}/contents/x.md")\n'
            '          batch = request("GET"',
            1,
        )
        errors = self._errors(mutated)
        self.assertTrue(any("не входит в белый список" in error for error in errors), errors)

    def test_merged_guard_is_read_from_the_job_condition(self) -> None:
        mutated = self.WORKFLOW.replace("github.event.pull_request.merged == true", "true", 1)
        errors = self._errors(mutated)
        self.assertTrue(any("merged == true" in error for error in errors), errors)

    def test_extra_trigger_is_rejected(self) -> None:
        mutated = self.WORKFLOW.replace(
            "on:\n  pull_request:", "on:\n  workflow_dispatch:\n  pull_request:", 1
        )
        errors = self._errors(mutated)
        self.assertTrue(any("единственный допустимый триггер" in error for error in errors), errors)

    def test_widened_permissions_are_rejected(self) -> None:
        mutated = self.WORKFLOW.replace("  pull-requests: read", "  pull-requests: write", 1)
        errors = self._errors(mutated)
        self.assertTrue(any("допустимы ровно" in error for error in errors), errors)

    def test_second_job_is_rejected(self) -> None:
        mutated = self.WORKFLOW + "  extra:\n    runs-on: ubuntu-latest\n"
        errors = self._errors(mutated)
        self.assertTrue(any("ровно один job" in error for error in errors), errors)

    def test_unparseable_yaml_fails_closed(self) -> None:
        errors = self._errors("on: [\n")
        self.assertTrue(any("не удалось разобрать YAML" in error for error in errors), errors)

    def test_codex_prefix_restriction_must_remain(self) -> None:
        mutated = self.WORKFLOW.replace('name.startswith("codex/")', "True", 1)
        errors = self._errors(mutated)
        self.assertTrue(any("codex/*" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
