import os
import subprocess
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
        self.assertNotIn("generated/", workflow)
        self.assertIn("operations\\scripts\\documents\\template_contracts.py", workflow)
        self.assertIn("runtime/health_check_report.md", workflow)
        self.assertIn("runtime/health_check.json", workflow)
        self.assertIn("docker build --pull -f dockerfile", workflow)
        self.assertIn("runtime/container_sbom.spdx.json", workflow)
        self.assertIn("anchore/sbom-action@e22c389904149dbc22b58101806040fa8d37a610", workflow)
        self.assertIn("--require-hashes", workflow)
        self.assertFalse((ROOT / ".github/workflows/publish_health_check_report.yml").exists())

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
        self.assertNotIn("pre_commit_regenerate_dashboards.sh || true", canonical)
        self.assertGreaterEqual(canonical.count("operations/scripts/quality/run_suite.py fast"), 2)

    def test_dashboard_regeneration_is_fail_closed(self) -> None:
        helper = (ROOT / "operations/hooks/pre_commit_regenerate_dashboards.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("set -euo pipefail", helper)
        self.assertNotIn("failed (see output above)", helper)
        self.assertNotIn("exit 0", helper)

    def test_dashboard_regeneration_propagates_generator_failure(self) -> None:
        helper = ROOT / "operations/hooks/pre_commit_regenerate_dashboards.sh"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            document = root / "document.md"
            document.write_text("---\nversion: 1.0\n---\n# Test\n", encoding="utf-8")
            subprocess.run(["git", "add", "document.md"], cwd=root, check=True)

            # find_python() in the helper tries python3.14, python3.13,
            # python3.12, python3, python in that order and picks the first
            # one that satisfies its own `>= 3.12` check via `-c`. Shimming
            # only "python3.12" let whichever of those names the real
            # environment's PATH already provides (e.g. a pre-installed
            # python3.13) win the search instead of this fake, making the
            # test pass or fail depending on what happens to be installed.
            # Shim every name the loop tries so this is deterministic.
            fake_bin = root / "fake_bin"
            fake_bin.mkdir()
            shim_body = '#!/bin/sh\nif [ "$1" = "-c" ]; then exit 0; fi\nexit 23\n'
            for name in ("python3.14", "python3.13", "python3.12", "python3", "python"):
                fake_python = fake_bin / name
                # On Windows, a file written via Python's native filesystem
                # API and then chmod'd (even via a separate `bash -c chmod`
                # call) is not reliably executable from bash's own exec()
                # check afterwards: NTFS has no POSIX execute bit, and Git
                # Bash's MSYS runtime tracks executability through its own
                # metadata that a cross-process, after-the-fact chmod does
                # not reliably set. Writing the shim's content *and* setting
                # its permissions from a single bash invocation avoids that
                # boundary entirely -- bash is the only thing that ever
                # touches the file, on every platform.
                subprocess.run(
                    [
                        "bash",
                        "-c",
                        f"cat > '{fake_python.as_posix()}' && chmod +x '{fake_python.as_posix()}'",
                    ],
                    input=shim_body,
                    text=True,
                    check=True,
                )
            environment = os.environ.copy()
            environment["PATH"] = f"{fake_bin}{os.pathsep}{environment['PATH']}"

            completed = subprocess.run(
                ["bash", str(helper)],
                cwd=root,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(completed.returncode, 23)

    def test_final_report_matches_current_repository_state(self) -> None:
        """work/acceptance/m01_final_report.md is fully computed by render_final_report()
        (see operations/scripts/milestones/update_completion_report.py), so it
        can never carry a stale hand-edited claim left over from an earlier
        quality report: regenerating it must reproduce the committed file
        exactly, aside from the "updated" timestamp, which tracks the date
        update_completion_report.py was last run rather than repository
        content."""
        from operations.scripts.milestones.update_completion_report import (
            render_final_report,
        )

        if subprocess.run(
            ["git", "rev-parse", "--verify", "origin/main^{commit}"],
            cwd=ROOT,
            capture_output=True,
            check=False,
        ).returncode:
            self.skipTest("origin/main недоступен в локальном snapshot")

        def strip_updated(text: str) -> str:
            return "\n".join(line for line in text.splitlines() if not line.startswith("updated: "))

        report = (ROOT / "work/acceptance/m01_final_report.md").read_text(encoding="utf-8")
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
