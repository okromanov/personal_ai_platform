from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from operations.scripts.versioning.increment_file_version import (
    increment_version,
    update_file_version,
)


class IncrementVersionTests(unittest.TestCase):
    def test_increments_minor_version(self) -> None:
        self.assertEqual(increment_version("1.0"), "1.1")
        self.assertEqual(increment_version("1.8"), "1.9")

    def test_rolls_over_to_next_major_at_minor_nine(self) -> None:
        self.assertEqual(increment_version("1.9"), "2.0")
        self.assertEqual(increment_version("4.9"), "5.0")

    def test_returns_input_unchanged_when_not_semantic_version(self) -> None:
        self.assertEqual(increment_version("not-a-version"), "not-a-version")
        self.assertEqual(increment_version(""), "")


class UpdateFileVersionTests(unittest.TestCase):
    def test_bumps_version_field_in_frontmatter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "doc.md"
            path.write_text(
                "---\nid: DOC_001\nversion: 1.0\n---\n\n# Doc\n",
                encoding="utf-8",
            )

            self.assertTrue(update_file_version(str(path)))

            content = path.read_text(encoding="utf-8")
            self.assertIn("version: 1.1", content)
            self.assertNotIn("version: 1.0", content)

    def test_preserves_rest_of_document_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "doc.md"
            path.write_text(
                "---\nid: DOC_002\nversion: 2.9\nother: value\n---\n\n# Body text\n",
                encoding="utf-8",
            )

            update_file_version(str(path))

            content = path.read_text(encoding="utf-8")
            self.assertIn("id: DOC_002", content)
            self.assertIn("other: value", content)
            self.assertIn("# Body text", content)
            self.assertIn("version: 3.0", content)

    def test_returns_false_when_file_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing.md"
            self.assertFalse(update_file_version(str(missing)))

    def test_returns_false_for_non_markdown_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "doc.txt"
            path.write_text("version: 1.0\n", encoding="utf-8")
            self.assertFalse(update_file_version(str(path)))

    def test_returns_false_when_no_version_field_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "doc.md"
            path.write_text("---\nid: DOC_003\n---\n\n# No version\n", encoding="utf-8")
            self.assertFalse(update_file_version(str(path)))

    def test_skips_fully_generated_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "doc.md"
            path.write_text(
                "<!-- generated file: do not edit manually -->\n"
                "---\nid: DOC_004\nversion: 1.0\n---\n\n# Generated\n",
                encoding="utf-8",
            )

            self.assertFalse(update_file_version(str(path)))

            self.assertIn("version: 1.0", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
