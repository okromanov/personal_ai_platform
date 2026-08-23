"""
Boundary and edge-case tests for parsing/validation functions that handle
untrusted or externally-influenced text: front matter parsing, confirmation
strings, and text-scanning summaries.

These complement the happy-path coverage in test_acceptance*.py by exercising
empty input, whitespace-only input, Unicode, very large input, and malformed
structure — the classes of input most likely to trigger off-by-one errors or
unhandled exceptions.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from operations.scripts.acceptance.apply import (
    _replace_front_matter_state,
    _replace_front_matter_updated,
    expected_confirmation,
    validate_confirmation,
)
from operations.scripts.common.project import atomic_write, read_text
from operations.scripts.status.generate_project_status import parse_unit_test_summary


class ConfirmationBoundaryTest(unittest.TestCase):
    def test_empty_confirmation_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            validate_confirmation("m01", "")

    def test_whitespace_only_confirmation_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            validate_confirmation("m01", "   \t\n  ")

    def test_confirmation_with_surrounding_whitespace_is_accepted(self) -> None:
        expected = expected_confirmation("m01")
        # Leading/trailing whitespace should be trimmed, matching the
        # documented .strip() contract.
        validate_confirmation("m01", f"  {expected}  \n")

    def test_confirmation_is_case_sensitive(self) -> None:
        expected = expected_confirmation("m01")
        with self.assertRaises(ValueError):
            validate_confirmation("m01", expected.upper())

    def test_confirmation_rejects_extra_characters(self) -> None:
        expected = expected_confirmation("m01")
        with self.assertRaises(ValueError):
            validate_confirmation("m01", expected + "!")

    def test_confirmation_rejects_injection_like_payload(self) -> None:
        with self.assertRaises(ValueError):
            validate_confirmation("m01", "ПРИНИМАЮ m01; rm -rf /")

    def test_confirmation_rejects_zero_width_injection(self) -> None:
        # A zero-width joiner inserted mid-string is invisible when printed
        # but must still break the exact-match check.
        expected = expected_confirmation("m01")
        tampered = expected[:5] + "‍" + expected[5:]
        with self.assertRaises(ValueError):
            validate_confirmation("m01", tampered)

    def test_milestone_id_with_unexpected_case_still_produces_lowercase_token(self) -> None:
        self.assertEqual(expected_confirmation("M01"), "ПРИНИМАЮ m01")


class FrontMatterBoundaryTest(unittest.TestCase):
    def test_empty_document_raises(self) -> None:
        with self.assertRaises(ValueError):
            _replace_front_matter_state("", field="state", allowed_from={"draft"}, target="active")

    def test_document_without_front_matter_raises(self) -> None:
        with self.assertRaises(ValueError):
            _replace_front_matter_state(
                "# Just a heading\n\nBody text.\n",
                field="state",
                allowed_from={"draft"},
                target="active",
            )

    def test_unterminated_front_matter_raises(self) -> None:
        with self.assertRaises(ValueError):
            _replace_front_matter_state(
                "---\nstate: draft\n\nBody without closing marker",
                field="state",
                allowed_from={"draft"},
                target="active",
            )

    def test_missing_field_raises(self) -> None:
        with self.assertRaises(ValueError):
            _replace_front_matter_state(
                "---\ntitle: X\n---\nBody\n",
                field="state",
                allowed_from={"draft"},
                target="active",
            )

    def test_disallowed_transition_raises(self) -> None:
        with self.assertRaises(ValueError):
            _replace_front_matter_state(
                "---\nstate: archived\n---\nBody\n",
                field="state",
                allowed_from={"draft"},
                target="active",
            )

    def test_already_at_target_state_is_idempotent(self) -> None:
        text = "---\nstate: active\n---\nBody\n"
        result = _replace_front_matter_state(
            text, field="state", allowed_from={"draft"}, target="active"
        )
        self.assertEqual(result.replace("\r\n", "\n"), text)

    def test_quoted_field_value_is_normalized(self) -> None:
        text = '---\nstate: "draft"\n---\nBody\n'
        result = _replace_front_matter_state(
            text, field="state", allowed_from={"draft"}, target="active"
        )
        self.assertIn("state: active", result)

    def test_crlf_line_endings_are_normalized(self) -> None:
        text = "---\r\nstate: draft\r\n---\r\nBody\r\n"
        result = _replace_front_matter_state(
            text, field="state", allowed_from={"draft"}, target="active"
        )
        self.assertNotIn("\r", result)
        self.assertIn("state: active", result)

    def test_empty_body_after_front_matter_is_preserved(self) -> None:
        text = "---\nstate: draft\n---\n"
        result = _replace_front_matter_state(
            text, field="state", allowed_from={"draft"}, target="active"
        )
        self.assertTrue(result.startswith("---\nstate: active\n---\n"))

    def test_updated_field_missing_raises_when_update_requested(self) -> None:
        text = "---\nstate: draft\n---\nBody\n"
        with self.assertRaises(ValueError):
            _replace_front_matter_state(
                text,
                field="state",
                allowed_from={"draft"},
                target="active",
                updated="2026-01-01",
            )

    def test_replace_updated_on_document_without_front_matter_raises(self) -> None:
        with self.assertRaises(ValueError):
            _replace_front_matter_updated("no front matter here", "2026-01-01")

    def test_unicode_content_in_body_is_preserved(self) -> None:
        text = "---\nstate: draft\n---\n# Заголовок 🎉\n\nТекст с эмодзи и юникодом: café, naïve.\n"
        result = _replace_front_matter_state(
            text, field="state", allowed_from={"draft"}, target="active"
        )
        self.assertIn("Заголовок 🎉", result)
        self.assertIn("café, naïve", result)


class UnitSummaryBoundaryTest(unittest.TestCase):
    def test_empty_output_with_success_code(self) -> None:
        summary = parse_unit_test_summary(0, "")
        self.assertTrue(summary["ok"])
        self.assertEqual(summary["total"], 0)
        self.assertEqual(summary["failed"], 0)

    def test_empty_output_with_failure_code(self) -> None:
        summary = parse_unit_test_summary(1, "")
        self.assertFalse(summary["ok"])
        # No parseable total, but returncode != 0 must still register a failure.
        self.assertEqual(summary["failed"], 1)

    def test_garbage_output_does_not_crash(self) -> None:
        garbage = "\x00\x01 binary-ish noise � \n" * 50
        summary = parse_unit_test_summary(1, garbage)
        self.assertFalse(summary["ok"])

    def test_very_large_output_is_handled(self) -> None:
        # Simulate a pathological test run with thousands of failure lines.
        huge_output = "Ran 5000 tests in 12.345s\n\n" + (
            "FAIL: test_something (module.Class)\n" * 5000
        )
        summary = parse_unit_test_summary(1, huge_output)
        self.assertEqual(summary["total"], 5000)
        # Only the first few problems should be retained, not all 5000.
        self.assertLessEqual(len(summary["problems"]), 5)


class PathHandlingBoundaryTest(unittest.TestCase):
    # relative_posix's path-traversal rejection is covered by
    # PathTraversalContainmentTest in test_security_extended.py — not
    # duplicated here.

    def test_atomic_write_rejects_empty_path_component_gracefully(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # Deeply nested path that does not exist yet must be created,
            # not silently dropped.
            target = Path(tmp) / "a" / "b" / "c" / "d.txt"
            changed = atomic_write(target, "content")
            self.assertTrue(changed)
            self.assertEqual(read_text(target), "content\n")

    def test_read_text_on_empty_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "empty.txt"
            target.write_text("", encoding="utf-8")
            self.assertEqual(read_text(target), "")


if __name__ == "__main__":
    unittest.main()
