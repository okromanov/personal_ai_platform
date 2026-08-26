import tempfile
import unittest
from pathlib import Path
from typing import cast

from operations.scripts.quality.record_quality_suite import build_record
from operations.scripts.quality.scope import PYTHON_QUALITY_PATHS, PYTHON_SOURCE_PATHS

ROOT = Path(__file__).resolve().parents[2]


class QualityIntegrationTests(unittest.TestCase):
    def test_event_gate_covers_push_pr_and_manual(self) -> None:
        workflow = (ROOT / ".github/workflows/project_check.yml").read_text(encoding="utf-8")
        runner = (ROOT / "operations/scripts/quality/run_suite.py").read_text(encoding="utf-8")
        for trigger in (
            "workflow_dispatch:",
            "pull_request:",
            "merge_group:",
            "push:",
        ):
            self.assertIn(trigger, workflow)
        # No cron schedule: every code change already triggers the full
        # suite via push/pull_request, so a time-based run would only
        # re-check an unchanged tree.
        self.assertNotIn("schedule:", workflow)
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
        self.assertNotIn("isInitialSetup", workflow)
        self.assertNotIn("ground zero|initial deployment", workflow)
        self.assertIn("generated/markdown_index.md", workflow)
        self.assertNotIn("generated/document_index.md", workflow)
        self.assertIn("runtime/health_check_report.md", workflow)
        self.assertIn("runtime/health_check.json", workflow)

    def test_quality_scope_includes_product_source_everywhere(self) -> None:
        self.assertIn("src", PYTHON_SOURCE_PATHS)
        self.assertEqual(
            PYTHON_QUALITY_PATHS,
            ("operations/scripts", "src", "operations/tests"),
        )
        runner = (ROOT / "operations/scripts/quality/run_suite.py").read_text(encoding="utf-8")
        analyzer = (ROOT / "operations/scripts/quality/code_analyzer.py").read_text(
            encoding="utf-8"
        )
        health = (ROOT / "operations/scripts/health_check/metrics.py").read_text(encoding="utf-8")
        self.assertIn("PYTHON_SOURCE_PATHS", runner)
        self.assertIn("PYTHON_QUALITY_PATHS", runner)
        self.assertIn("PYTHON_QUALITY_PATHS", analyzer)
        self.assertIn("PYTHON_QUALITY_PATHS", health)

    def test_quality_record_requires_exact_sha_and_present_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "ruff.txt").write_text("passed\n", encoding="utf-8")
            # A tool that finds nothing to report (e.g. Vulture on a clean
            # tree) legitimately writes an empty file; build_record() must
            # accept that rather than treating "empty" the same as "missing".
            (root / "dead_code.txt").write_text("", encoding="utf-8")
            source: dict[str, object] = {
                "repository": "owner/repo",
                "workflow": "Project check",
                "run_id": "123",
                "run_url": "https://github.com/owner/repo/actions/runs/123",
                "event_sha": "a" * 40,
            }
            record = build_record(
                root, "a" * 40, ["ruff.txt", "dead_code.txt"], server_source=source
            )
            self.assertEqual(record["result"], "passed")
            self.assertEqual(record["git_sha"], "a" * 40)
            artifacts = cast(list[dict[str, object]], record["artifacts"])
            self.assertEqual(artifacts[0]["path"], "ruff.txt")
            self.assertEqual(artifacts[1]["bytes"], 0)
            with self.assertRaisesRegex(ValueError, "40-"):
                build_record(root, "short", ["ruff.txt"], server_source=source)
            with self.assertRaisesRegex(ValueError, "отсутствует"):
                build_record(root, "a" * 40, ["missing.txt"], server_source=source)

    def test_pre_commit_hook_contains_validation_logic(self) -> None:
        canonical = (ROOT / "operations/hooks/pre_commit_hook.sh").read_text(encoding="utf-8")
        self.assertIn("operations/scripts/quality/run_suite.py fast", canonical)

    def test_final_report_matches_current_repository_state(self) -> None:
        """work/m01_final_report.md is fully computed by render_final_report()
        (see operations/scripts/milestones/update_completion_report.py), so it
        can never carry a stale hand-edited claim left over from an earlier
        quality report: regenerating it must reproduce the committed file
        exactly, aside from the "updated" timestamp, which tracks the date
        update_completion_report.py was last run rather than repository
        content."""
        from operations.scripts.milestones.update_completion_report import (
            render_final_report,
        )

        def strip_updated(text: str) -> str:
            return "\n".join(line for line in text.splitlines() if not line.startswith("updated: "))

        report = (ROOT / "work/m01_final_report.md").read_text(encoding="utf-8")
        rendered = render_final_report(ROOT, "m01")
        self.assertEqual(strip_updated(report), strip_updated(rendered))
        for stale_claim in ("70/70", "21/21", "38 требований", "100%", "evidence_state:"):
            self.assertNotIn(stale_claim, report)

    def test_pre_push_hook_runs_the_canonical_full_profile(self) -> None:
        canonical = (ROOT / "operations/hooks/pre_push_hook.sh").read_text(encoding="utf-8")
        self.assertIn("operations/scripts/quality/run_suite.py full", canonical)
        # Network-fetched, pinned-binary checks stay CI-only, not invoked from
        # this local hook (mentioning them in the explanatory comment is fine).
        for ci_only_invocation in ("actionlint ", "gitleaks dir", "-m pip_audit"):
            self.assertNotIn(ci_only_invocation, canonical)

    def test_shellcheck_covers_both_pre_commit_and_pre_push_hooks(self) -> None:
        workflow = (ROOT / ".github/workflows/project_check.yml").read_text(encoding="utf-8")
        for hook_path in (
            "operations/hooks/pre_commit_hook.sh",
            "operations/hooks/pre_push_hook.sh",
        ):
            self.assertIn(hook_path, workflow)

    def test_proposed_technology_adrs_require_m02_evidence(self) -> None:
        for number in range(5, 10):
            path = next((ROOT / "adr").glob(f"adr_00{number}_*.md"))
            text = path.read_text(encoding="utf-8")
            self.assertIn("decision_state: proposed", text)
            self.assertIn("до смены `decision_state`", text)
            self.assertNotIn("(выбран)", text)
