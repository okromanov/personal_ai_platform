from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from operations.scripts.documents.links import check_markdown_links, fix_markdown_links


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

    def test_rejects_bare_identifier_mention_in_prose(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "specifications").mkdir()
            (root / "specifications" / "business_requirements.md").write_text(
                "### BR_001 — Пример\n\nТекст.\n", encoding="utf-8"
            )
            (root / "source.md").write_text(
                "---\nid: TASK_001\ntype: task\n---\n\nСм. требование BR_001 в прозе.\n",
                encoding="utf-8",
            )
            errors = check_markdown_links(root)
            self.assertTrue(any("упоминание BR_001" in error for error in errors))

    def test_accepts_linked_identifier_mention(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "specifications").mkdir()
            (root / "specifications" / "business_requirements.md").write_text(
                "### BR_001 — Пример\n\nТекст.\n", encoding="utf-8"
            )
            (root / "source.md").write_text(
                "---\nid: TASK_001\ntype: task\n---\n\n"
                "См. требование [`BR_001`](specifications/business_requirements.md#br_001).\n",
                encoding="utf-8",
            )
            errors = check_markdown_links(root)
            self.assertEqual([e for e in errors if "упоминание" in e], [])

    def test_ignores_non_document_extension_in_clickable_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "base.py").write_text("class Channel: ...\n", encoding="utf-8")
            (root / "source.md").write_text(
                "Контракт в `src/base.py` без ссылки — это допустимо для кода.\n",
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


class FixLinksTests(unittest.TestCase):
    def test_fixes_bare_mention_once_target_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "work" / "tasks").mkdir(parents=True)
            (root / "work" / "tests").mkdir(parents=True)
            task_path = root / "work" / "tasks" / "task_002_arc_002.md"
            task_path.write_text(
                "---\nid: TASK_002\ntype: task\nversion: 1.0\n---\n\n"
                "# TASK_002\n\nТест TEST_008 проверяет всё.\n",
                encoding="utf-8",
            )
            self.assertEqual(check_markdown_links(root), [])

            (root / "work" / "tests" / "test_008.md").write_text(
                "---\nid: TEST_008\ntype: test\nversion: 1.0\n---\n\n# TEST_008\n",
                encoding="utf-8",
            )
            self.assertTrue(check_markdown_links(root))

            fixed = fix_markdown_links(root)
            self.assertEqual(fixed, ["work/tasks/task_002_arc_002.md"])
            self.assertIn(
                "[`TEST_008`](../tests/test_008.md)", task_path.read_text(encoding="utf-8")
            )
            self.assertEqual(check_markdown_links(root), [])

    def test_fixes_clickable_document_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "target.md").write_text("# Target\n", encoding="utf-8")
            source = root / "source.md"
            source.write_text("См. `target.md`.\n", encoding="utf-8")

            fixed = fix_markdown_links(root)
            self.assertEqual(fixed, ["source.md"])
            self.assertIn("[`target.md`](target.md)", source.read_text(encoding="utf-8"))
            self.assertEqual(check_markdown_links(root), [])

    def test_leaves_literal_commands_unlinked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "milestones.md").write_text(
                '# Вехи\n\n<a id="m01"></a>\n## m01 — Основа\n\nКоманда: `ПРОДОЛЖАЙ m01`.\n',
                encoding="utf-8",
            )
            fixed = fix_markdown_links(root)
            self.assertEqual(fixed, [])
            self.assertEqual(check_markdown_links(root), [])


if __name__ == "__main__":
    unittest.main()
