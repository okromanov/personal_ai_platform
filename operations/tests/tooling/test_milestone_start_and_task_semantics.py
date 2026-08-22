from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from operations.scripts.common.project import CommandResult
from operations.scripts.milestones import start as milestone_start
from operations.scripts.milestones.start import (
    _transition,
    preflight_start,
    start_milestone,
)
from operations.scripts.tasks.semantics import (
    delivery_closure,
    milestone_test_coverage_semantic,
    validate_task_semantics,
)


class MilestoneStartAndTaskSemanticsTests(unittest.TestCase):
    def _fixture(self, root: Path, *, unrelated: bool = False, with_test: bool = True) -> None:
        (root / "operations").mkdir()
        (root / "work/tasks").mkdir(parents=True)
        (root / "work/tests").mkdir(parents=True)
        (root / "specifications").mkdir()
        (root / "milestones.md").write_text(
            "---\nid: milestones\ntype: roadmap\ndocument_state: current\nversion: 1.0\n"
            "updated: 2026-08-20\n---\n\n"
            "## m01 — Foundation\n\n- work_state: `completed`\n\n"
            "## m02 — Feature\n\n- work_state: `planned`\n"
            "- состав: `BR_001`, `SYS_001`\n",
            encoding="utf-8",
        )
        (root / "specifications/model.md").write_text(
            "### BR_001 — Goal\n\n"
            "### BR_002 — Other\n\n"
            "### SYS_001 — Contract\n\n- `traces_to`: `BR_001`\n\n"
            "### ARC_CMP_001 — Adapter\n\n- `traces_to`: `SYS_001`\n",
            encoding="utf-8",
        )
        (root / "operations/quality_registry.json").write_text(
            json.dumps(
                {
                    "evidence_catalog": {"e": {"class": "hard", "source": "future"}},
                    "profiles": {
                        "m02": {
                            "milestones": ["m02"],
                            "paths": ["src/**"],
                            "scope_coverage": "task_test",
                            "required_evidence": ["e"],
                        }
                    },
                }
            ),
            encoding="utf-8",
        )
        implemented = "BR_002" if unrelated else "ARC_CMP_001"
        (root / "work/tasks/task_0001_adapter.md").write_text(
            "---\nid: TASK_0001\ntype: task\ntitle: Adapter\ncomponent: ARC_CMP_001\n"
            "work_state: planned\nversion: 1.0\nupdated: 2026-08-20\n"
            "next_actor: agent\nowner_action: none\nallowed_paths:\n"
            "  - work/tasks/task_0001_adapter.md\ntraces_to:\n  - m02\nimplements:\n"
            f"  - {implemented}\n---\n# TASK_0001 — Adapter\n\n"
            "## 5. План выполнения\n\n- [ ] Build\n",
            encoding="utf-8",
        )
        if with_test:
            (root / "work/tests/test_0001.md").write_text(
                "---\nid: TEST_0001\ntype: test\nspec_state: current\nversion: 1.0\n"
                "traces_to:\n  - TASK_0001\nverifies:\n  - SYS_001\naccepts:\n  - m02\n"
                "automated_evidence: e\n---\n# TEST_0001 — Adapter\n",
                encoding="utf-8",
            )

    def test_semantic_closure_and_valid_preflight_cover_transitive_business_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fixture(root)
            required, covered = milestone_test_coverage_semantic(root, "m02")
            self.assertEqual(required, {"BR_001", "SYS_001"})
            self.assertEqual(covered, required)
            self.assertEqual(validate_task_semantics(root, "m02"), [])
            self.assertEqual(preflight_start(root, "m02"), [])
            before = (root / "milestones.md").read_text(encoding="utf-8")
            self.assertEqual(start_milestone(root, "m02", dry_run=True), [])
            self.assertEqual((root / "milestones.md").read_text(encoding="utf-8"), before)

    def test_unrelated_component_claim_and_missing_test_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fixture(root, unrelated=True, with_test=False)
            errors = validate_task_semantics(root, "m02")
            joined = "\n".join(errors)
            self.assertIn("implements вне семантики", joined)
            self.assertIn("не связан ни с одним TEST", joined)
            self.assertIn("scope не покрыт", joined)
            self.assertTrue(preflight_start(root, "m02"))

    def test_apply_is_atomic_after_preflight_and_updates_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fixture(root)
            branch = CommandResult(("git",), 0, "feature\n", "")
            with (
                patch("operations.scripts.milestones.start.run_command", return_value=branch),
                patch("operations.scripts.milestones.start.today_iso", return_value="2026-08-21"),
            ):
                self.assertEqual(start_milestone(root, "m02", dry_run=False), [])
            text = (root / "milestones.md").read_text(encoding="utf-8")
            self.assertIn("updated: 2026-08-21", text)
            self.assertIn("- work_state: `in-progress`", text)

            with self.assertRaisesRegex(ValueError, "ожидается"):
                _transition(text, "m02", "2026-08-21")

    def test_delivery_closure_ignores_unknown_identifiers(self) -> None:
        self.assertEqual(delivery_closure({}, {"UNKNOWN"}), {"UNKNOWN"})

    def test_preflight_and_transition_report_each_atomic_start_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fixture(root)
            self.assertEqual(preflight_start(root, "m99"), ["Неизвестный milestone m99"])
            self.assertEqual(start_milestone(root, "m99"), ["Неизвестный milestone m99"])

            milestones = root / "milestones.md"
            original = milestones.read_text(encoding="utf-8")
            milestones.write_text(
                original.replace("work_state: `completed`", "work_state: `in-progress`").replace(
                    "work_state: `planned`", "work_state: `in-progress`"
                ),
                encoding="utf-8",
            )
            blockers = preflight_start(root, "m02")
            self.assertTrue(any("только из planned" in value for value in blockers))
            self.assertTrue(any("ещё не completed" in value for value in blockers))

            milestones.write_text(original, encoding="utf-8")
            (root / "operations/quality_registry.json").write_text(
                json.dumps({"evidence_catalog": {}, "profiles": {}}), encoding="utf-8"
            )
            self.assertTrue(
                any("quality profile" in value for value in preflight_start(root, "m02"))
            )

            with self.assertRaisesRegex(ValueError, "front matter"):
                _transition("## m02 — Feature\n- work_state: `planned`\n", "m02", "2026-08-21")
            with self.assertRaisesRegex(ValueError, "updated"):
                _transition(
                    "---\nid: milestones\n---\n\n## m02 — Feature\n- work_state: `planned`\n",
                    "m02",
                    "2026-08-21",
                )

            self._fixture_default_branch_block(root)

    def _fixture_default_branch_block(self, root: Path) -> None:
        self._fixture_reset_registry(root)
        branch = CommandResult(("git",), 0, "main\n", "")
        with patch("operations.scripts.milestones.start.run_command", return_value=branch):
            self.assertEqual(
                start_milestone(root, "m02", dry_run=False),
                ["Старт milestone запрещён на default branch"],
            )

    def _fixture_reset_registry(self, root: Path) -> None:
        (root / "operations/quality_registry.json").write_text(
            json.dumps(
                {
                    "evidence_catalog": {"e": {"class": "hard", "source": "future"}},
                    "profiles": {
                        "m02": {
                            "milestones": ["m02"],
                            "paths": ["src/**"],
                            "scope_coverage": "task_test",
                            "required_evidence": ["e"],
                        }
                    },
                }
            ),
            encoding="utf-8",
        )

    def test_cli_reports_dry_run_apply_and_blockers(self) -> None:
        root = Path("/project")
        with (
            patch.object(milestone_start, "require_supported_python"),
            patch.object(milestone_start, "find_project_root", return_value=root),
            patch.object(milestone_start, "start_milestone", return_value=[]),
            patch.object(sys, "argv", ["start", "--milestone", "m02", "--dry-run"]),
        ):
            self.assertEqual(milestone_start.main(), 0)
        with (
            patch.object(milestone_start, "require_supported_python"),
            patch.object(milestone_start, "find_project_root", return_value=root),
            patch.object(milestone_start, "start_milestone", return_value=[]),
            patch.object(sys, "argv", ["start", "--milestone", "m02", "--apply"]),
        ):
            self.assertEqual(milestone_start.main(), 0)
        with (
            patch.object(milestone_start, "require_supported_python"),
            patch.object(milestone_start, "find_project_root", return_value=root),
            patch.object(
                milestone_start,
                "start_milestone",
                return_value=["first blocker", "second blocker"],
            ),
            patch.object(sys, "argv", ["start", "--milestone", "m02"]),
        ):
            self.assertEqual(milestone_start.main(), 1)
