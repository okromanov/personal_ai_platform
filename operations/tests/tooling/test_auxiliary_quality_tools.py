from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from operations.scripts.documents.auto_generate_tasks import (
    _extract_components_with_targets,
    _generate_task_document,
    auto_generate_tasks,
)
from operations.scripts.evidence import generate_bundle
from operations.scripts.github import post_pr_comment
from operations.scripts.quality.action_practicality import check_project_status
from operations.scripts.quality.paths_validation import validate_task_paths
from operations.scripts.quality.record_quality_suite import main as record_quality_main
from operations.scripts.quality.test_coverage import validate_test_coverage
from operations.scripts.status.technical_status import generate_technical_status
from operations.scripts.traceability.auto_link import (
    _extract_id_field,
    _update_yaml_field,
    auto_link_requirements,
)


class AutoGenerateTaskTests(unittest.TestCase):
    def test_component_parser_and_document_are_deterministic(self) -> None:
        parsed = _extract_components_with_targets(
            "### ARC_CMP_001 — One\n\n`traces_to`: SYS_002, BR_001\n"
            "### ARC_CMP_002 — Two\n\nNo relation\n",
            "ARC_CMP",
        )
        self.assertEqual(parsed["ARC_CMP_001"], {"SYS_002", "BR_001"})
        self.assertEqual(parsed["ARC_CMP_002"], set())

        text = _generate_task_document(
            7,
            "ARC_CMP_001",
            "m02",
            "TASK_006",
            "work/tasks/task_007_arc_001.md",
        )
        self.assertIn("id: TASK_007", text)
        self.assertIn("  - TASK_006", text)
        self.assertIn("  - work/tasks/task_007_arc_001.md", text)

    def test_generates_only_in_scope_uncovered_components(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "specifications").mkdir()
            (root / "work" / "tasks").mkdir(parents=True)
            (root / "specifications" / "architecture_baseline.md").write_text(
                "### ARC_CMP_001 — One\n\n`traces_to`: SYS_001\n"
                "### ARC_CMP_002 — Two\n\n`traces_to`: SYS_999\n",
                encoding="utf-8",
            )
            (root / "specifications" / "infrastructure_baseline.md").write_text(
                "### INF_CMP_001 — Infra\n\n`implements`: SYS_001\n", encoding="utf-8"
            )
            (root / "work" / "tasks" / "task_004_old.md").write_text(
                "---\nid: TASK_004\ntitle: Existing\n---\n", encoding="utf-8"
            )

            state = {"current": {"id": "m02", "work_state": "in-progress", "scope": ["SYS_001"]}}
            with patch(
                "operations.scripts.documents.auto_generate_tasks.collect_milestones",
                return_value=state,
            ):
                created = auto_generate_tasks(root)
                repeated = auto_generate_tasks(root)

            self.assertEqual(
                created,
                ["work/tasks/task_005_arc_001.md", "work/tasks/task_006_inf_001.md"],
            )
            self.assertEqual(repeated, [])
            second = (root / created[1]).read_text(encoding="utf-8")
            self.assertIn("  - TASK_005", second)

    def test_generation_is_blocked_before_an_active_scoped_stage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch(
                "operations.scripts.documents.auto_generate_tasks.collect_milestones",
                return_value={"current": {"id": "m01", "work_state": "in-progress"}},
            ):
                self.assertEqual(auto_generate_tasks(root), [])
            with patch(
                "operations.scripts.documents.auto_generate_tasks.collect_milestones",
                return_value={"current": {"id": "m02", "work_state": "planned", "scope": []}},
            ):
                self.assertEqual(auto_generate_tasks(root), [])


