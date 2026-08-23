from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from operations.scripts.common.status_types import MilestoneItem
from operations.scripts.documents.check import (
    _block_scalar_errors,
    check_automation_policy,
    check_business_requirements_coverage,
    check_milestones,
)
from operations.scripts.evidence.record import _evidence_targets
from operations.scripts.quality.registry import QualityProfile, _matches, uncovered_paths
from operations.scripts.status.generate_project_status import (
    AcceptanceResult,
    CoverageResult,
    EffectiveTestItem,
    ProgressSnapshot,
)


def _profile(*, paths: list[str]) -> QualityProfile:
    return {
        "milestones": ["m01"],
        "required_evidence": [],
        "paths": paths,
        "scope_coverage": "task_test",
        "scope_evidence": [],
    }


def _minimal_snapshot(
    milestone_id: str, *, evidence_id: str, verifies: list[str]
) -> ProgressSnapshot:
    milestone: MilestoneItem = {
        "id": milestone_id,
        "title": "",
        "work_state": "in-progress",
        "scope": [],
    }
    test: EffectiveTestItem = {
        "id": "TEST_001",
        "spec_state": "current",
        "execution": "automated",
        "automated_evidence": evidence_id,
        "manual_evidence": "",
        "traces_to": [],
        "verifies": verifies,
        "accepts": [milestone_id],
        "title": "",
        "path": "",
        "effective_result": "passed",
    }
    coverage: CoverageResult = {
        "scope_total": 0,
        "scope_covered": 0,
        "scope": [],
        "covered": [],
        "tracked_kind": "foundation_paths",
        "tracked_total": 0,
        "tracked_covered": 0,
        "tracked_targets": [],
        "blockers": [],
        "modes": [],
    }
    acceptance: AcceptanceResult = {
        "state": "not-ready",
        "technical_ready": False,
        "accepted": False,
        "pending_gates": [],
        "owner_action": "none",
        "tasks_total": 0,
        "tasks_verified": 0,
        "tests_total": 1,
        "tests_passed": 1,
        "tests": [test],
        "quality": {"profiles": [], "evidence": [], "blockers": [], "warnings": [], "ready": True},
        "coverage": coverage,
        "evidence_results": {},
        "evidence_context": {},
        "changed_paths": [],
        "coverage_base": {"mode": "tracked_tree", "git_sha": None},
        "uncovered_paths": [],
        "impacted_profiles": [],
        "documents_total": 0,
        "documents_current": 0,
        "decisions_proposed": 0,
        "remaining": [],
        "blockers": [],
    }
    return {
        "overall": "healthy",
        "milestones": {"count": 1, "items": [milestone], "current": milestone, "states": {}},
        "current": milestone,
        "next_milestone": None,
        "tasks": {"count": 0, "states": {}, "tasks": []},
        "tests": {"count": 1, "items": [], "states": {}},
        "checks_passed": 0,
        "checks_total": 0,
        "check_summary": {},
        "unit": {
            "ok": True,
            "total": 0,
            "passed": 0,
            "failed": 0,
            "duration": None,
            "label": "",
            "problems": [],
        },
        "acceptance": acceptance,
        "deviations": [],
        "next_action": {
            "actor": "владелец",
            "instruction": "",
            "commands": [],
            "requires_fresh_session": False,
        },
        "git": {},
    }


MINIMAL_PROJECT_WORKFLOW = """\
name: Project check
on:
  workflow_dispatch:
  pull_request:
{push_block}
permissions:
  contents: read
  pull-requests: read
jobs:
  check:
    runs-on: windows-latest
    steps:
      - run: gh api "repos/$env:GITHUB_REPOSITORY/commits/$env:GITHUB_SHA/pulls"
  linux-smoke:
    runs-on: ubuntu-latest
    steps: []
"""

MINIMAL_DAILY_WORKFLOW = """\
name: Daily project status
on:
  schedule:
    - cron: "0 0 * * *"
  workflow_dispatch:
permissions:
  contents: read
jobs:
  update:
    runs-on: windows-latest
    steps: []
"""


class GovernanceHardeningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[2]

    def test_dot_directory_path_matches_without_losing_leading_dot(self) -> None:
        self.assertTrue(_matches(".github/workflows/project_check.yml", [".github/workflows/**"]))
        profiles: list[tuple[str, QualityProfile]] = [
            ("foundation", _profile(paths=[".github/workflows/**"]))
        ]
        self.assertEqual(uncovered_paths(profiles, [".github/workflows/project_check.yml"]), [])

    def test_derived_paths_do_not_block_profile_coverage(self) -> None:
        profiles: list[tuple[str, QualityProfile]] = [
            ("foundation", _profile(paths=["operations/**"]))
        ]
        self.assertEqual(
            uncovered_paths(
                profiles, ["generated/traceability_matrix.md", "runtime/evidence/x.json"]
            ),
            [],
        )

    def test_accepts_and_empty_product_scope_never_produce_empty_evidence_targets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "operations").mkdir()
            registry = {
                "version": 1,
                "evidence_catalog": {"unit_tests": {"class": "hard", "source": "unit_tests"}},
                "profiles": {
                    "foundation": {
                        "milestones": ["m01"],
                        "paths": ["operations/**"],
                        "scope_coverage": "global_evidence",
                        "scope_evidence": ["unit_tests"],
                        "required_evidence": ["unit_tests"],
                    }
                },
            }
            (root / "operations/quality_registry.json").write_text(
                json.dumps(registry), encoding="utf-8"
            )
            snapshot = _minimal_snapshot("m01", evidence_id="unit_tests", verifies=["SEC_CTL_018"])
            targets = _evidence_targets(root, snapshot)
            self.assertEqual(targets["unit_tests"], ["path:operations/**"])
            self.assertTrue(targets["unit_tests"])

    def test_publication_and_acceptance_rules_are_consistent(self) -> None:
        change_process = (self.root / "operations/change_process.md").read_text(
            encoding="utf-8-sig"
        )
        instruction = (self.root / "AGENTS.md").read_text(encoding="utf-8-sig")
        acceptance = (self.root / "operations/acceptance.md").read_text(encoding="utf-8-sig")

        self.assertIn("Все изменения агента выполняются в отдельной ветке", change_process)
        self.assertIn("автоматически обнаружена", change_process)
        self.assertIn("operations/change_process.md", instruction)
        self.assertIn("operations/acceptance.md", instruction)
        self.assertIn("operations/semantic_review.md", instruction)
        self.assertNotIn("`main` защищается правилами GitHub", change_process)
        self.assertNotIn("через защищённый `main`", acceptance)
        self.assertLess(
            len(instruction.splitlines()), 200
        )  # Section 3.6 added for interactive processes

    def test_document_templates_use_current_russian_structure(self) -> None:
        templates = "\n".join(
            path.read_text(encoding="utf-8-sig")
            for path in sorted((self.root / "operations/templates").glob("*.md"))
        )
        milestone = (self.root / "operations/templates/milestone_template.md").read_text(
            encoding="utf-8-sig"
        )

        self.assertIn("- состав:", milestone)
        self.assertNotIn("- scope:", milestone)
        for stale_phrase in [
            "provider/backend",
            "step → step",
            "technology choice",
            "после controls",
            "проверяются checker",
            "business-level draft scope",
            "quality profile",
        ]:
            self.assertNotIn(stale_phrase, templates)

    def test_milestone_state_machine_rejects_multiple_active_and_skipped_completion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "milestones.md").write_text(
                "## m01 — Основа\n\n- work_state: `in-progress`\n\n"
                "## m02 — Следующий\n\n- work_state: `in-progress`\n- состав: `SYS_001`\n\n"
                "## m03 — Поздний\n\n- work_state: `completed`\n",
                encoding="utf-8",
            )
            errors = check_milestones(root).errors
            self.assertTrue(any("только один" in error for error in errors), errors)
            self.assertTrue(any("непрерывный префикс" in error for error in errors), errors)

    def test_business_requirements_coverage_accepts_complete_disjoint_split(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "specifications").mkdir()
            (root / "specifications/business_requirements.md").write_text(
                "### BR_001 — A\n### BR_002 — B\n### BR_003 — C\n",
                encoding="utf-8",
            )
            (root / "milestones.md").write_text(
                "Обязательный состав продукта: `BR_001`, `BR_002`.\n\n"
                "## m01 — Основа\n\n- work_state: `in-progress`\n\n"
                "## m02 — Далее\n\n- work_state: `planned`\n- состав: `BR_001`, `BR_002`.\n\n"
                "## 3. Кандидатные направления после V1\n\n"
                "| BR | Требование |\n|---|---|\n"
                "| [`BR_003`](specifications/business_requirements.md#br_003) | C |\n",
                encoding="utf-8",
            )
            self.assertEqual(check_business_requirements_coverage(root).errors, [])

    def _write_minimal_automation_fixture(
        self,
        root: Path,
        *,
        with_push_trigger: bool,
        push_paths_filter: bool = False,
    ) -> None:
        (root / ".github/workflows").mkdir(parents=True)
        (root / "operations/scripts/automation").mkdir(parents=True)
        (root / "operations/scripts/acceptance").mkdir(parents=True)
        push_block = ""
        if with_push_trigger:
            push_block = "  push:\n    branches:\n      - main\n"
            if push_paths_filter:
                push_block += "    paths-ignore:\n      - '**'\n"
        workflow = MINIMAL_PROJECT_WORKFLOW.format(push_block=push_block)
        workflow += (
            "      - run: py operations\\scripts\\tasks\\check_change_scope.py --base x --head y\n"
        )
        (root / ".github/workflows/project_check.yml").write_text(workflow, encoding="utf-8")
        (root / ".github/workflows/daily_project_status.yml").write_text(
            MINIMAL_DAILY_WORKFLOW, encoding="utf-8"
        )
        (root / "operations/scripts/automation/run_daily.ps1").write_text(
            "# no-op\n", encoding="utf-8"
        )
        (root / "operations/scripts/acceptance/apply.py").write_text(
            "validate_semantic_review\n--semantic-review\n",
            encoding="utf-8",
        )

    def test_automation_policy_requires_push_trigger_on_main(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_minimal_automation_fixture(root, with_push_trigger=False)
            errors = check_automation_policy(root).errors
            self.assertTrue(any("push на main" in error for error in errors), errors)

    def test_automation_policy_accepts_push_trigger_on_main(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_minimal_automation_fixture(root, with_push_trigger=True)
            errors = check_automation_policy(root).errors
            self.assertFalse(any("push на main" in error for error in errors), errors)

    def test_automation_policy_rejects_path_filtered_push_trigger(self) -> None:
        """Отфильтрованный триггер молча перестаёт срабатывать на прямых изменениях main."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_minimal_automation_fixture(
                root, with_push_trigger=True, push_paths_filter=True
            )
            errors = check_automation_policy(root).errors
            self.assertTrue(any("path-filter" in error for error in errors), errors)

    def test_business_requirements_coverage_rejects_missing_and_overlapping_br(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "specifications").mkdir()
            (root / "specifications/business_requirements.md").write_text(
                "### BR_001 — A\n### BR_002 — B\n### BR_003 — C\n",
                encoding="utf-8",
            )
            (root / "milestones.md").write_text(
                "Обязательный состав продукта: `BR_001`.\n\n"
                "## m01 — Основа\n\n- work_state: `in-progress`\n\n"
                "## 3. Кандидатные направления после V1\n\n"
                "| BR | Требование |\n|---|---|\n"
                "| [`BR_001`](specifications/business_requirements.md#br_001) | A |\n",
                encoding="utf-8",
            )
            errors = check_business_requirements_coverage(root).errors
            self.assertTrue(
                any("BR_002" in error and "не входит ни в состав V1" in error for error in errors),
                errors,
            )
            self.assertTrue(any("одновременно в составе V1" in error for error in errors), errors)
            self.assertTrue(
                any("не поставляет его через строку" in error for error in errors), errors
            )

    def test_automation_policy_rejects_non_read_workflow_permission(self) -> None:
        """Полномочия автоматизации расширяются одной строкой в permissions,
        поэтому запрещено любое значение кроме read/none, а не только contents: write."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_minimal_automation_fixture(root, with_push_trigger=True)
            path = root / ".github/workflows/project_check.yml"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    "permissions:\n  contents: read\n",
                    "permissions:\n  contents: read\n  id-token: write\n",
                ),
                encoding="utf-8",
            )
            errors = check_automation_policy(root).errors
            self.assertTrue(
                any("расширяет полномочия автоматизации" in error for error in errors), errors
            )

    def test_automation_policy_accepts_additional_read_permission(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_minimal_automation_fixture(root, with_push_trigger=True)
            path = root / ".github/workflows/project_check.yml"
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    "permissions:\n  contents: read\n",
                    "permissions:\n  contents: read\n  pull-requests: read\n",
                ),
                encoding="utf-8",
            )
            errors = check_automation_policy(root).errors
            self.assertFalse(any("расширяет полномочия" in error for error in errors), errors)

    def test_workflow_block_scalar_break_is_detected(self) -> None:
        """Продолжение многострочного скрипта на нулевом отступе молча закрывает
        блок YAML и ломает рабочий процесс целиком."""
        intact = (
            "jobs:\n  check:\n    steps:\n      - name: Run\n        run: |\n"
            "          set -e\n          echo ok\n"
        )
        broken = (
            "jobs:\n  check:\n    steps:\n      - name: Run\n        run: |\n"
            "          set -e\nprint('оторвалось')\n"
        )
        self.assertEqual(_block_scalar_errors("project_check.yml", intact), [])
        self.assertTrue(
            any(
                "разрывает его" in error
                for error in _block_scalar_errors("project_check.yml", broken)
            )
        )

    def test_business_requirements_coverage_allows_candidates_after_v1_boundary(self) -> None:
        """Планирование кандидатов на этапе после V1 — прямая задача такого этапа,
        а не поставка кандидата до приёмки V1."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "specifications").mkdir()
            (root / "specifications/business_requirements.md").write_text(
                "### BR_001 — A\n\n- priority: `core`\n\n### BR_002 — B\n\n- priority: `important`\n",
                encoding="utf-8",
            )
            (root / "milestones.md").write_text(
                "Его поставка завершается после `m02`.\n\n"
                "Обязательный состав продукта: `BR_001`.\n\n"
                "## m01 — Основа\n\n- work_state: `in-progress`\n\n"
                "## m02 — Поставка\n\n- work_state: `planned`\n- состав: `BR_001`.\n\n"
                "## m03 — Следующий цикл\n\n- work_state: `planned`\n- состав: `BR_002`.\n\n"
                "## 3. Кандидатные направления после V1\n\n"
                "| BR | Требование | Приоритет | Направление |\n|---|---|---|---|\n"
                "| [`BR_002`](specifications/business_requirements.md#br_002) | B | `important` | Позже |\n",
                encoding="utf-8",
            )
            self.assertEqual(check_business_requirements_coverage(root).errors, [])

    def test_business_requirements_coverage_rejects_core_requirement_deferred_past_v1(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "specifications").mkdir()
            (root / "specifications/business_requirements.md").write_text(
                "### BR_001 — A\n\n- priority: `core`\n\n### BR_002 — B\n\n- priority: `core`\n",
                encoding="utf-8",
            )
            (root / "milestones.md").write_text(
                "Его поставка завершается после `m02`.\n\n"
                "Обязательный состав продукта: `BR_001`.\n\n"
                "## m01 — Основа\n\n- work_state: `in-progress`\n\n"
                "## m02 — Поставка\n\n- work_state: `planned`\n- состав: `BR_001`.\n\n"
                "## 3. Кандидатные направления после V1\n\n"
                "| BR | Требование | Приоритет | Направление |\n|---|---|---|---|\n"
                "| [`BR_002`](specifications/business_requirements.md#br_002) | B | `important` | Позже |\n",
                encoding="utf-8",
            )
            errors = check_business_requirements_coverage(root).errors
            self.assertTrue(
                any("`core` отложен за пределы V1" in error for error in errors), errors
            )
            self.assertTrue(any("разошёлся с каталогом" in error for error in errors), errors)

    def test_business_requirements_coverage_rejects_non_core_inside_v1(self) -> None:
        """Периметр V1 равен множеству core в обе стороны: иначе состав и приоритет
        становятся двумя равноправными источниками одного смысла."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "specifications").mkdir()
            (root / "specifications/business_requirements.md").write_text(
                "### BR_001 — A\n\n- priority: `core`\n\n### BR_002 — B\n\n- priority: `important`\n",
                encoding="utf-8",
            )
            (root / "milestones.md").write_text(
                "Его поставка завершается после `m02`.\n\n"
                "Обязательный состав продукта: `BR_001`, `BR_002`.\n\n"
                "## m01 — Основа\n\n- work_state: `in-progress`\n\n"
                "## m02 — Поставка\n\n- work_state: `planned`\n- состав: `BR_001`, `BR_002`.\n\n"
                "## 3. Кандидатные направления после V1\n\n"
                "| BR | Требование | Приоритет | Направление |\n|---|---|---|---|\n",
                encoding="utf-8",
            )
            errors = check_business_requirements_coverage(root).errors
            self.assertTrue(
                any("без приоритета `core` включён" in error for error in errors), errors
            )


if __name__ == "__main__":
    unittest.main()
