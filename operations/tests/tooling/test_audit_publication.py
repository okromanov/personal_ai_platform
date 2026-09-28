from __future__ import annotations

import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from operations.scripts.audit import prepare_environment as env
from operations.scripts.audit.publication import validate_published_audit
from operations.scripts.tasks import check_change_scope
from operations.scripts.tasks.check_change_scope import validate_audit_publication

ROOT = Path(__file__).resolve().parents[3]
BASELINE = "work/audit/audit_baseline_2026_10_01.md"
EVIDENCE = "work/audit/evidence/2026_10_01_completion"
REGISTER = (
    "| ID | Severity | State | First seen | Review date | Owner | Evidence | Resolution |\n"
    "|---|---|---|---|---|---|---|---|\n"
    "| [AUD-001](a.md#aud-001) | high | resolved | 2026-09-01 | — | owner | e | r |\n"
    "| [AUD-002](a.md#aud-002) | low | open | 2026-09-01 | 2026-12-01 | owner | e | r |\n"
)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


class PublicationTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        _git(self.root, "init", "-q", "-b", "main")
        _git(self.root, "config", "user.email", "audit@example.invalid")
        _git(self.root, "config", "user.name", "Audit")
        self._write("src/app.py", "print('app')\n")
        self._write("work/audit/audit_register.md", REGISTER)
        _git(self.root, "add", ".")
        _git(self.root, "commit", "-q", "-m", "audited state")
        self.audited = _git(self.root, "rev-parse", "HEAD")
        self.base = self.audited
        self.tracked = ["src/app.py", "work/audit/audit_register.md"]

    def _write(self, path: str, text: str) -> None:
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    def _package(self, **overrides: object) -> dict[str, object]:
        entries, digest = env.tree_digest(env.run_command, self.root, self.audited)
        package: dict[str, object] = {
            "manifest.json": {"mode": "FULL_REPOSITORY", "head_sha": self.audited},
            "environment_attestation.json": {
                "schema": env.SCHEMA,
                "target_sha": self.audited,
                "ready": True,
                "tree": {"entries": entries, "sha256": digest},
                "checks": [{"name": "git_full_history", "passed": True, "detail": "full history"}],
            },
            "file_role_inventory.json": {
                "files": [
                    {"path": path, "evidence_state": "CURRENT_CONTENT_REVIEWED"}
                    for path in self.tracked
                ]
            },
            "previous_findings.json": {
                "records": [
                    {"id": "AUD-001", "evaluation": "CONFIRMED"},
                    {"id": "AUD-002", "evaluation": "REGRESSION"},
                ]
            },
        }
        package.update(overrides)
        return package

    def _publish(self, package: dict[str, object]) -> str:
        self._write(BASELINE, "# Аудит\n")
        for name, content in package.items():
            text = content if isinstance(content, str) else json.dumps(content)
            self._write(f"{EVIDENCE}/{name}", text)
        _git(self.root, "add", ".")
        _git(self.root, "commit", "-q", "-m", "publish audit")
        return _git(self.root, "rev-parse", "HEAD")

    def _errors(self, package: dict[str, object]) -> list[str]:
        head = self._publish(package)
        return validate_published_audit(self.root, head, BASELINE)

    def test_complete_audit_is_accepted(self) -> None:
        self.assertEqual(self._errors(self._package()), [])

    def test_missing_evidence_file_is_rejected(self) -> None:
        package = self._package()
        del package["environment_attestation.json"]
        errors = self._errors(package)
        self.assertTrue(any("environment_attestation.json" in e for e in errors), errors)

    def test_invalid_json_is_rejected(self) -> None:
        errors = self._errors(self._package(**{"manifest.json": "{not json"}))
        self.assertTrue(any("некорректный JSON" in e for e in errors), errors)

    def test_environment_that_was_not_ready_is_rejected(self) -> None:
        package = self._package()
        attestation = dict(package["environment_attestation.json"])  # type: ignore[call-overload]
        attestation["ready"] = False
        attestation["checks"] = [{"name": "tool_gitleaks", "passed": False, "detail": "missing"}]
        errors = self._errors(self._package(**{"environment_attestation.json": attestation}))
        self.assertTrue(any("tool_gitleaks" in e for e in errors), errors)

    def test_unknown_attestation_schema_is_rejected(self) -> None:
        errors = self._errors(self._package(**{"environment_attestation.json": {"schema": "x"}}))
        self.assertTrue(any("неизвестная схема" in e for e in errors), errors)
        errors = validate_published_audit(self.root, "HEAD", BASELINE)
        self.assertTrue(errors)

    def test_attestation_for_another_tree_is_rejected(self) -> None:
        package = self._package()
        attestation = dict(package["environment_attestation.json"])  # type: ignore[call-overload]
        attestation["tree"] = {"entries": 99, "sha256": "0" * 64}
        errors = self._errors(self._package(**{"environment_attestation.json": attestation}))
        self.assertTrue(any("дерево в attestation" in e for e in errors), errors)

    def test_audited_commit_missing_from_history_is_rejected(self) -> None:
        package = self._package()
        attestation = dict(package["environment_attestation.json"])  # type: ignore[call-overload]
        attestation["target_sha"] = "1" * 40
        errors = self._errors(self._package(**{"environment_attestation.json": attestation}))
        self.assertTrue(any("недоступен в истории" in e for e in errors), errors)

    def test_manifest_for_another_revision_is_rejected(self) -> None:
        manifest = {"mode": "FULL_REPOSITORY", "head_sha": "2" * 40}
        errors = self._errors(self._package(**{"manifest.json": manifest}))
        self.assertTrue(any("head_sha" in e for e in errors), errors)

    def test_not_checked_file_is_rejected(self) -> None:
        inventory = {
            "files": [
                {"path": "src/app.py", "evidence_state": "NOT_CHECKED"},
                {"path": "work/audit/audit_register.md", "evidence_state": "CURRENT"},
            ]
        }
        errors = self._errors(self._package(**{"file_role_inventory.json": inventory}))
        self.assertTrue(any("NOT_CHECKED: src/app.py" in e for e in errors), errors)

    def test_full_audit_must_cover_every_tracked_file(self) -> None:
        inventory = {"files": [{"paths": ["src/app.py", "ghost.py"], "evidence_state": "CURRENT"}]}
        errors = self._errors(self._package(**{"file_role_inventory.json": inventory}))
        self.assertTrue(any("work/audit/audit_register.md" in e for e in errors), errors)
        self.assertTrue(any("ghost.py" in e for e in errors), errors)

    def test_changeset_audit_needs_no_full_coverage_but_no_not_checked(self) -> None:
        inventory = {"files": [{"path": "src/app.py", "evidence_state": "CURRENT"}]}
        manifest = {"mode": "CHANGESET", "head_sha": self.audited}
        package = self._package(
            **{"file_role_inventory.json": inventory, "manifest.json": manifest}
        )
        self.assertEqual(self._errors(package), [])

    def test_every_register_entry_must_be_rechecked(self) -> None:
        findings = {
            "records": [
                {"id": "AUD-001", "evaluation": "NOT_CHECKED"},
            ]
        }
        errors = self._errors(self._package(**{"previous_findings.json": findings}))
        self.assertTrue(any("не перепроверены записи реестра: AUD-002" in e for e in errors))
        self.assertTrue(any("AUD-001" in e and "итоговой оценки" in e for e in errors), errors)

    def test_malformed_containers_are_rejected(self) -> None:
        package = self._package(
            **{"file_role_inventory.json": [], "previous_findings.json": {"records": {}}}
        )
        errors = self._errors(package)
        self.assertTrue(any("списком files" in e for e in errors), errors)
        self.assertTrue(any("списком records" in e for e in errors), errors)

    def test_gate_checks_only_newly_added_baselines(self) -> None:
        head = self._publish(self._package())
        self.assertEqual(validate_audit_publication(self.root, self.base, head), [])
        self._write(f"{EVIDENCE}/file_role_inventory.json", json.dumps({"files": []}))
        _git(self.root, "commit", "-q", "-am", "later edit")
        later = _git(self.root, "rev-parse", "HEAD")
        self.assertEqual(validate_audit_publication(self.root, head, later), [])
        errors = validate_audit_publication(self.root, self.base, later)
        self.assertTrue(any("не вошли в инвентарь" in e for e in errors), errors)
        self.assertTrue(validate_audit_publication(self.root, "missing-ref", later))