class TraceabilityAutoLinkTests(unittest.TestCase):
    def test_yaml_helpers_preserve_front_matter(self) -> None:
        source = "---\nid: ARC_001\ntraces_to:\n  - SYS_002\n---\nBody\n"
        self.assertEqual(_extract_id_field(source, "traces_to"), ["SYS_002"])
        updated = _update_yaml_field(source, "traces_to", ["SYS_003", "SYS_001", "SYS_003"])
        self.assertIn("traces_to:\n  - SYS_001\n  - SYS_003\n", updated)
        self.assertEqual(_update_yaml_field(source, "traces_to", []), source)

    def test_auto_link_finds_architecture_implementation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            specs = root / "specifications"
            specs.mkdir()
            (specs / "business_requirements.md").write_text(
                '<a id="br_001"></a>\n', encoding="utf-8"
            )
            (specs / "system_specification.md").write_text(
                '<a id="sys_001"></a>\n', encoding="utf-8"
            )
            (specs / "architecture_baseline.md").write_text(
                '<a id="arc_001"></a>\n### ARC_001 — Gateway\n\nimplements:\n  - SYS_001\n',
                encoding="utf-8",
            )

            self.assertEqual(auto_link_requirements(root), {"SYS_001": ["ARC_001"]})


class EvidenceAndCommentTests(unittest.TestCase):
    @staticmethod
    def _provenance_args(sha: str) -> list[str]:
        return [
            "--repository",
            "owner/repo",
            "--workflow",
            "Project check",
            "--run-id",
            "1",
            "--run-url",
            "https://github.com/owner/repo/actions/runs/1",
            "--event-sha",
            sha,
        ]

    def test_generate_bundle_main_handles_missing_and_successful_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with (
                patch.object(generate_bundle, "find_project_root", return_value=root),
                patch.object(generate_bundle, "require_supported_python"),
                patch(
                    "sys.argv",
                    [
                        "generate_bundle",
                        "--check-summary",
                        "missing.json",
                        "--test-returncode",
                        "1",
                        *self._provenance_args("a" * 40),
                    ],
                ),
            ):
                self.assertEqual(generate_bundle.main(), 1)

            summary_path = root / "summary.json"
            summary_path.write_text(
                json.dumps({"checks": [{"name": "documents", "ok": True, "errors": []}]}),
                encoding="utf-8",
            )
            bundle = {"acceptance_state": "ready"}
            evidence_path = root / "runtime" / "evidence" / "latest.json"
            with (
                patch.object(generate_bundle, "find_project_root", return_value=root),
                patch.object(generate_bundle, "require_supported_python"),
                patch.object(generate_bundle, "git_info", return_value={"commit": "a" * 40}),
                patch.object(generate_bundle, "build_evidence_bundle", return_value=bundle),
                patch.object(generate_bundle, "write_evidence_bundle", return_value=evidence_path),
                patch(
                    "sys.argv",
                    [
                        "generate_bundle",
                        "--check-summary",
                        "summary.json",
                        "--test-returncode",
                        "0",
                        "--test-output",
                        "Ran 2 tests\\nOK",
                        *self._provenance_args("a" * 40),
                    ],
                ),
            ):
                self.assertEqual(generate_bundle.main(), 0)

    def test_pr_comment_formats_failures_and_main_writes_utf8(self) -> None:
        summary = {
            "checks": [
                {"name": "documents", "ok": True, "errors": []},
                {"name": "traceability", "ok": False, "errors": ["broken edge"]},
            ]
        }
        comment = post_pr_comment.format_pr_comment(
            {"git_sha": "a" * 40, "acceptance_state": "blocked"}, summary, 1
        )
        self.assertIn("❌ FAIL", comment)
        self.assertIn("broken edge", comment)
        self.assertIn("`blocked`", comment)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "evidence.json").write_text(
                json.dumps({"git_sha": "b" * 40, "acceptance_state": "ready"}),
                encoding="utf-8",
            )
            (root / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
            with (
                patch.object(post_pr_comment, "find_project_root", return_value=root),
                patch(
                    "sys.argv",
                    [
                        "post_pr_comment",
                        "--evidence-path",
                        "evidence.json",
                        "--check-summary",
                        "summary.json",
                        "--test-returncode",
                        "0",
                        "--output",
                        "runtime/comment.md",
                    ],
                ),
            ):
                self.assertEqual(post_pr_comment.main(), 0)
            self.assertIn("bbbbbbbb", (root / "runtime/comment.md").read_text("utf-8"))

    def test_quality_record_main_rejects_invalid_sha_and_writes_valid_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / "artifact.txt"
            artifact.write_text("ok", encoding="utf-8")
            with (
                patch(
                    "operations.scripts.quality.record_quality_suite.find_project_root",
                    return_value=root,
                ),
                patch(
                    "sys.argv",
                    [
                        "record_quality_suite",
                        "--git-sha",
                        "bad",
                        "--output",
                        "record.json",
                        "--artifact",
                        "artifact.txt",
                        *self._provenance_args("c" * 40),
                    ],
                ),
            ):
                self.assertEqual(record_quality_main(), 1)

            with (
                patch(
                    "operations.scripts.quality.record_quality_suite.find_project_root",
                    return_value=root,
                ),
                patch(
                    "sys.argv",
                    [
                        "record_quality_suite",
                        "--git-sha",
                        "c" * 40,
                        "--output",
                        "runtime/record.json",
                        "--artifact",
                        "artifact.txt",
                        *self._provenance_args("c" * 40),
                    ],
                ),
            ):
                self.assertEqual(record_quality_main(), 0)
            record = json.loads((root / "runtime/record.json").read_text("utf-8"))
            self.assertEqual(record["git_sha"], "c" * 40)


class QualityUtilityTests(unittest.TestCase):
    def test_task_path_validation_reports_missing_exact_and_glob_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tasks = root / "work" / "tasks"
            tasks.mkdir(parents=True)
            (root / "existing.txt").write_text("ok", encoding="utf-8")
            (tasks / "task_001.md").write_text(
                "allowed_paths:\n  - missing.txt\n  - src/**\n  - existing.txt\n", encoding="utf-8"
            )
            errors = validate_task_paths(root)
            self.assertEqual(len(errors), 2)
            self.assertTrue(any("missing.txt" in error for error in errors))
            self.assertTrue(any("src/**" in error for error in errors))

    def test_owner_action_practicality_reports_each_policy_violation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "project_status.md").write_text(
                "## Ваше действие сейчас\nЗапустить python и слить PR.\n"
                "## Когда потребуется ваше участие\n"
                + "".join(f"{index}. Step\n" for index in range(1, 8))
                + "\n`ПРОДОЛЖАЙ m02` `ПРОДОЛЖАЙ m03`\n",
                encoding="utf-8",
            )
            errors = check_project_status(root)
            self.assertGreaterEqual(len(errors), 4)

    def test_requirement_coverage_detects_uncovered_and_empty_tests(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with (
                patch(
                    "operations.scripts.quality.test_coverage.collect_milestones",
                    return_value={"current": {"id": "m02", "work_state": "in-progress"}},
                ),
                patch(
                    "operations.scripts.quality.test_coverage.milestone_test_coverage",
                    return_value=({"SYS_001", "SYS_002", "SEC_CTL_001"}, {"SYS_001"}),
                ),
            ):
                errors = validate_test_coverage(root)
            self.assertTrue(any("SYS_002" in error for error in errors))
            self.assertTrue(any("SEC_CTL_001" in error for error in errors))

    def test_planned_milestone_defers_test_coverage_gate(self) -> None:
        with patch(
            "operations.scripts.quality.test_coverage.collect_milestones",
            return_value={"current": {"id": "m03", "work_state": "planned"}},
        ):
            self.assertEqual(validate_test_coverage(Path(".")), [])

    def test_technical_status_writes_snapshot_bound_to_commit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot = {"acceptance": {"state": "ready"}}
            with (
                patch(
                    "operations.scripts.status.technical_status.build_progress_snapshot",
                    return_value=snapshot,
                ),
                patch(
                    "operations.scripts.status.technical_status.render_progress_sections",
                    return_value="Progress",
                ),
            ):
                path = generate_technical_status(
                    root,
                    check_summary={},
                    test_returncode=0,
                    test_output="OK",
                    git={"commit": "d" * 40},
                )
            text = path.read_text(encoding="utf-8")
            self.assertIn("technical_status_dddddddddddd", text)
            self.assertIn("acceptance_state: ready", text)
            self.assertIn("Progress", text)


if __name__ == "__main__":
    unittest.main()
