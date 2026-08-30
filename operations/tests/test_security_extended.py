"""
Security-focused tests that go beyond document/workflow governance
(test_governance_hardening.py) into input-validation robustness: injection
resistance in subprocess invocation, provenance-record spoofing resistance,
and path-traversal containment.

The repository has no user-facing authentication/authorization layer — its
attack surface is CI-facing (build provenance, git command invocation, and
filesystem path handling). These tests target exactly that surface.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from operations.scripts.common.project import relative_posix, run_command
from operations.scripts.quality.registry import validate_server_source


class SubprocessInjectionSafetyTest(unittest.TestCase):
    """run_command must pass argv as a list (never shell=True), so shell
    metacharacters in any single argument are inert."""

    def test_shell_metacharacters_in_argument_are_treated_literally(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / "should_not_exist.txt"
            payload = f"; touch {marker} #"
            # 'echo' just prints the literal string back; if shell=True were
            # used, ';' would terminate the command and 'touch' would run.
            result = run_command(["echo", payload], cwd=Path(tmp))
            self.assertTrue(result.ok)
            self.assertIn(payload, result.stdout)
            self.assertFalse(marker.exists(), "Shell metacharacter was interpreted, not literal")

    def test_command_substitution_syntax_is_inert(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = "$(id)"
            result = run_command(["echo", payload], cwd=Path(tmp))
            self.assertTrue(result.ok)
            # Literal string must come back unexpanded.
            self.assertIn("$(id)", result.stdout)

    def test_nonexistent_binary_fails_closed_not_open(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_command(["definitely-not-a-real-binary-xyz"], cwd=Path(tmp))
            self.assertFalse(result.ok)
            self.assertEqual(result.returncode, 127)


class ProvenanceSpoofingResistanceTest(unittest.TestCase):
    """validate_server_source is the last line of defense against a forged
    CI provenance record being accepted as evidence of a real quality run."""

    def _valid_source(self, **overrides: str) -> dict[str, str]:
        base = {
            "repository": "okromanov/personal_ai_platform",
            "workflow": "Project check",
            "run_id": "123456789",
            "run_url": "https://github.com/okromanov/personal_ai_platform/actions/runs/123456789",
            "event_sha": "a" * 40,
        }
        base.update(overrides)
        return base

    def test_valid_source_passes(self) -> None:
        errors = validate_server_source(self._valid_source())
        self.assertEqual(errors, [])

    def test_lookalike_domain_is_rejected(self) -> None:
        spoofed = self._valid_source(
            run_url="https://github.com.evil.example/okromanov/personal_ai_platform/actions/runs/1"
        )
        errors = validate_server_source(spoofed)
        self.assertTrue(any("run_url" in e for e in errors))

    def test_http_instead_of_https_is_rejected(self) -> None:
        spoofed = self._valid_source(
            run_url="http://github.com/okromanov/personal_ai_platform/actions/runs/123456789"
        )
        errors = validate_server_source(spoofed)
        self.assertTrue(any("run_url" in e for e in errors))

    def test_path_traversal_in_run_url_is_rejected(self) -> None:
        spoofed = self._valid_source(
            run_url="https://github.com/okromanov/personal_ai_platform/actions/runs/../../evil"
        )
        errors = validate_server_source(spoofed)
        self.assertTrue(any("run_url" in e for e in errors))

    def test_non_hex_sha_is_rejected(self) -> None:
        spoofed = self._valid_source(event_sha="g" * 40)
        errors = validate_server_source(spoofed)
        self.assertTrue(any("event_sha" in e for e in errors))

    def test_short_sha_is_rejected(self) -> None:
        spoofed = self._valid_source(event_sha="a" * 7)  # abbreviated SHA
        errors = validate_server_source(spoofed)
        self.assertTrue(any("event_sha" in e for e in errors))

    def test_sha_with_injected_whitespace_is_rejected(self) -> None:
        spoofed = self._valid_source(event_sha="a" * 39 + " ")
        errors = validate_server_source(spoofed)
        self.assertTrue(any("event_sha" in e for e in errors))

    def test_mismatched_expected_sha_is_rejected(self) -> None:
        source = self._valid_source(event_sha="a" * 40)
        errors = validate_server_source(source, expected_sha="b" * 40)
        self.assertTrue(any("не совпадает" in e for e in errors))

    def test_non_numeric_run_id_is_rejected(self) -> None:
        spoofed = self._valid_source(run_id="123; DROP TABLE runs")
        errors = validate_server_source(spoofed)
        self.assertTrue(any("run_id" in e for e in errors))

    def test_missing_fields_are_reported_not_silently_accepted(self) -> None:
        errors = validate_server_source({"repository": "x/y"})
        self.assertTrue(errors)
        self.assertTrue(any("не содержит" in e for e in errors))

    def test_non_dict_input_is_rejected(self) -> None:
        for bad_input in [None, "a string", 42, ["list"], True]:
            with self.subTest(bad_input=bad_input):
                errors = validate_server_source(bad_input)
                self.assertTrue(errors)


class PathTraversalContainmentTest(unittest.TestCase):
    """Filesystem helpers must not silently escape the declared root when
    handed a maliciously-crafted relative path."""

    def test_relative_posix_refuses_dotdot_escape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            outside = Path(tmp) / "outside_secret.txt"
            outside.write_text("secret", encoding="utf-8")

            with self.assertRaises(ValueError):
                relative_posix(outside, root)

    def test_relative_posix_refuses_sibling_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project_a"
            sibling = Path(tmp) / "project_b"
            root.mkdir()
            sibling.mkdir()
            target = sibling / "file.txt"
            target.write_text("data", encoding="utf-8")

            with self.assertRaises(ValueError):
                relative_posix(target, root)


class BuildContextSecretPolicyTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[2]

    def test_source_secrets_package_is_not_ignored_by_git(self) -> None:
        source_candidate = "src/secrets/new_provider.py"
        result = run_command(
            ["git", "check-ignore", "--no-index", "-q", source_candidate],
            cwd=self.root,
        )
        self.assertNotEqual(
            result.returncode,
            0,
            "The source package src/secrets must remain visible to Git",
        )

    def test_root_secret_directory_is_ignored_by_git(self) -> None:
        result = run_command(
            ["git", "check-ignore", "--no-index", "-q", "secrets/local_token"],
            cwd=self.root,
        )
        self.assertEqual(result.returncode, 0)

    def test_docker_context_excludes_common_secret_files(self) -> None:
        patterns = {
            line.strip()
            for line in (self.root / ".dockerignore").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
        required = {
            ".env",
            ".env.*",
            "**/.env",
            "**/.env.*",
            "secrets",
            "credentials",
            "**/*.pem",
            "**/*.key",
            "**/*.p12",
            "**/*.pfx",
            "**/id_rsa*",
            "**/id_ed25519*",
        }
        self.assertEqual(required - patterns, set())
        self.assertNotIn("**/secrets", patterns, "Do not exclude the src/secrets code package")


if __name__ == "__main__":
    unittest.main()
