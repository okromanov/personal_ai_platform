from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from operations.scripts.documents.links import check_markdown_links


class LinkTests(unittest.TestCase):
    def test_rejects_unlinked_existing_markdown_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "target.md").write_text("# Target\n", encoding="utf-8")
            (root / "source.md").write_text("См. `target.md`.\n", encoding="utf-8")
            errors = check_markdown_links(root)
            self.assertTrue(any("должна быть кликабельной" in error for error in errors))

    def test_accepts_clickable_markdown_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "target.md").write_text("# Target\n", encoding="utf-8")
            (root / "source.md").write_text(
                "См. [`target.md`](target.md).\n",
                encoding="utf-8",
            )
            self.assertEqual(check_markdown_links(root), [])

    def test_rejects_link_from_document_to_itself(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "source.md").write_text(
                "См. [`source.md`](source.md).\n",
                encoding="utf-8",
            )
            errors = check_markdown_links(root)
            self.assertTrue(any("не должен ссылаться сам на себя" in error for error in errors))

    def test_accepts_internal_anchor_without_repeating_filename(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "source.md").write_text(
                "[Перейти к разделу](#раздел)\n\n## Раздел\n",
                encoding="utf-8",
            )
            self.assertEqual(check_markdown_links(root), [])

    def test_ignores_code_blocks_and_future_filename_examples(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "source.md").write_text(
                "```powershell\nGet-Content target.md\n```\nШаблон `task_xxxx.md`.\n",
                encoding="utf-8",
            )
            self.assertEqual(check_markdown_links(root), [])

    def test_runtime_artifact_does_not_change_document_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "source.md").write_text(
                "Техническая сводка: `runtime/technical_status.md`.\n",
                encoding="utf-8",
            )
            errors_before = check_markdown_links(root)

            runtime = root / "runtime"
            runtime.mkdir()
            (runtime / "technical_status.md").write_text("# Сводка\n", encoding="utf-8")
            errors_after = check_markdown_links(root)

            self.assertEqual(errors_before, [])
            self.assertEqual(errors_after, errors_before)


if __name__ == "__main__":
    unittest.main()
