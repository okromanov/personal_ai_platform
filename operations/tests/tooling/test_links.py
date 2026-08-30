from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from operations.scripts.documents.links import (
    _fix_bare_identifier_references,
    _fix_clickable_document_references,
    _href_for_record,
    _is_literal_command_span,
    _own_identifiers,
    _resolve_document_reference,
    check_markdown_links,
    fix_markdown_links,
)


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

    def test_rejects_range_shorthand_that_drops_second_endpoint_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "adr").mkdir()
            (root / "adr" / "adr_001_a.md").write_text(
                "---\nid: ADR_001\ntype: adr\n---\n\n# ADR_001\n", encoding="utf-8"
            )
            (root / "adr" / "adr_004_b.md").write_text(
                "---\nid: ADR_004\ntype: adr\n---\n\n# ADR_004\n", encoding="utf-8"
            )
            (root / "source.md").write_text(
                "---\nid: TASK_001\ntype: task\n---\n\n"
                "См. переход [`ADR_001`](adr/adr_001_a.md)–004 отдельным PR.\n",
                encoding="utf-8",
            )
            errors = check_markdown_links(root)
            self.assertTrue(any("диапазон ADR_001–004" in error for error in errors))

    def test_rejects_range_shorthand_sharing_one_code_span(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "work" / "tasks").mkdir(parents=True)
            (root / "work" / "tasks" / "task_014_a.md").write_text(
                "---\nid: TASK_014\ntype: task\n---\n\n# TASK_014\n", encoding="utf-8"
            )
            (root / "work" / "tasks" / "task_017_b.md").write_text(
                "---\nid: TASK_017\ntype: task\n---\n\n# TASK_017\n", encoding="utf-8"
            )
            (root / "source.md").write_text(
                "---\nid: ADR_001\ntype: adr\n---\n\n"
                "Оставшиеся задачи (`TASK_014-017`) несут риск.\n",
                encoding="utf-8",
            )
            errors = check_markdown_links(root)
            self.assertTrue(any("в одном code span" in error for error in errors))

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

    def test_fixes_backtick_wrapped_bare_mention(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "work" / "tasks").mkdir(parents=True)
            (root / "work" / "tests").mkdir(parents=True)
            task_path = root / "work" / "tasks" / "task_002_arc_002.md"
            task_path.write_text(
                "---\nid: TASK_002\ntype: task\nversion: 1.0\n---\n\n"
                "# TASK_002\n\nСм. `TEST_008` в документе.\n",
                encoding="utf-8",
            )
            (root / "work" / "tests" / "test_008.md").write_text(
                "---\nid: TEST_008\ntype: test\nversion: 1.0\n---\n\n# TEST_008\n",
                encoding="utf-8",
            )
            fixed = fix_markdown_links(root)
            self.assertEqual(fixed, ["work/tasks/task_002_arc_002.md"])
            self.assertIn(
                "[`TEST_008`](../tests/test_008.md)", task_path.read_text(encoding="utf-8")
            )
            self.assertEqual(check_markdown_links(root), [])

    def test_fixes_range_shorthand_dropped_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "adr").mkdir()
            (root / "adr" / "adr_001_a.md").write_text(
                "---\nid: ADR_001\ntype: adr\n---\n\n# ADR_001\n", encoding="utf-8"
            )
            (root / "adr" / "adr_004_b.md").write_text(
                "---\nid: ADR_004\ntype: adr\n---\n\n# ADR_004\n", encoding="utf-8"
            )
            source = root / "source.md"
            source.write_text(
                "---\nid: TASK_001\ntype: task\n---\n\n"
                "См. переход [`ADR_001`](adr/adr_001_a.md)–004 отдельным PR.\n",
                encoding="utf-8",
            )
            fixed = fix_markdown_links(root)
            self.assertEqual(fixed, ["source.md"])
            text = source.read_text(encoding="utf-8")
            self.assertIn("[`ADR_001`](adr/adr_001_a.md)–[`ADR_004`](adr/adr_004_b.md)", text)
            self.assertEqual(check_markdown_links(root), [])

    def test_fixes_range_shorthand_sharing_one_code_span(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "work" / "tasks").mkdir(parents=True)
            (root / "work" / "tasks" / "task_014_a.md").write_text(
                "---\nid: TASK_014\ntype: task\n---\n\n# TASK_014\n", encoding="utf-8"
            )
            (root / "work" / "tasks" / "task_017_b.md").write_text(
                "---\nid: TASK_017\ntype: task\n---\n\n# TASK_017\n", encoding="utf-8"
            )
            source = root / "source.md"
            source.write_text(
                "---\nid: ADR_001\ntype: adr\n---\n\n"
                "Оставшиеся задачи (`TASK_014-017`) несут риск.\n",
                encoding="utf-8",
            )
            fixed = fix_markdown_links(root)
            self.assertEqual(fixed, ["source.md"])
            text = source.read_text(encoding="utf-8")
            self.assertIn(
                "[`TASK_014`](work/tasks/task_014_a.md)-[`TASK_017`](work/tasks/task_017_b.md)",
                text,
            )
            self.assertNotIn("`TASK_014-017`", text)
            self.assertEqual(check_markdown_links(root), [])


