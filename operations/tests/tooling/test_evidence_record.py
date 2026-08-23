from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import cast
from unittest.mock import patch

from operations.scripts.common.status_types import MilestoneItem
from operations.scripts.evidence.record import (
    _evidence_targets,
    build_evidence_bundle,
    write_evidence_bundle,
)
from operations.scripts.status.generate_project_status import (
    AcceptanceResult,
    CoverageResult,
    EffectiveTestItem,
    ProgressSnapshot,
)


def _milestone(milestone_id: str) -> MilestoneItem:
    return {"id": milestone_id, "title": "", "work_state": "in-progress", "scope": []}


def _coverage(*, scope: list[str], tracked_targets: list[str]) -> CoverageResult:
    return {
        "scope_total": len(scope),
        "scope_covered": 0,
        "scope": scope,
        "covered": [],
        "tracked_kind": "foundation_paths",
        "tracked_total": len(tracked_targets),
        "tracked_covered": 0,
        "tracked_targets": tracked_targets,
        "blockers": [],
        "modes": [],
    }


def _test_item(
    test_id: str,
    *,
    automated_evidence: str,
    verifies: list[str],
    accepts: list[str],
    traces_to: list[str] | None = None,
    effective_result: str = "passed",
) -> EffectiveTestItem:
    return {
        "id": test_id,
        "spec_state": "current",
        "execution": "automated",
        "automated_evidence": automated_evidence,
        "manual_evidence": "",
        "traces_to": traces_to or [],
        "verifies": verifies,
        "accepts": accepts,
        "title": test_id,
        "path": f"work/tests/{test_id.lower()}.md",
        "effective_result": effective_result,
    }


def _acceptance(*, coverage: CoverageResult, tests: list[EffectiveTestItem]) -> AcceptanceResult:
    return {
        "state": "ready-for-semantic-review",
        "technical_ready": True,
        "accepted": False,
        "pending_gates": ["semantic_review"],
        "owner_action": "none",
        "tasks_total": 0,
        "tasks_verified": 0,
        "tests_total": len(tests),
        "tests_passed": len(tests),
        "tests": tests,
        "quality": {"profiles": [], "evidence": [], "blockers": [], "warnings": [], "ready": True},
        "coverage": coverage,
        "evidence_results": {},
        "evidence_context": {
            "git_sha": "a" * 40,
            "timestamp": "2026-08-20T12:00:00Z",
            "environment": {"os": "linux"},
        },
        "changed_paths": [],
        "coverage_base": {"mode": "git", "git_sha": "b" * 40},
        "uncovered_paths": [],
        "impacted_profiles": [],
        "documents_total": 0,
        "documents_current": 0,
        "decisions_proposed": 0,
        "remaining": [],
        "blockers": [],
    }


def _snapshot(milestone_id: str, acceptance: AcceptanceResult) -> ProgressSnapshot:
    milestone = _milestone(milestone_id)
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
        "acceptance": acceptance,
        "deviations": [],
        "next_action": {
            "actor": "владелец",
            "instruction": "",
            "commands": [],
            "requires_fresh_session": False,
        },
        "git": {"commit": "fallback"},
    }


class EvidenceRecordTests(unittest.TestCase):
    def test_targets_merge_tests_profiles_and_fallback_paths(self) -> None:
        test_item = _test_item(
            "TEST_001",
            automated_evidence="e2e",
            # Duplicate SYS_001 on purpose: targets must be de-duplicated.
            verifies=["SYS_001", "SYS_001"],
            accepts=["m02"],
        )
        acceptance = _acceptance(
            coverage=_coverage(scope=["BR_001"], tracked_targets=[]), tests=[test_item]
        )
        snapshot = _snapshot("m02", acceptance)
        registry = {
            "profiles": {
                "m02": {
                    "milestones": ["m02"],
                    "paths": ["src/**"],
                    "scope_coverage": "global_evidence",
                    "scope_evidence": ["project_checks"],
                    "required_evidence": ["project_checks", "unit_tests"],
                }
            }
        }
        with patch(
            "operations.scripts.evidence.record.load_quality_registry", return_value=registry
        ):
            targets = _evidence_targets(Path("."), snapshot)

        self.assertEqual(targets["e2e"], ["SYS_001", "milestone:m02"])
        self.assertEqual(targets["project_checks"], ["BR_001"])
        self.assertEqual(targets["unit_tests"], ["BR_001"])

        # Empty product scope: global-evidence targets fall back to profile paths.
        snapshot["acceptance"]["coverage"] = _coverage(scope=[], tracked_targets=[])
        registry["profiles"]["m02"]["scope_coverage"] = "task_test"
        with patch(
            "operations.scripts.evidence.record.load_quality_registry", return_value=registry
        ):
            fallback = _evidence_targets(Path("."), snapshot)
        self.assertEqual(fallback["project_checks"], ["path:src/**"])

    def test_build_bundle_normalizes_evidence_and_tests(self) -> None:
        test_item = _test_item(
            "TEST_001",
            automated_evidence="project_checks",
            verifies=["SYS_001"],
            accepts=["m02"],
            traces_to=["ARC_001"],
        )
        acceptance = _acceptance(
            coverage=_coverage(scope=["SYS_001"], tracked_targets=[]), tests=[test_item]
        )
        acceptance["quality"] = {
            "profiles": ["m02"],
            "evidence": [{"id": "project_checks", "result": "passed", "class": "hard"}],
            "blockers": [],
            "warnings": [],
            "ready": True,
        }
        acceptance["impacted_profiles"] = ["m02"]
        snapshot = _snapshot("m02", acceptance)
        with (
            patch(
                "operations.scripts.evidence.record.build_progress_snapshot",
                return_value=snapshot,
            ),
            patch(
                "operations.scripts.evidence.record._evidence_targets",
                return_value={"project_checks": ["SYS_001"]},
            ),
        ):
            bundle = build_evidence_bundle(
                Path("."),
                check_summary={},
                test_returncode=0,
                test_output="OK",
                git={"commit": "fallback"},
                server_source={
                    "repository": "owner/repo",
                    "workflow": "Project check",
                    "run_id": "1",
                    "run_url": "https://github.com/owner/repo/actions/runs/1",
                    "event_sha": "a" * 40,
                },
            )

        evidence = cast(list[dict[str, object]], bundle["evidence"])
        tests = cast(list[dict[str, object]], bundle["tests"])
        self.assertEqual(bundle["git_sha"], "a" * 40)
        self.assertEqual(bundle["schema_version"], 2)
        self.assertEqual(evidence[0]["targets"], ["SYS_001"])
        self.assertEqual(tests[0]["test_id"], "TEST_001")

    def test_write_bundle_uses_sha_name_and_atomic_latest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle: dict[str, object] = {"git_sha": "A" * 40, "result": "passed"}
            path = write_evidence_bundle(root, bundle)
            self.assertEqual(path.name, f"evidence_{'a' * 40}.json")
            self.assertEqual(
                json.loads((root / "runtime/evidence/latest.json").read_text("utf-8")), bundle
            )

            unknown = write_evidence_bundle(root, {"git_sha": "invalid"})
            self.assertEqual(unknown.name, "evidence_unknown.json")


if __name__ == "__main__":
    unittest.main()
