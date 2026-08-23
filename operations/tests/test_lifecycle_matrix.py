from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from operations.scripts.acceptance.apply import apply_acceptance, validate_evidence_bundle
from operations.scripts.milestones.start import start_milestone
from operations.scripts.status.generate_project_status import collect_milestones
from operations.scripts.tasks.check_change_scope import (
    changed_paths_between,
    validate_change_scope,
)


class LifecycleMatrixTests(unittest.TestCase):
    def _git(self, root: Path, *args: str) -> str:
        completed = subprocess.run(
            ["git", *args], cwd=root, check=True, capture_output=True, text=True
        )
        return completed.stdout.strip()

    @staticmethod
    def _source(sha: str) -> dict[str, object]:
        return {
            "repository": "owner/repo",
            "workflow": "Project check",
            "run_id": "100",
            "run_url": "https://github.com/owner/repo/actions/runs/100",
            "event_sha": sha,
            "artifact_id": "200",
            "artifact_digest": "c" * 64,
        }

    def test_m01_accept_m02_start_premature_reject_and_m02_accept(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "work/tasks").mkdir(parents=True)
            (root / "work/tests").mkdir(parents=True)
            (root / "work/acceptance").mkdir(parents=True)
            (root / "adr").mkdir()
            (root / "milestones.md").write_text(
                "---\nid: milestones\ntype: roadmap\ndocument_state: current\nversion: 1.0\n"
                "updated: 2026-08-21\n---\n\n"
                "## m01 — Foundation\n\n- work_state: `in-progress`\n\n"
                "## m02 — Feature\n\n- work_state: `planned`\n"
                "- состав: `BR_001`, `SYS_001`\n",
                encoding="utf-8",
            )
            (root / "adr/adr_001.md").write_text(
                "---\nid: ADR_001\ntype: adr\ndecision_state: proposed\nversion: 1.0\n"
                "updated: 2026-08-21\ntraces_to:\n  - m01\n---\n# ADR_001 — Baseline\n",
                encoding="utf-8",
            )
            self._git(root, "init", "-b", "feature")
            self._git(root, "config", "user.name", "Lifecycle")
            self._git(root, "config", "user.email", "lifecycle@example.invalid")
            self._git(root, "add", "milestones.md", "adr/adr_001.md")
            self._git(root, "commit", "-m", "m01 ready")
            m01_source = self._git(root, "rev-parse", "HEAD")

            changed = apply_acceptance(
                root,
                "m01",
                source_sha=m01_source,
                evidence_ref="server:evidence",
                semantic_review_ref="server:semantic",
                owner_confirmation="ПРИНИМАЮ m01",
                accepted_at="2026-08-21T10:00:00Z",
                server_source=self._source(m01_source),
                evidence_data={
                    "acceptance_state": "ready-for-semantic-review",
                    "git_sha": m01_source,
                },
                semantic_review_data={
                    "milestone": "m01",
                    "result": "pass",
                    "reviewed_sha": m01_source,
                },
            )
            self.assertEqual(
                set(changed),
                {"adr/adr_001.md", "milestones.md", "work/acceptance/m01.json"},
            )
            self._git(root, "add", *changed)
            self._git(root, "commit", "-m", "accept m01")
            m01_acceptance = self._git(root, "rev-parse", "HEAD")
            scope_paths = changed_paths_between(root, m01_source, m01_acceptance)
            self.assertEqual(
                validate_change_scope(
                    root,
                    scope_paths,
                    base=m01_source,
                    head=m01_acceptance,
                ),
                [],
            )
            accepted_adr = (root / "adr/adr_001.md").read_text(encoding="utf-8")
            (root / "adr/adr_001.md").write_text(
                accepted_adr + "\nНеразрешённая смысловая правка.\n", encoding="utf-8"
            )
            self._git(root, "add", "adr/adr_001.md")
            self._git(root, "commit", "-m", "tamper acceptance")
            tampered = self._git(root, "rev-parse", "HEAD")
            self.assertTrue(
                validate_change_scope(
                    root,
                    changed_paths_between(root, m01_source, tampered),
                    base=m01_source,
                    head=tampered,
                )
            )
            (root / "adr/adr_001.md").write_text(accepted_adr, encoding="utf-8")
            self._git(root, "add", "adr/adr_001.md")
            self._git(root, "commit", "-m", "restore exact acceptance")

            (root / "operations").mkdir()
            (root / "specifications").mkdir()
            (root / "specifications/model.md").write_text(
                "### BR_001 — Goal\n\n"
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
            task = root / "work/tasks/task_001.md"
            task.write_text(
                "---\nid: TASK_001\ntype: task\ntitle: Adapter\ncomponent: ARC_CMP_001\n"
                "work_state: in-progress\nversion: 1.0\nupdated: 2026-08-21\n"
                "next_actor: agent\nowner_action: none\nallowed_paths:\n  - work/tasks/task_001.md\n"
                "traces_to:\n  - m02\nimplements:\n  - ARC_CMP_001\n---\n"
                "# TASK_001 — Adapter\n\n## 5. План выполнения\n\n- [ ] Build\n",
                encoding="utf-8",
            )
            (root / "work/tests/test_001.md").write_text(
                "---\nid: TEST_001\ntype: test\nspec_state: current\nversion: 1.0\n"
                "traces_to:\n  - TASK_001\nverifies:\n  - SYS_001\naccepts:\n  - m02\n"
                "automated_evidence: e\n---\n# TEST_001 — Adapter\n",
                encoding="utf-8",
            )
            self._git(root, "add", "operations", "specifications", "work/tasks", "work/tests")
            self._git(root, "commit", "-m", "prepare m02")
            with patch("operations.scripts.milestones.start.today_iso", return_value="2026-08-21"):
                self.assertEqual(start_milestone(root, "m02", dry_run=True), [])
                self.assertEqual(start_milestone(root, "m02", dry_run=False), [])
            self._git(root, "add", "milestones.md")
            self._git(root, "commit", "-m", "start m02")
            m02_started = self._git(root, "rev-parse", "HEAD")

            invalid = root.parent / "premature-evidence.json"
            invalid.write_text(
                json.dumps(
                    {
                        "schema_version": 2,
                        "milestone": "m02",
                        "acceptance_state": "not-ready",
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "техническую готовность"):
                validate_evidence_bundle(root, invalid, "m02")
            with self.assertRaisesRegex(ValueError, "не завершены TASK"):
                apply_acceptance(
                    root,
                    "m02",
                    source_sha=m02_started,
                    evidence_ref="server:evidence",
                    semantic_review_ref="server:semantic",
                    owner_confirmation="ПРИНИМАЮ m02",
                    accepted_at="2026-08-21T12:00:00Z",
                    server_source=self._source(m02_started),
                )

            task.write_text(
                task.read_text(encoding="utf-8")
                .replace("work_state: in-progress", "work_state: completed")
                .replace("next_actor: agent", "next_actor: none")
                .replace("- [ ] Build", "- [x] Build"),
                encoding="utf-8",
            )
            self._git(root, "add", "work/tasks/task_001.md")
            self._git(root, "commit", "-m", "complete m02")
            m02_source = self._git(root, "rev-parse", "HEAD")
            apply_acceptance(
                root,
                "m02",
                source_sha=m02_source,
                evidence_ref="server:evidence",
                semantic_review_ref="server:semantic",
                owner_confirmation="ПРИНИМАЮ m02",
                accepted_at="2026-08-21T13:00:00Z",
                server_source=self._source(m02_source),
                evidence_data={
                    "acceptance_state": "ready-for-semantic-review",
                    "git_sha": m02_source,
                },
                semantic_review_data={
                    "milestone": "m02",
                    "result": "pass",
                    "reviewed_sha": m02_source,
                },
            )
            milestone_items = collect_milestones(root)["items"]
            self.assertIsInstance(milestone_items, list)
            if isinstance(milestone_items, list):
                self.assertEqual(milestone_items[1]["work_state"], "completed")
