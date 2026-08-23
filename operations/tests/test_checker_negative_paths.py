from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from operations.scripts.documents.check import (
    check_acceptance_model,
    check_authority_graph,
    check_automation_policy,
    check_business_requirements_coverage,
    check_document_policy,
    check_metadata,
    check_tasks,
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
        }
        planned = dict(task, id="TASK_002", next_actor="none", owner_action="none")
        planned["work_state"] = "planned"
        with (
            patch(
                "operations.scripts.documents.check.collect_tasks",
                return_value={"tasks": [task, planned]},
            ),
            patch("operations.scripts.documents.check.render_task_index", return_value="index"),
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
        ):
            self.assertIn(fragment, joined)

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
            patch("operations.scripts.documents.check.render_task_index", return_value="index"),
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
            patch("operations.scripts.documents.check.render_task_index", return_value="index"),
            patch("operations.scripts.documents.check.read_text", return_value="index"),
            patch.object(Path, "exists", return_value=True),
        ):
            filled_result = check_tasks(Path("."))
        self.assertNotIn("шаблонной заглушкой", "\n".join(filled_result.errors))

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


if __name__ == "__main__":
    unittest.main()
