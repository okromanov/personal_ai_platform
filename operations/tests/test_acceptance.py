from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from operations.scripts.common.status_types import MilestoneItem
from operations.scripts.evidence.record import _evidence_targets
from operations.scripts.quality.registry import (
    evaluate_milestone_quality,
    validate_quality_registry,
)
from operations.scripts.status.generate_project_status import ProgressSnapshot


def _minimal_snapshot(milestone_id: str, *, tracked_targets: list[str]) -> ProgressSnapshot:
    milestone: MilestoneItem = {
        "id": milestone_id,
        "title": "",
        "work_state": "in-progress",
        "scope": [],
        "result": "",
    }
    return {
        "overall": "healthy",
        "milestones": {"count": 1, "items": [milestone], "current": milestone, "states": {}},
        "current": milestone,
        "next_milestone": None,
        "tasks": {"count": 0, "states": {}, "tasks": []},
        "tests": {"count": 0, "items": [], "states": {}},
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
        "acceptance": {
            "state": "not-ready",
            "technical_ready": False,
            "accepted": False,
            "pending_gates": [],
            "owner_action": "none",
            "tasks_total": 0,
            "tasks_verified": 0,
            "tests_total": 0,
            "tests_passed": 0,
            "tests": [],
            "quality": {
                "profiles": [],
                "evidence": [],
                "blockers": [],
                "warnings": [],
                "ready": True,
            },
            "coverage": {
                "scope_total": 0,
                "scope_covered": 0,
                "scope": [],
                "covered": [],
                "tracked_kind": "foundation_paths",
                "tracked_total": len(tracked_targets),
                "tracked_covered": 0,
                "tracked_targets": tracked_targets,
                "blockers": [],
                "modes": [],
            },
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
        },
        "deviations": [],
        "next_action": {
            "actor": "владелец",
            "instruction": "",
            "commands": [],
            "requires_fresh_session": False,
        },
        "git": {},
    }


class AcceptanceTests(unittest.TestCase):
    def _checks(self, ok: bool = True) -> dict[str, object]:
        return {
            "ok": ok,
            "checks": [{"name": "project", "ok": ok, "errors": [], "warnings": []}],
        }

    def _registry(self) -> dict[str, Any]:
        return {
            "version": 2,
            "evidence_catalog": {
                "project_checks": {"class": "hard", "source": "checker"},
                "unit_tests": {"class": "hard", "source": "unit_tests"},
            },
            "profiles": {
                "foundation": {
                    "milestones": ["m01"],
                    "paths": ["*.md"],
                    "scope_coverage": "global_evidence",
                    "scope_evidence": ["project_checks"],
                    "required_evidence": ["project_checks", "unit_tests"],
                }
            },
        }

    def test_foundation_profile_passes_only_with_required_evidence_and_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "operations").mkdir()
            (root / "operations/quality_registry.json").write_text(
                json.dumps(self._registry()), encoding="utf-8"
            )
            context = {
                "git_sha": "a" * 40,
                "timestamp": "2026-08-13T10:00:00+03:00",
                "environment": {"os": "Windows", "python": "3.12"},
            }
            m01 = evaluate_milestone_quality(
                root,
                "m01",
                check_summary=self._checks(),
                unit_summary={"ok": True},
                context=context,
            )
            self.assertTrue(m01["ready"], m01)
            self.assertEqual({row["git_sha"] for row in m01["evidence"]}, {"a" * 40})
            self.assertTrue(all(row["environment"] for row in m01["evidence"]))

            m02 = evaluate_milestone_quality(
                root,
                "m02",
                check_summary=self._checks(),
                unit_summary={"ok": True},
                context=context,
            )
            self.assertFalse(m02["ready"])
            self.assertIn("quality profile missing for m02", "\n".join(m02["blockers"]))
            self.assertEqual(validate_quality_registry(root, {"m01", "m02"}), [])

    def test_foundation_evidence_targets_machine_path_scope_when_product_scope_is_empty(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "operations").mkdir()
            registry = self._registry()
            registry["profiles"]["foundation"]["paths"] = ["*.md", "operations/**"]
            (root / "operations/quality_registry.json").write_text(
                json.dumps(registry), encoding="utf-8"
            )
            snapshot = _minimal_snapshot("m01", tracked_targets=["path:*.md", "path:operations/**"])
            targets = _evidence_targets(root, snapshot)
            self.assertEqual(targets["project_checks"], ["path:*.md", "path:operations/**"])
            self.assertTrue(
                all(
                    targets[evidence_id]
                    for evidence_id in registry["profiles"]["foundation"]["required_evidence"]
                )
            )

    def test_invalid_global_coverage_profile_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "operations").mkdir()
            registry = self._registry()
            registry["profiles"]["foundation"]["scope_evidence"] = []
            (root / "operations/quality_registry.json").write_text(
                json.dumps(registry), encoding="utf-8"
            )
            errors = validate_quality_registry(root, {"m01"})
            self.assertTrue(any("scope_evidence" in item for item in errors), errors)


if __name__ == "__main__":
    unittest.main()
