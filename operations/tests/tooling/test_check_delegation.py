"""Wiring tests for the check.py entries that only delegate.

Seven of the twenty-eight checks in `check.py` are one-liners around a
validator that lives in another module. Those validators have their own
unit tests, so a source-level mutation sweep (2026-09-02) that emptied each
check in turn found several of them UNDETECTED: nothing asserted that the
documentation audit still *calls* the validator, or that it publishes the
result under the name the profile lists. Unhooking one would have removed a
rule from the gate with the whole suite green.

These tests deliberately do not re-verify the validators' logic — that would
duplicate their own test modules. They pin two things only: the delegation
happens, and a validator that raises fails closed instead of passing silently.
"""

from __future__ import annotations

import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path
from unittest.mock import patch

from operations.scripts.documents import check as check_module
from operations.scripts.documents.check import CheckResult

SENTINEL = "sentinel error from the delegated validator"

# (имя проверки, функция-обёртка, путь для patch делегата)
# Ленивые импорты патчатся по модулю-источнику: обёртка импортирует символ в
# момент вызова, поэтому подмена атрибута в `check` до него не дошла бы.
DELEGATIONS: tuple[tuple[str, Callable[[Path], CheckResult], str], ...] = (
    (
        "full_traceability",
        check_module.check_full_traceability,
        "operations.scripts.documents.check.validate_full_traceability",
    ),
    (
        "adr_decision_tasks",
        check_module.check_adr_decision_tasks,
        "operations.scripts.documents.check.validate_adr_decision_tasks",
    ),
    (
        "semantic_consistency",
        check_module.check_semantic_consistency,
        "operations.scripts.documents.check.validate_semantic_consistency",
    ),
    (
        "test_coverage",
        check_module.check_test_coverage_quality,
        "operations.scripts.quality.test_coverage.validate_test_coverage",
    ),
    (
        "owner_actions",
        check_module.check_owner_action_quality,
        "operations.scripts.quality.action_practicality.check_project_status",
    ),
    (
        "allowed_paths",
        check_module.check_allowed_paths_quality,
        "operations.scripts.quality.paths_validation.validate_task_paths",
    ),
    (
        "links",
        lambda root: check_module._result("links", check_module.check_markdown_links(root)),
        "operations.scripts.documents.check.check_markdown_links",
    ),
)


class DelegationWiringTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def test_each_delegating_check_surfaces_the_validator_result(self) -> None:
        for name, checker, target in DELEGATIONS:
            with self.subTest(check=name):
                with patch(target, return_value=[SENTINEL]) as delegate:
                    result = checker(self.root)
                delegate.assert_called_once()
                self.assertEqual(result.name, name)
                self.assertFalse(result.ok)
                self.assertIn(SENTINEL, result.errors)

    def test_each_delegating_check_reports_a_clean_validator_as_ok(self) -> None:
        for name, checker, target in DELEGATIONS:
            with self.subTest(check=name):
                with patch(target, return_value=[]):
                    result = checker(self.root)
                self.assertEqual(result.name, name)
                self.assertTrue(result.ok)

    def test_quality_registry_delegates_with_the_milestone_ids(self) -> None:
        with patch(
            "operations.scripts.documents.check.collect_milestones",
            return_value={"items": [{"id": "M01"}, {"id": "m02"}]},
        ):
            with patch(
                "operations.scripts.documents.check.validate_quality_registry",
                return_value=[SENTINEL],
            ) as delegate:
                result = check_module.check_quality_registry(self.root)
        self.assertEqual(delegate.call_args.args[1], {"m01", "m02"})
        self.assertEqual(result.name, "quality_registry")
        self.assertIn(SENTINEL, result.errors)


class DelegationFailsClosedTests(unittest.TestCase):
    """A validator that raises must become a reported error, never silence.

    The three lazily-imported checks wrap their delegate in
    `except Exception`. That is the correct fail-closed shape, but an
    `except` that returned `[]` would look identical from the outside and
    would quietly drop the rule from the audit.
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def test_raising_validator_becomes_an_error_result(self) -> None:
        cases = (
            (
                "test_coverage",
                check_module.check_test_coverage_quality,
                "operations.scripts.quality.test_coverage.validate_test_coverage",
            ),
            (
                "owner_actions",
                check_module.check_owner_action_quality,
                "operations.scripts.quality.action_practicality.check_project_status",
            ),
            (
                "allowed_paths",
                check_module.check_allowed_paths_quality,
                "operations.scripts.quality.paths_validation.validate_task_paths",
            ),
        )
        for name, checker, target in cases:
            with self.subTest(check=name):
                with patch(target, side_effect=RuntimeError("boom")):
                    result = checker(self.root)
                self.assertEqual(result.name, name)
                self.assertFalse(result.ok, "исключение не должно давать зелёный результат")
                self.assertTrue(any("boom" in error for error in result.errors), result.errors)

    def test_unresolvable_milestones_fail_quality_registry_closed(self) -> None:
        with patch(
            "operations.scripts.documents.check.collect_milestones",
            side_effect=RuntimeError("no milestones"),
        ):
            result = check_module.check_quality_registry(self.root)
        self.assertFalse(result.ok)
        self.assertTrue(any("no milestones" in error for error in result.errors))


if __name__ == "__main__":
    unittest.main()
