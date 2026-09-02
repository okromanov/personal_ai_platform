from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from operations.scripts.common.project import atomic_write_generated, read_text
from operations.scripts.documents.check import FAST_CHECK_NAMES, run_all_checks
from operations.scripts.documents.generate import generate_all


class GenerationSafetyTests(unittest.TestCase):
    def test_renderer_failure_does_not_partially_write_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "project_status.md").write_text("old status\n", encoding="utf-8")
            with patch(
                "operations.scripts.documents.generate.render_repository_project_status",
                side_effect=ValueError("duplicate"),
            ):
                with self.assertRaisesRegex(ValueError, "duplicate"):
                    generate_all(root)
            self.assertEqual(
                (root / "project_status.md").read_text(encoding="utf-8"), "old status\n"
            )
            self.assertFalse((root / "generated").exists())

    def test_generated_snapshot_is_stable_until_content_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "generated.md"
            rendered = "---\ngeneration_state: generated\n---\n\n# Report\n"
            self.assertTrue(atomic_write_generated(path, rendered))
            first = read_text(path)
            self.assertRegex(first, r"(?m)^generated_at: .+$")
            self.assertFalse(atomic_write_generated(path, rendered))
            self.assertEqual(read_text(path), first)
            self.assertTrue(atomic_write_generated(path, rendered + "\nChanged.\n"))
            self.assertNotEqual(read_text(path), first)

    def test_checker_exception_is_localized_and_other_checks_continue(self) -> None:
        # A synthetic empty root is enough: every other check already
        # handles a missing file as its own (possibly failing) result
        # rather than crashing run_all_checks, so this only needs to prove
        # isolation, not re-run the full real-repo check pass (which cost
        # ~4.5s here for no additional assertion coverage).
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch(
                "operations.scripts.documents.check.check_structure",
                side_effect=RuntimeError("boom"),
            ):
                results = run_all_checks(root)
        by_name = {result.name: result for result in results}
        self.assertIn("structure", by_name)
        self.assertIn("secrets", by_name)
        self.assertFalse(by_name["structure"].ok)
        self.assertIn("RuntimeError: boom", by_name["structure"].errors[0])


class CheckProfileCompositionTests(unittest.TestCase):
    """The `--fast` profile is what the pre-commit hook runs, so what it does
    and does not contain is an operational fact, not an implementation
    detail. It used to be a second literal list beside the full one, where a
    renamed check would silently drop out of one profile only.
    """

    def _names(self, *, fast: bool) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            return [result.name for result in run_all_checks(Path(tmp), fast=fast)]

    def test_fast_profile_is_exactly_the_declared_subset(self) -> None:
        self.assertEqual(self._names(fast=True), list(FAST_CHECK_NAMES))

    def test_every_fast_check_also_runs_in_the_full_profile(self) -> None:
        self.assertEqual(set(FAST_CHECK_NAMES) - set(self._names(fast=False)), set())

    def test_secrets_is_in_the_fast_profile(self) -> None:
        # The pre-commit hook is the only gate a commit is guaranteed to
        # pass through; dropping the secret scan from it would move the
        # first detection of a committed secret to CI, after push.
        self.assertIn("secrets", FAST_CHECK_NAMES)

    def test_full_profile_is_a_strict_superset(self) -> None:
        self.assertGreater(len(self._names(fast=False)), len(FAST_CHECK_NAMES))


if __name__ == "__main__":
    unittest.main()
