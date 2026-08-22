import tempfile
import unittest
from pathlib import Path
from typing import cast

from operations.scripts.quality.record_quality_suite import build_record

ROOT = Path(__file__).resolve().parents[2]


class QualityIntegrationTests(unittest.TestCase):
    def test_event_gate_covers_push_pr_manual_and_weekly(self) -> None:
        workflow = (ROOT / ".github/workflows/project_check.yml").read_text(encoding="utf-8")
        runner = (ROOT / "operations/scripts/quality/run_suite.py").read_text(encoding="utf-8")
        for trigger in (
            "workflow_dispatch:",
            "pull_request:",
            "merge_group:",
            "push:",
            "schedule:",
        ):
            self.assertIn(trigger, workflow)
        self.assertIn("quality-skills:", workflow)
        self.assertIn("QUALITY_RESULT", workflow)
        self.assertIn("operations/quality/requirements_dev.txt", workflow)
        self.assertIn("record_quality_suite.py", workflow)
        self.assertIn("runtime/evidence/latest.json", workflow)
        for provenance_argument in (
            "--repository",
            "--workflow",
            "--run-id",
            "--run-url",
            "--event-sha",
        ):
            self.assertIn(provenance_argument, workflow)
        self.assertIn("run_suite.py full", workflow)
        self.assertIn("check_coverage.py", runner)
        self.assertIn("actionlint", workflow)
        self.assertIn("shellcheck", workflow)
        self.assertIn("gitleaks", workflow)
        self.assertIn("pip_audit", workflow)

    def test_quality_record_requires_exact_sha_and_nonempty_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "ruff.txt").write_text("passed\n", encoding="utf-8")
            source: dict[str, object] = {
                "repository": "owner/repo",
                "workflow": "Project check",
                "run_id": "123",
                "run_url": "https://github.com/owner/repo/actions/runs/123",
                "event_sha": "a" * 40,
            }
            record = build_record(root, "a" * 40, ["ruff.txt"], server_source=source)
            self.assertEqual(record["result"], "passed")
            self.assertEqual(record["git_sha"], "a" * 40)
            artifacts = cast(list[dict[str, object]], record["artifacts"])
            self.assertEqual(artifacts[0]["path"], "ruff.txt")
            with self.assertRaisesRegex(ValueError, "40-"):
                build_record(root, "short", ["ruff.txt"], server_source=source)
            with self.assertRaisesRegex(ValueError, "отсутствует"):
                build_record(root, "a" * 40, ["missing.txt"], server_source=source)

    def test_only_one_hook_contains_validation_logic(self) -> None:
        canonical = (ROOT / ".claude/skills/pre_commit_hook.sh").read_text(encoding="utf-8")
        wrapper = (ROOT / "operations/hooks/pre_commit_hook.sh").read_text(encoding="utf-8")
        self.assertIn("operations/scripts/quality/run_suite.py fast", canonical)
        self.assertIn(".claude/skills/pre_commit_hook.sh", wrapper)
        self.assertNotIn("documents/check.py", wrapper)

    def test_superseded_report_cannot_claim_acceptance_readiness(self) -> None:
        report = (ROOT / "work/m01/final_report.md").read_text(encoding="utf-8")
        self.assertIn("evidence_state: superseded", report)
        for stale_claim in ("70/70", "21/21", "38 требований", "100%"):
            self.assertNotIn(stale_claim, report)

    def test_proposed_technology_adrs_require_m02_evidence(self) -> None:
        for number in range(5, 10):
            path = next((ROOT / "adr").glob(f"adr_00{number}_*.md"))
            text = path.read_text(encoding="utf-8")
            self.assertIn("decision_state: proposed", text)
            self.assertIn("до смены `decision_state`", text)
            self.assertNotIn("(выбран)", text)
