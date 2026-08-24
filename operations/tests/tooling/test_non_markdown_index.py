from __future__ import annotations

import unittest
from pathlib import Path

from operations.scripts.common.project import iter_files, relative_posix
from operations.scripts.documents.non_markdown_index import (
    NO_DESCRIPTION,
    _file_description,
    render_non_markdown_index,
)
from operations.scripts.documents.repository_tree import GENERATED_HEADER

ROOT = Path(__file__).resolve().parents[3]


class NonMarkdownIndexTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rendered = render_non_markdown_index(ROOT, "2000-01-01")

    def test_starts_with_generated_marker_and_frontmatter(self) -> None:
        lines = self.rendered.splitlines()
        self.assertEqual(lines[0], GENERATED_HEADER)
        self.assertIn("type: generated_document", self.rendered)

    def test_lists_every_tracked_non_markdown_file_exactly_once(self) -> None:
        expected = {
            relative_posix(path, ROOT)
            for path in iter_files(ROOT, include_generated=False)
            if path.suffix.lower() != ".md"
        }
        for relative in expected:
            self.assertEqual(
                self.rendered.count(f"[`{relative}`]"),
                1,
                f"{relative} should appear exactly once",
            )

    def test_does_not_list_any_markdown_document(self) -> None:
        self.assertNotIn("[`AGENTS.md`]", self.rendered)
        self.assertNotIn("[`project_status.md`]", self.rendered)
        table_start = self.rendered.index("| Файл | Задача | Описание |")
        for line in self.rendered[table_start:].splitlines()[2:]:
            file_cell = line.split("|")[1].strip()
            self.assertFalse(file_cell.endswith(".md`]"), line)

    def test_task_001_deliverables_link_to_their_task(self) -> None:
        row = next(
            line
            for line in self.rendered.splitlines()
            if line.startswith("| [`src/channels/base.py`]")
        )
        self.assertIn("[`TASK_001`](../work/tasks/task_001_arc_001.md)", row)

    def test_file_with_no_owning_task_shows_no_link(self) -> None:
        row = next(
            line for line in self.rendered.splitlines() if line.startswith("| [`pyproject.toml`]")
        )
        self.assertIn("| — |", row)

    def test_distinct_python_modules_get_their_own_real_description(self) -> None:
        base_row = next(
            line
            for line in self.rendered.splitlines()
            if line.startswith("| [`src/channels/base.py`]")
        )
        telegram_row = next(
            line
            for line in self.rendered.splitlines()
            if line.startswith("| [`src/channels/telegram.py`]")
        )
        self.assertNotEqual(base_row, telegram_row)
        self.assertIn("Базовый контракт канала", base_row)
        self.assertIn("Реализация канала Telegram", telegram_row)

    def test_descriptions_are_russian_and_simple(self) -> None:
        table_start = self.rendered.index("| Файл | Задача | Описание |")
        for line in self.rendered[table_start:].splitlines()[2:]:
            cells = line.split("|")
            description = cells[3].strip()
            self.assertNotIn("\n\n", description)
            self.assertFalse(description.startswith("_Описание не задано"))

    def test_file_with_no_registered_description_falls_back_to_dash(self) -> None:
        path = ROOT / "pyproject.toml"
        self.assertEqual(_file_description(path, "some/unregistered/path.json"), NO_DESCRIPTION)

    def test_empty_init_file_gets_the_honest_package_marker(self) -> None:
        path = ROOT / "operations" / "__init__.py"
        self.assertEqual(
            _file_description(path, "operations/__init__.py"),
            "Пустой файл-маркер Python-пакета.",
        )

    def test_shell_script_description_is_russian(self) -> None:
        row = next(
            line
            for line in self.rendered.splitlines()
            if line.startswith("| [`.claude/skills/pre_commit_hook.sh`]")
        )
        self.assertIn("Канонический pre-commit hook", row)
