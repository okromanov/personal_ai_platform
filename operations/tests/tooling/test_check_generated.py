"""Negative paths for check_generated.

Found UNDETECTED by the 2026-09-02 source-level mutation sweep: emptying the
check left the whole suite green. `run_suite.py` does guard the same drift
from the outside — it regenerates and then runs `git diff --exit-code` — but
that step only sees a *tracked* file that changed. It cannot see a
`project_status.md` that was deleted from the tree, and it says nothing about
the generated marker or the template registry. Those are this check's job.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from operations.scripts.documents.check import check_generated
from operations.scripts.documents.repository_tree import GENERATED_HEADER

RENDERED = f"{GENERATED_HEADER}\n---\nid: project_status\n---\n\n# Статус\n"


class CheckGeneratedTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        # Реестр шаблонов проверяется отдельным тестовым модулем; здесь он
        # заглушён, чтобы утверждения касались только производного файла.
        registry = patch(
            "operations.scripts.documents.check.validate_template_registry", return_value=[]
        )
        registry.start()
        self.addCleanup(registry.stop)
        renderer = patch(
            "operations.scripts.documents.check.render_repository_project_status",
            return_value=RENDERED,
        )
        renderer.start()
        self.addCleanup(renderer.stop)

    def _write(self, text: str) -> None:
        (self.root / "project_status.md").write_text(text, encoding="utf-8")

    def test_missing_derived_file_is_reported(self) -> None:
        result = check_generated(self.root)
        self.assertFalse(result.ok)
        self.assertTrue(any("project_status.md" in error for error in result.errors))

    def test_missing_generated_marker_is_reported(self) -> None:
        self._write(RENDERED.replace(GENERATED_HEADER + "\n", "", 1))
        result = check_generated(self.root)
        self.assertTrue(any("marker generated" in error for error in result.errors), result.errors)

    def test_content_that_does_not_match_the_generator_is_reported(self) -> None:
        self._write(f"{GENERATED_HEADER}\n---\nid: project_status\n---\n\n# Отредактировано\n")
        result = check_generated(self.root)
        self.assertTrue(
            any("не соответствует генератору" in error for error in result.errors),
            result.errors,
        )

    def test_matching_generated_file_passes(self) -> None:
        self._write(RENDERED)
        self.assertEqual(check_generated(self.root).errors, [])

    def test_template_registry_errors_are_surfaced_by_this_check(self) -> None:
        # check_generated — единственное место, где реестр шаблонов входит в
        # `check.py --all`; отдельный шаг `template_contracts.py` в
        # run_suite.py к профилю проверок не относится.
        self._write(RENDERED)
        with patch(
            "operations.scripts.documents.check.validate_template_registry",
            return_value=["registry is broken"],
        ):
            result = check_generated(self.root)
        self.assertIn("registry is broken", result.errors)


if __name__ == "__main__":
    unittest.main()