class LinksInternalHelpersTests(unittest.TestCase):
    """Direct coverage of small internal helpers whose edge branches (missing
    reference, escaping path, malformed frontmatter, out-of-range error line)
    aren't reachable through the public check/fix flow without contrivance."""

    def test_resolve_document_reference_falls_back_to_rglob(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "nested" / "deep").mkdir(parents=True)
            (root / "nested" / "deep" / "target.md").write_text("# Target\n", encoding="utf-8")
            source = root / "elsewhere" / "source.md"
            source.parent.mkdir(parents=True)
            source.write_text("placeholder\n", encoding="utf-8")
            resolved = _resolve_document_reference(root, source, "target.md")
            self.assertEqual(resolved, root / "nested" / "deep" / "target.md")

    def test_resolve_document_reference_returns_none_when_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.md"
            source.write_text("placeholder\n", encoding="utf-8")
            self.assertIsNone(_resolve_document_reference(root, source, "missing.md"))

    def test_resolve_document_reference_ignores_path_escaping_root(self) -> None:
        with tempfile.TemporaryDirectory() as outer:
            outer_path = Path(outer)
            root = outer_path / "repo"
            (root / "sub").mkdir(parents=True)
            (outer_path / "outside.md").write_text("# Outside\n", encoding="utf-8")
            source = root / "sub" / "source.md"
            source.write_text("placeholder\n", encoding="utf-8")
            self.assertIsNone(_resolve_document_reference(root, source, "../../outside.md"))

    def test_own_identifiers_tolerates_malformed_frontmatter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "broken.md"
            text = "---\nnot a valid frontmatter line\n---\n\n### BR_001 — Пример\n"
            path.write_text(text, encoding="utf-8")
            self.assertEqual(_own_identifiers(path, text), set())

    def test_href_for_record_self_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "work" / "tasks" / "task_001.md"
            source.parent.mkdir(parents=True)
            source.write_text("placeholder\n", encoding="utf-8")
            whole_file: dict[str, object] = {
                "path": "work/tasks/task_001.md",
                "family": "TASK",
                "anchor": "task_001",
            }
            self.assertEqual(_href_for_record(whole_file, source, root), "")
            anchored: dict[str, object] = {
                "path": "work/tasks/task_001.md",
                "family": "BR",
                "anchor": "br_001",
            }
            self.assertEqual(_href_for_record(anchored, source, root), "#br_001")

    def test_is_literal_command_span_single_identifier_is_not_literal(self) -> None:
        line = "См. `TEST_008` в документе."
        start = line.index("TEST_008")
        end = start + len("TEST_008")
        self.assertFalse(_is_literal_command_span(line, start, end))

    def test_fix_bare_identifier_references_skips_unknown_and_out_of_range(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "source.md"
            path.write_text("одна строка\n", encoding="utf-8")
            errors = [
                "source.md:1: упоминание UNKNOWN_001 должно быть кликабельной ссылкой "
                "на nowhere.md#unknown",
                "source.md:99: упоминание BR_001 должно быть кликабельной ссылкой "
                "на specifications/business_requirements.md#br_001",
            ]
            changed = _fix_bare_identifier_references(root, errors, {}, None)
            self.assertEqual(changed, set())

    def test_fix_clickable_document_references_covers_edge_branches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "target.md").write_text("# Target\n", encoding="utf-8")
            path = root / "source.md"
            path.write_text("текст без обратных кавычек\n", encoding="utf-8")
            errors = [
                "source.md:99: ссылка на существующий документ должна быть кликабельной: target.md",
                "source.md:1: ссылка на существующий документ должна быть кликабельной: missing.md",
                "source.md:1: ссылка на существующий документ должна быть кликабельной: target.md",
            ]
            changed = _fix_clickable_document_references(root, errors, None)
            self.assertEqual(changed, set())


if __name__ == "__main__":
    unittest.main()
