"""Negative paths for check_owner_interface.

Found UNDETECTED by the 2026-09-25 source-level mutation sweep: emptying the
check left the whole suite green. These tests ensure each sub-check can fail
independently.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from operations.scripts.documents.check import check_owner_interface

_BASE = """\
# Статус

Ваше действие сейчас: продолжить.

Чтобы продолжить, отправьте агенту одну команду.

| Следующий исполнитель | агент |
|---|---|

- [x] выполнено
- [ ] осталось

Блокеры: нет.
"""


class CheckOwnerInterfaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def _render(self, text: str) -> None:
        patcher = patch(
            "operations.scripts.documents.check.render_repository_project_status",
            return_value=text,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_missing_required_token_fails(self) -> None:
        self._render(_BASE.replace("Ваше действие сейчас", ""))
        result = check_owner_interface(self.root)
        self.assertFalse(result.ok)
        self.assertTrue(
            any("Ваше действие сейчас" in error for error in result.errors),
            result.errors,
        )

    def test_percentage_is_rejected(self) -> None:
        self._render(_BASE + "\nПрогресс: 50%")
        result = check_owner_interface(self.root)
        self.assertFalse(result.ok)
        self.assertTrue(
            any("процент" in error.lower() for error in result.errors),
            result.errors,
        )

    def test_internal_technical_detail_is_rejected(self) -> None:
        self._render(_BASE + "\nGit SHA: abc123")
        result = check_owner_interface(self.root)
        self.assertFalse(result.ok)
        self.assertTrue(
            any("Git SHA" in error for error in result.errors),
            result.errors,
        )

    def test_multiple_next_actor_sections_are_rejected(self) -> None:
        self._render(_BASE + "\n| Следующий исполнитель | владелец |")
        result = check_owner_interface(self.root)
        self.assertFalse(result.ok)
        self.assertTrue(
            any("одного следующего исполнителя" in error for error in result.errors),
            result.errors,
        )

    def test_valid_render_passes(self) -> None:
        self._render(_BASE)
        result = check_owner_interface(self.root)
        self.assertTrue(result.ok, result.errors)