class ChangeScopeWiringTests(unittest.TestCase):
    VALIDATORS = (
        "validate_change_scope",
        "validate_document_metadata",
        "validate_audit_history",
        "validate_audit_publication",
        "validate_gate_machinery_isolation",
        "validate_coverage_policy_ratchet",
    )

    def test_every_validator_can_fail_the_gate(self) -> None:
        clean = SimpleNamespace(errors=[], completed_tasks=[])
        for failing in self.VALIDATORS:
            with self.subTest(failing=failing), contextlib.ExitStack() as stack:
                stack.enter_context(
                    patch.object(check_change_scope, "find_project_root", return_value=ROOT)
                )
                stack.enter_context(
                    patch.object(check_change_scope, "changed_paths_between", return_value=[])
                )
                stack.enter_context(
                    patch.object(
                        check_change_scope,
                        "review_task_architecture_visualization",
                        return_value=clean,
                    )
                )
                for name in self.VALIDATORS:
                    result = [f"{name} failed"] if name == failing else []
                    stack.enter_context(patch.object(check_change_scope, name, return_value=result))
                stack.enter_context(patch("sys.argv", ["check_change_scope", "--base", "b"]))
                output = stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
                self.assertEqual(check_change_scope.main(), 1)
                self.assertIn(f"{failing} failed", output.getvalue())


class RealHistoryTests(unittest.TestCase):
    def test_the_partial_2026_09_25_publication_would_be_rejected(self) -> None:
        # Published without an environment attestation or a file-role inventory.
        errors = validate_audit_publication(
            ROOT,
            "5713a82f440a318ee89a77cff825430b13adfdf2",
            "5d6915a0363f8503ca13289522cf07d16671750e",
        )
        self.assertTrue(any("environment_attestation.json" in e for e in errors), errors)
        self.assertTrue(any("file_role_inventory.json" in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main()
