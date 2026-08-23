from __future__ import annotations

import unittest
from pathlib import Path

from operations.scripts.documents.test_catalog import collect_tests, render_test_catalog

ROOT = Path(__file__).resolve().parents[3]


class CollectTestsTests(unittest.TestCase):
    def test_discovers_every_test_the_canonical_runner_would_run(self) -> None:
        import unittest as _unittest

        loader = _unittest.TestLoader()
        discovery_root = (ROOT / "operations/tests").resolve()
        suite = loader.discover(
            str(discovery_root), pattern="test_*.py", top_level_dir=str(discovery_root)
        )
        self.assertEqual(len(collect_tests(ROOT)), suite.countTestCases())

    def test_each_row_has_a_non_empty_description(self) -> None:
        for row in collect_tests(ROOT):
            self.assertTrue(row["description"].strip(), row)

    def test_category_is_always_a_known_label(self) -> None:
        from operations.scripts.documents.test_catalog import CATEGORY_LABELS

        for row in collect_tests(ROOT):
            self.assertIn(row["category"], CATEGORY_LABELS)

    def test_undocumented_test_falls_back_to_humanized_method_name(self) -> None:
        row = next(
            row
            for row in collect_tests(ROOT)
            if row["file"] == "operations/tests/tooling/test_test_catalog.py"
            and row["method"] == "test_undocumented_test_falls_back_to_humanized_method_name"
        )
        self.assertEqual(
            row["description"], "Undocumented test falls back to humanized method name"
        )


class RenderTestCatalogTests(unittest.TestCase):
    def test_output_has_generated_header_and_frontmatter(self) -> None:
        rendered = render_test_catalog(ROOT)
        self.assertTrue(rendered.startswith("<!-- generated file: do not edit manually -->\n"))
        self.assertIn("id: generated_test_catalog", rendered)
        self.assertIn("generation_state: generated", rendered)

    def test_total_count_matches_collected_rows(self) -> None:
        rendered = render_test_catalog(ROOT)
        total = len(collect_tests(ROOT))
        self.assertIn(f"| Всего тестов | `{total}` |", rendered)

    def test_rendering_is_idempotent(self) -> None:
        self.assertEqual(render_test_catalog(ROOT), render_test_catalog(ROOT))

    def test_every_row_appears_in_rendered_table(self) -> None:
        rendered = render_test_catalog(ROOT)
        sample = next(
            row for row in collect_tests(ROOT) if row["file"].endswith("test_test_catalog.py")
        )
        self.assertIn(f"`{sample['method']}`", rendered)


if __name__ == "__main__":
    unittest.main()
