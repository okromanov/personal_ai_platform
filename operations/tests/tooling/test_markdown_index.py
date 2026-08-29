from __future__ import annotations

import unittest
from pathlib import Path

from operations.scripts.common.project import iter_files, relative_posix
from operations.scripts.documents.index import render_index
from operations.scripts.documents.repository_tree import GENERATED_HEADER

ROOT = Path(__file__).resolve().parents[3]


class MarkdownIndexTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rendered = render_index(ROOT, "2000-01-01")

    def test_starts_with_generated_marker_and_frontmatter(self) -> None:
        lines = self.rendered.splitlines()
        self.assertEqual(lines[0], GENERATED_HEADER)
        self.assertIn("id: generated_markdown_index", self.rendered)

    def test_lists_every_tracked_markdown_file_exactly_once(self) -> None:
        expected = {
            relative_posix(path, ROOT)
            for path in iter_files(ROOT, suffixes={".md"}, include_generated=False)
        }
        for relative in expected:
            self.assertEqual(
                self.rendered.count(f"[`{relative}`]"),
                1,
                f"{relative} should appear exactly once",
            )

    def test_no_longer_filters_by_primary_document_status(self) -> None:
        # The diagnostic view covers tracked Markdown without a primary-document filter.
        self.assertIn("[`project_status.md`]", self.rendered)
        self.assertNotIn("[`tasks.md`]", self.rendered)

    def test_generated_directory_is_excluded(self) -> None:
        self.assertNotIn("[`generated/markdown_index.md`]", self.rendered)
        self.assertNotIn("[`generated/non_markdown_index.md`]", self.rendered)
