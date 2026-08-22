from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from operations.scripts.acceptance.apply import (
    _replace_front_matter_state,
    _replace_front_matter_updated,
    _replace_milestone_work_state,
    apply_acceptance,
    canonical_v1_scope_ids,
    validate_confirmation,
    validate_evidence_bundle,
    validate_semantic_review,
)
from operations.scripts.status.generate_project_status import (
    collect_milestones,
    evaluate_acceptance,
)


def _server_source(sha: str = "a" * 40) -> dict[str, object]:
    return {
        "repository": "example/repo",
        "workflow": "Project check",
        "run_id": "1",
        "run_url": "https://github.com/example/repo/actions/runs/1",
        "event_sha": sha,
        "artifact_id": "2",
        "artifact_digest": "sha256:" + "3" * 64,
    }


class AcceptanceTransitionTests(unittest.TestCase):
    def test_m01_reaches_semantic_review_without_repository_maintenance_tasks(self) -> None:
        root = Path(__file__).resolve().parents[2]
        project_tasks = {"tasks": []}
        passing_tests = {
            "items": [
                {
                    "id": "TEST_0001",
                    "execution": "automated",
                    "automated_evidence": "project_checks",
                    "traces_to": [],
                    "verifies": [],
                    "accepts": ["m01"],
                }
            ]
        }
        passing_evidence = {
            evidence_id: {"result": "passed", "class": "hard", "source": "test"}
            for evidence_id in ["project_checks", "unit_tests", "quality_suite"]
        }
        with (
            patch(
                "operations.scripts.status.generate_project_status._change_scope",
                return_value={
                    "mode": "tracked_tree",
                    "base_sha": "repository-start",
                    "paths": [],
                    "error": None,
                },
            ),
            patch(
                "operations.scripts.status.generate_project_status.evidence_results",
                return_value=passing_evidence,
            ),
            patch(
                "operations.scripts.quality.registry.evidence_results",
                return_value=passing_evidence,
            ),
        ):
            result = evaluate_acceptance(
                root,
                milestones={
                    "items": [
                        {"id": "m01", "title": "Основа", "work_state": "in-progress", "scope": []}
                    ],
                    "current": {
                        "id": "m01",
                        "title": "Основа",
                        "work_state": "in-progress",
                        "scope": [],
                    },
                },
                tasks=project_tasks,
                tests=passing_tests,
                check_summary={"ok": True, "checks": []},
                unit_summary={"ok": True},
                git={"commit": "a" * 40},
            )

        self.assertEqual(result["state"], "ready-for-semantic-review")
        self.assertTrue(result["technical_ready"])
        self.assertEqual(result["pending_gates"], ["semantic_review"])
        self.assertEqual(result["blockers"], [])

        with tempfile.TemporaryDirectory() as tmp:
            transition_root = Path(tmp)
            shutil.copy2(root / "milestones.md", transition_root / "milestones.md")
            (transition_root / "work/acceptance").mkdir(parents=True)
            shutil.copytree(root / "adr", transition_root / "adr")
            changed = apply_acceptance(
                transition_root,
                "m01",
                source_sha="a" * 40,
                evidence_ref="evidence.json",
                semantic_review_ref="semantic.json",
                owner_confirmation="ПРИНИМАЮ m01",
                accepted_at="2026-08-14T12:00:00+02:00",
                server_source=_server_source(),
                evidence_data={
                    "acceptance_state": "ready-for-semantic-review",
                    "git_sha": "a" * 40,
                },
                semantic_review_data={
                    "milestone": "m01",
                    "result": "pass",
                    "reviewed_sha": "a" * 40,
                },
            )
            after = collect_milestones(transition_root)

        self.assertIn("work/acceptance/m01.json", changed)
        self.assertEqual(after["items"][0]["work_state"], "completed")
        self.assertEqual(after["current"]["id"], "m02")

    def test_non_baseline_milestone_also_requires_semantic_review_before_acceptance(self) -> None:
        """Периодическая смысловая проверка обязательна для каждого этапа, не только для m01:

        техническая готовность m02 не должна давать ready-for-acceptance в обход
        отдельной смысловой проверки — иначе дрейф вроде найденного в m01
        (забытые ссылки, расходящаяся статистика) остаётся незамеченным на
        следующих этапах.
        """
        root = Path(__file__).resolve().parents[2]
        project_tasks = {"tasks": []}
        passing_tests = {
            "items": [
                {
                    "id": "TEST_9001",
                    "execution": "automated",
                    "automated_evidence": "project_checks",
                    "traces_to": [],
                    "verifies": [],
                    "accepts": ["m02"],
                }
            ]
        }
        passing_evidence = {
            evidence_id: {"result": "passed", "class": "hard", "source": "test"}
            for evidence_id in ["project_checks", "unit_tests"]
        }
        synthetic_registry = {
            "version": 1,
            "evidence_catalog": {
                "project_checks": {"class": "hard", "source": "checker"},
                "unit_tests": {"class": "hard", "source": "unit_tests"},
            },
            "profiles": {
                "m02_profile": {
                    "milestones": ["m02"],
                    "paths": ["*.md"],
                    "scope_coverage": "global_evidence",
                    "scope_evidence": ["project_checks"],
                    "required_evidence": ["project_checks", "unit_tests"],
                }
            },
        }
        with (
            patch(
                "operations.scripts.status.generate_project_status._change_scope",
                return_value={
                    "mode": "tracked_tree",
                    "base_sha": "repository-start",
                    "paths": [],
                    "error": None,
                },
            ),
            patch(
                "operations.scripts.status.generate_project_status.evidence_results",
                return_value=passing_evidence,
            ),
            patch(
                "operations.scripts.quality.registry.evidence_results",
                return_value=passing_evidence,
            ),
            patch(
                "operations.scripts.status.generate_project_status.load_quality_registry",
                return_value=synthetic_registry,
            ),
            patch(
                "operations.scripts.quality.registry.load_quality_registry",
                return_value=synthetic_registry,
            ),
        ):
            result = evaluate_acceptance(
                root,
                milestones={
                    "items": [
                        {
                            "id": "m02",
                            "title": "Второй этап",
                            "work_state": "in-progress",
                            "scope": [],
                        }
                    ],
                    "current": {
                        "id": "m02",
                        "title": "Второй этап",
                        "work_state": "in-progress",
                        "scope": [],
                    },
                },
                tasks=project_tasks,
                tests=passing_tests,
                check_summary={"ok": True, "checks": []},
                unit_summary={"ok": True},
                git={"commit": "a" * 40},
            )

        self.assertTrue(result["technical_ready"])
        self.assertEqual(result["state"], "ready-for-semantic-review")
        self.assertEqual(result["pending_gates"], ["semantic_review"])
        self.assertNotEqual(result["state"], "ready-for-acceptance")

    def test_semantic_review_schema_applies_to_non_m01_without_v1_scope_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = {
                "type": "semantic_review",
                "milestone": "m02",
                "result": "pass",
                "reviewed_sha": "a" * 40,
                "timestamp": "2026-08-17T09:00:00+03:00",
                "reviewer": "owner",
                "review_context": "fresh-session",
                "lifecycle_tested": True,
                "reviewed_artifacts": [
                    "AGENTS.md",
                    "project_rules.md",
                    "operations/change_process.md",
                    "milestones.md",
                    "project_status.md",
                    "tasks.md",
                    "specifications/",
                    "adr/",
                    "operations/",
                    "work/",
                    "generated/",
                    ".github/workflows/",
                ],
                "scores": {
                    "clarity": 8,
                    "consistency": 8,
                    "hierarchy": 8,
                    "automation": 8,
                    "owner_usability": 8,
                    "agent_readiness": 8,
                    "language": 8,
                    "minimality": 8,
                    "overall": 8,
                },
                "findings": [],
            }
            path = root / "semantic.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            with patch("operations.scripts.acceptance.apply._git_head", return_value="a" * 40):
                validate_semantic_review(root, path, "m02")

            without_lifecycle = {**data, "lifecycle_tested": False}
            path.write_text(json.dumps(without_lifecycle), encoding="utf-8")
            with patch("operations.scripts.acceptance.apply._git_head", return_value="a" * 40):
                with self.assertRaisesRegex(ValueError, "lifecycle_tested"):
                    validate_semantic_review(root, path, "m02")

    def test_owner_confirmation_must_match_exact_milestone(self) -> None:
        validate_confirmation("m01", "ПРИНИМАЮ m01")
        with self.assertRaises(ValueError):
            validate_confirmation("m01", "принимаю m01")
        with self.assertRaises(ValueError):
            validate_confirmation("m01", "ПРИНИМАЮ m02")

    def test_state_transitions_change_only_typed_fields(self) -> None:
        doc = "---\nid: x\ntype: adr\ndecision_state: proposed\nversion: 1.0\n---\n\n# X\nbody\n"
        updated = _replace_front_matter_state(
            doc,
            field="decision_state",
            allowed_from={"proposed"},
            target="accepted",
        )
        self.assertIn("decision_state: accepted", updated)
        self.assertIn("# X\nbody", updated)

        milestones = (
            "## m01 — Foundation\n\n- work_state: `in-progress`\n- состав: `SYS_001`\n\n"
            "## m02 — Next\n\n- work_state: `planned`\n"
        )
        changed = _replace_milestone_work_state(milestones, "m01")
        self.assertIn("- work_state: `completed`", changed)
        self.assertIn("## m02 — Next\n\n- work_state: `planned`", changed)

    def test_m01_acceptance_creates_one_record_without_bulk_document_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "work/tasks").mkdir(parents=True)
            (root / "work/acceptance").mkdir(parents=True)
            (root / "adr").mkdir()
            (root / "milestones.md").write_text(
                "---\nid: milestones\ntype: roadmap\ndocument_state: current\nversion: 1.0\n"
                "updated: 2026-08-12\n---\n\n## m01 — Foundation\n\n"
                "- work_state: `in-progress`\n- состав: —\n",
                encoding="utf-8",
            )
            task_path = root / "work/tasks/task_0001.md"
            task_path.write_text(
                "---\nid: TASK_0001\ntype: task\nwork_state: completed\nversion: 1.0\n"
                "traces_to:\n  - m01\n---\n# TASK_0001\n",
                encoding="utf-8",
            )
            adr_path = root / "adr/adr_001_sample.md"
            adr_path.write_text(
                "---\nid: ADR_001\ntype: adr\ndecision_state: proposed\nversion: 1.0\nupdated: 2026-08-12\n"
                "traces_to:\n  - m01\n---\n# ADR_001\nbody\n",
                encoding="utf-8",
            )
            unrelated_adr = root / "adr/adr_002_unrelated.md"
            unrelated_adr.write_text(
                "---\nid: ADR_002\ntype: adr\ndecision_state: proposed\nversion: 1.0\nupdated: 2026-08-12\n"
                "traces_to:\n  - SYS_001\n---\n# ADR_002\nbody\n",
                encoding="utf-8",
            )
            ordinary_path = root / "governance.md"
            ordinary = (
                "---\nid: g\ntype: governance\ndocument_state: current\nversion: 1.0\n---\n# G\n"
            )
            ordinary_path.write_text(ordinary, encoding="utf-8")

            changed = apply_acceptance(
                root,
                "m01",
                source_sha="a" * 40,
                evidence_ref="runtime/evidence/latest.json",
                semantic_review_ref="runtime/evidence/m01_semantic_review.json",
                owner_confirmation="ПРИНИМАЮ m01",
                accepted_at="2026-08-13T10:00:00+02:00",
                evidence_data={
                    "acceptance_state": "ready-for-semantic-review",
                    "git_sha": "a" * 40,
                    "timestamp": "2026-08-13T09:00:00+02:00",
                    "coverage_base": {"mode": "tracked_tree", "git_sha": "repository-start"},
                    "coverage": {"tracked_total": 7, "tracked_covered": 7},
                },
                semantic_review_data={
                    "type": "semantic_review",
                    "milestone": "m01",
                    "result": "pass",
                    "reviewed_sha": "a" * 40,
                },
                evidence_digest="1" * 64,
                semantic_review_digest="2" * 64,
                server_source=_server_source(),
            )

            self.assertEqual(
                set(changed),
                {"milestones.md", "adr/adr_001_sample.md", "work/acceptance/m01.json"},
            )
            self.assertEqual(ordinary_path.read_text(encoding="utf-8"), ordinary)
            self.assertIn(
                "work_state: `completed`", (root / "milestones.md").read_text(encoding="utf-8")
            )
            self.assertIn("work_state: completed", task_path.read_text(encoding="utf-8"))
            self.assertIn("decision_state: accepted", adr_path.read_text(encoding="utf-8"))
            self.assertIn("decision_state: proposed", unrelated_adr.read_text(encoding="utf-8"))
            record = json.loads((root / "work/acceptance/m01.json").read_text(encoding="utf-8"))
            self.assertEqual(record["decision"], "accepted")
            self.assertEqual(record["source_git_sha"], "a" * 40)
            self.assertEqual(record["schema_version"], 2)
            self.assertEqual(record["technical_evidence"]["sha256"], "1" * 64)
            self.assertEqual(record["semantic_review"]["sha256"], "2" * 64)
            self.assertNotIn("runtime/evidence", json.dumps(record))

    def test_acceptance_rejects_unfinished_task_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "work/tasks").mkdir(parents=True)
            (root / "work/acceptance").mkdir(parents=True)
            original = "## m01 — Foundation\n\n- work_state: `in-progress`\n"
            (root / "milestones.md").write_text(original, encoding="utf-8")
            (root / "work/tasks/task_0001.md").write_text(
                "---\nid: TASK_0001\ntype: task\nwork_state: in-progress\nversion: 1.0\n"
                "traces_to:\n  - m01\n---\n# TASK_0001\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "не завершены TASK"):
                apply_acceptance(
                    root,
                    "m01",
                    source_sha="a" * 40,
                    evidence_ref="evidence.json",
                    semantic_review_ref="semantic.json",
                    owner_confirmation="ПРИНИМАЮ m01",
                    accepted_at="2026-08-13T10:00:00+02:00",
                    server_source=_server_source(),
                )
            self.assertEqual((root / "milestones.md").read_text(encoding="utf-8"), original)

    def test_direct_acceptance_requires_owner_and_sha_bound_dual_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "work/tasks").mkdir(parents=True)
            (root / "work/acceptance").mkdir(parents=True)
            (root / "milestones.md").write_text(
                "---\nid: milestones\ntype: roadmap\ndocument_state: current\nversion: 1.0\n"
                "updated: 2026-08-20\n---\n\n## m02 — Feature\n\n"
                "- work_state: `in-progress`\n- состав: `SYS_001`\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "техническое evidence"):
                apply_acceptance(
                    root,
                    "m02",
                    owner_confirmation="ПРИНИМАЮ m02",
                    source_sha="a" * 40,
                    evidence_ref="server:evidence",
                    semantic_review_ref="server:semantic",
                    accepted_at="2026-08-21T10:00:00Z",
                    server_source=_server_source(),
                )
            evidence: dict[str, object] = {
                "acceptance_state": "ready-for-semantic-review",
                "git_sha": "a" * 40,
            }
            with self.assertRaisesRegex(ValueError, "semantic review"):
                apply_acceptance(
                    root,
                    "m02",
                    owner_confirmation="ПРИНИМАЮ m02",
                    evidence_data=evidence,
                    source_sha="a" * 40,
                    evidence_ref="server:evidence",
                    semantic_review_ref="server:semantic",
                    accepted_at="2026-08-21T10:00:00Z",
                    server_source=_server_source(),
                )
            semantic: dict[str, object] = {
                "milestone": "m02",
                "result": "pass",
                "reviewed_sha": "a" * 40,
            }
            with self.assertRaisesRegex(ValueError, "точная строка"):
                apply_acceptance(
                    root,
                    "m02",
                    owner_confirmation="принимаю m02",
                    evidence_data=evidence,
                    semantic_review_data=semantic,
                    source_sha="a" * 40,
                    evidence_ref="server:evidence",
                    semantic_review_ref="server:semantic",
                    accepted_at="2026-08-21T10:00:00Z",
                    server_source=_server_source(),
                )

            with self.assertRaisesRegex(ValueError, "front matter"):
                _replace_front_matter_updated("body", "2026-08-21")

    def test_evidence_bundle_requires_ready_exact_sha_and_full_coverage(self) -> None:
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch("operations.scripts.acceptance.apply._require_clean_worktree"),
        ):
            root = Path(tmp)
            path = root / "evidence.json"
            bundle = {
                "schema_version": 2,
                "milestone": "m01",
                "acceptance_state": "ready-for-semantic-review",
                "blockers": [],
                "pending_gates": ["semantic_review"],
                "git_sha": "a" * 40,
                "timestamp": "2026-08-13T10:00:00+03:00",
                "environment": {"os": "Windows"},
                "server_source": _server_source(),
                "evidence": [
                    {
                        "id": "project_checks",
                        "result": "passed",
                        "source": "checker",
                        "git_sha": "a" * 40,
                        "timestamp": "2026-08-13T10:00:00+03:00",
                        "environment": {"os": "Windows"},
                        "validation_errors": [],
                    }
                ],
                "coverage_base": {"mode": "tracked_tree", "git_sha": "repository-start"},
                "changed_paths": ["allowed.md"],
                "uncovered_paths": [],
                "coverage": {"scope_total": 10, "scope_covered": 10},
            }
            change_scope = {
                "mode": "tracked_tree",
                "base_sha": "repository-start",
                "paths": ["allowed.md"],
                "error": None,
            }
            path.write_text(json.dumps(bundle), encoding="utf-8")
            with (
                patch("operations.scripts.acceptance.apply._git_head", return_value="a" * 40),
                patch(
                    "operations.scripts.acceptance.apply._change_scope", return_value=change_scope
                ),
            ):
                validate_evidence_bundle(root, path, "m01")

            evidence_rows = bundle["evidence"]
            self.assertIsInstance(evidence_rows, list)
            evidence_row = evidence_rows[0] if isinstance(evidence_rows, list) else {}
            self.assertIsInstance(evidence_row, dict)
            original_row = dict(evidence_row) if isinstance(evidence_row, dict) else {}
            if isinstance(evidence_row, dict):
                evidence_row.update(
                    {
                        "source": "record:runtime/fake.json",
                        "type": "quality_suite",
                        "server_source": _server_source(),
                    }
                )
            path.write_text(json.dumps(bundle), encoding="utf-8")
            with (
                patch("operations.scripts.acceptance.apply._git_head", return_value="a" * 40),
                patch(
                    "operations.scripts.acceptance.apply._change_scope", return_value=change_scope
                ),
            ):
                with self.assertRaisesRegex(ValueError, "строгую record schema"):
                    validate_evidence_bundle(root, path, "m01")
            if isinstance(evidence_rows, list):
                evidence_rows[0] = original_row

            bundle["pending_gates"] = []
            path.write_text(json.dumps(bundle), encoding="utf-8")
            with (
                patch("operations.scripts.acceptance.apply._git_head", return_value="a" * 40),
                patch(
                    "operations.scripts.acceptance.apply._change_scope", return_value=change_scope
                ),
            ):
                with self.assertRaisesRegex(ValueError, "pending gate"):
                    validate_evidence_bundle(root, path, "m01")
            bundle["pending_gates"] = ["semantic_review"]

            bundle["git_sha"] = "b" * 40
            path.write_text(json.dumps(bundle), encoding="utf-8")
            with (
                patch("operations.scripts.acceptance.apply._git_head", return_value="a" * 40),
                patch(
                    "operations.scripts.acceptance.apply._change_scope", return_value=change_scope
                ),
            ):
                with self.assertRaisesRegex(ValueError, "SHA mismatch"):
                    validate_evidence_bundle(root, path, "m01")

            bundle["git_sha"] = "a" * 40
            bundle["coverage"] = {"scope_total": 10, "scope_covered": 9}
            path.write_text(json.dumps(bundle), encoding="utf-8")
            with (
                patch("operations.scripts.acceptance.apply._git_head", return_value="a" * 40),
                patch(
                    "operations.scripts.acceptance.apply._change_scope", return_value=change_scope
                ),
            ):
                with self.assertRaisesRegex(ValueError, "scope coverage"):
                    validate_evidence_bundle(root, path, "m01")

            bundle["coverage"] = {
                "scope_total": 0,
                "scope_covered": 0,
                "tracked_total": 7,
                "tracked_covered": 6,
            }
            path.write_text(json.dumps(bundle), encoding="utf-8")
            with (
                patch("operations.scripts.acceptance.apply._git_head", return_value="a" * 40),
                patch(
                    "operations.scripts.acceptance.apply._change_scope", return_value=change_scope
                ),
            ):
                with self.assertRaisesRegex(ValueError, "проверяемых областей"):
                    validate_evidence_bundle(root, path, "m01")

    def test_m01_semantic_review_requires_exact_sha_and_full_artifact_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_root = Path(__file__).resolve().parents[2]
            shutil.copy2(source_root / "milestones.md", root / "milestones.md")
            (root / "specifications").mkdir(parents=True, exist_ok=True)
            shutil.copy2(
                source_root / "specifications" / "business_requirements.md",
                root / "specifications" / "business_requirements.md",
            )
            path = root / "semantic.json"
            data = {
                "type": "semantic_review",
                "milestone": "m01",
                "result": "pass",
                "reviewed_sha": "a" * 40,
                "timestamp": "2026-08-13T13:00:00+03:00",
                "reviewer": "owner",
                "review_context": "fresh-session",
                "lifecycle_tested": True,
                "v1_scope_owner_decision": "ПОДТВЕРЖДАЮ СОСТАВ V1",
                "v1_scope_ids": canonical_v1_scope_ids(source_root),
                "strategic_answers": {
                    "v1_scope": "Текущий core-периметр достаточен",
                    "m02_interfaces": "Telegram достаточно",
                    "portability_boundary": "Полный локальный контур вне V1",
                    "scheduled_tasks_order": "m05 приемлем",
                    "model_outage_strategy": "Явный отказ сейчас, резерв к m06",
                },
                "reviewed_artifacts": [
                    "AGENTS.md",
                    "project_rules.md",
                    "operations/change_process.md",
                    "milestones.md",
                    "project_status.md",
                    "tasks.md",
                    "specifications/",
                    "adr/",
                    "operations/",
                    "work/",
                    "generated/",
                    ".github/workflows/",
                ],
                "scores": {
                    "clarity": 8,
                    "consistency": 8,
                    "hierarchy": 8,
                    "automation": 8,
                    "owner_usability": 8,
                    "agent_readiness": 8,
                    "language": 8,
                    "minimality": 8,
                    "overall": 8,
                },
                "findings": [],
            }
            path.write_text(json.dumps(data), encoding="utf-8")
            with patch("operations.scripts.acceptance.apply._git_head", return_value="a" * 40):
                validate_semantic_review(root, path, "m01")

            data["reviewed_sha"] = "b" * 40
            path.write_text(json.dumps(data), encoding="utf-8")
            with patch("operations.scripts.acceptance.apply._git_head", return_value="a" * 40):
                with self.assertRaisesRegex(ValueError, "SHA mismatch"):
                    validate_semantic_review(root, path, "m01")

            data["reviewed_sha"] = "a" * 40
            data["reviewed_artifacts"].remove("specifications/")
            path.write_text(json.dumps(data), encoding="utf-8")
            with patch("operations.scripts.acceptance.apply._git_head", return_value="a" * 40):
                with self.assertRaisesRegex(ValueError, "обязательные artifacts"):
                    validate_semantic_review(root, path, "m01")

            data["reviewed_artifacts"].append("specifications/")
            data["v1_scope_ids"] = data["v1_scope_ids"][:-1]
            path.write_text(json.dumps(data), encoding="utf-8")
            with patch("operations.scripts.acceptance.apply._git_head", return_value="a" * 40):
                with self.assertRaisesRegex(ValueError, "неактуальный состав V1"):
                    validate_semantic_review(root, path, "m01")

            data["v1_scope_ids"] = canonical_v1_scope_ids(source_root)
            data["strategic_answers"] = {
                "v1_scope": "Текущий core-периметр достаточен",
                "portability_boundary": "Полный локальный контур вне V1",
                "scheduled_tasks_order": "m05 приемлем",
                "model_outage_strategy": "Явный отказ сейчас, резерв к m06",
            }
            path.write_text(json.dumps(data), encoding="utf-8")
            with patch("operations.scripts.acceptance.apply._git_head", return_value="a" * 40):
                with self.assertRaisesRegex(ValueError, "пять стратегических"):
                    validate_semantic_review(root, path, "m01")

    def test_m01_semantic_pass_rejects_unresolved_serious_findings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_root = Path(__file__).resolve().parents[2]
            shutil.copy2(source_root / "milestones.md", root / "milestones.md")
            (root / "specifications").mkdir(parents=True, exist_ok=True)
            shutil.copy2(
                source_root / "specifications" / "business_requirements.md",
                root / "specifications" / "business_requirements.md",
            )
            (root / "project_status.md").write_text("# Состояние\n", encoding="utf-8")
            path = root / "semantic.json"
            data = {
                "type": "semantic_review",
                "milestone": "m01",
                "result": "pass",
                "reviewed_sha": "a" * 40,
                "timestamp": "2026-08-14T12:00:00+02:00",
                "reviewer": "independent-agent",
                "review_context": "fresh-session",
                "lifecycle_tested": True,
                "v1_scope_owner_decision": "ПОДТВЕРЖДАЮ СОСТАВ V1",
                "v1_scope_ids": canonical_v1_scope_ids(source_root),
                "strategic_answers": {
                    "v1_scope": "Текущий core-периметр достаточен",
                    "m02_interfaces": "Telegram достаточно",
                    "portability_boundary": "Полный локальный контур вне V1",
                    "scheduled_tasks_order": "m05 приемлем",
                    "model_outage_strategy": "Явный отказ сейчас, резерв к m06",
                },
                "reviewed_artifacts": [
                    "AGENTS.md",
                    "project_rules.md",
                    "operations/change_process.md",
                    "milestones.md",
                    "project_status.md",
                    "tasks.md",
                    "specifications/",
                    "adr/",
                    "operations/",
                    "work/",
                    "generated/",
                    ".github/workflows/",
                ],
                "scores": {
                    "clarity": 8,
                    "consistency": 8,
                    "hierarchy": 8,
                    "automation": 8,
                    "owner_usability": 8,
                    "agent_readiness": 8,
                    "language": 8,
                    "minimality": 8,
                    "overall": 8,
                },
                "findings": [
                    {
                        "severity": "high",
                        "state": "unresolved",
                        "evidence": "project_status.md показывает невозможное действие",
                        "locations": [{"path": "project_status.md", "anchor": "состояние"}],
                        "remediation": "исправить маршрут владельца",
                    }
                ],
            }
            path.write_text(json.dumps(data), encoding="utf-8")
            with patch("operations.scripts.acceptance.apply._git_head", return_value="a" * 40):
                with self.assertRaisesRegex(ValueError, "critical/high"):
                    validate_semantic_review(root, path, "m01")

            del data["findings"][0]["locations"]
            path.write_text(json.dumps(data), encoding="utf-8")
            with patch("operations.scripts.acceptance.apply._git_head", return_value="a" * 40):
                with self.assertRaisesRegex(ValueError, "не содержит locations"):
                    validate_semantic_review(root, path, "m01")


if __name__ == "__main__":
    unittest.main()
