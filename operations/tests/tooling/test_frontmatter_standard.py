"""Negative paths for check_frontmatter_standard.

Found by a source-level mutation sweep (2026-09-02): emptying this check —
roughly a hundred lines enforcing per-type required frontmatter fields plus
the task and TEST conditional rules — left the whole suite green. It is one
of the six checks in the `--fast` profile, i.e. one of the few that every
commit passes through, so it is enforced far more often than it was covered.
"""

from __future__ import annotations

import tempfile
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from operations.scripts.documents.check import check_frontmatter_standard

TASK_FIELDS = """id: TASK_001
type: task
title: Пример задачи
work_state: active
version: 1.0
updated: 2026-09-02
depends_on:
  - system_specification
next_actor: agent
owner_action: none
allowed_paths:
  - src/
traces_to: SYS_001
"""


@contextmanager
def repo(**documents: str) -> Iterator[Path]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for relative, body in documents.items():
            path = root / relative.replace("__", "/")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
        yield root


def frontmatter(fields: str, body: str = "\nТекст.\n") -> str:
    return f"---\n{fields}---\n{body}"


class RequiredFieldTests(unittest.TestCase):
    def test_missing_required_field_for_a_known_type_is_reported(self) -> None:
        fields = "id: PR_001\ntype: project_rules\ndocument_state: current\nversion: 1.0\n"
        with repo(**{"operations__rules.md": frontmatter(fields)}) as root:
            result = check_frontmatter_standard(root)
        self.assertFalse(result.ok)
        joined = " ".join(result.errors)
        self.assertIn("updated", joined)
        self.assertIn("depends_on", joined)

    def test_complete_frontmatter_for_a_known_type_passes(self) -> None:
        fields = (
            "id: PR_001\ntype: project_rules\ndocument_state: current\n"
            "version: 1.0\nupdated: 2026-09-02\ndepends_on:\n  - agents\n"
        )
        with repo(**{"operations__rules.md": frontmatter(fields)}) as root:
            result = check_frontmatter_standard(root)
        self.assertEqual(result.errors, [])

    def test_unknown_type_is_not_constrained(self) -> None:
        with repo(**{"operations__note.md": frontmatter("id: N_001\ntype: scratch\n")}) as root:
            result = check_frontmatter_standard(root)
        self.assertEqual(result.errors, [])

    def test_templates_are_exempt(self) -> None:
        fields = "id: T_001\ntype: project_rules\n"
        with repo(**{"operations__templates__rules_template.md": frontmatter(fields)}) as root:
            result = check_frontmatter_standard(root)
        self.assertEqual(result.errors, [])


class TaskConditionalRuleTests(unittest.TestCase):
    def test_owner_next_actor_cannot_have_owner_action_none(self) -> None:
        fields = TASK_FIELDS.replace("next_actor: agent", "next_actor: owner")
        with repo(**{"work__tasks__task_001.md": frontmatter(fields)}) as root:
            result = check_frontmatter_standard(root)
        self.assertTrue(
            any("owner_action" in error for error in result.errors),
            result.errors,
        )

    def test_owner_next_actor_with_a_real_action_passes(self) -> None:
        fields = TASK_FIELDS.replace("next_actor: agent", "next_actor: owner").replace(
            "owner_action: none", "owner_action: review"
        )
        with repo(**{"work__tasks__task_001.md": frontmatter(fields)}) as root:
            result = check_frontmatter_standard(root)
        self.assertEqual(result.errors, [])

    def test_yaml_bare_none_is_recognised_as_no_owner_action(self) -> None:
        # Регрессия. Frontmatter здесь читается сырым: разбор превращает
        # `owner_action: none` в Python None, и сравнение str(...) == "none"
        # давало "None". Правило было мёртвым, хотя ровно эту форму и
        # используют все задачи в репозитории.
        fields = TASK_FIELDS.replace("next_actor: agent", "next_actor: owner")
        with repo(**{"work__tasks__task_001.md": frontmatter(fields)}) as root:
            errors = check_frontmatter_standard(root).errors
        self.assertTrue(any("owner_action" in error for error in errors), errors)

    def test_missing_owner_action_is_treated_as_none(self) -> None:
        fields = TASK_FIELDS.replace("next_actor: agent", "next_actor: owner").replace(
            "owner_action: none\n", ""
        )
        with repo(**{"work__tasks__task_001.md": frontmatter(fields)}) as root:
            errors = check_frontmatter_standard(root).errors
        self.assertTrue(any("owner_action" in error for error in errors), errors)

    def test_empty_allowed_paths_is_reported(self) -> None:
        fields = TASK_FIELDS.replace("allowed_paths:\n  - src/\n", "allowed_paths: []\n")
        with repo(**{"work__tasks__task_001.md": frontmatter(fields)}) as root:
            result = check_frontmatter_standard(root)
        self.assertTrue(
            any("allowed_paths" in error for error in result.errors),
            result.errors,
        )


class TestSpecConditionalRuleTests(unittest.TestCase):
    BASE = "id: TEST_001\ntype: test\nspec_state: current\nversion: 1.0\nupdated: 2026-09-02\n"

    def _errors(self, extra: str) -> list[str]:
        with repo(**{"work__tests__test_001.md": frontmatter(self.BASE + extra)}) as root:
            return check_frontmatter_standard(root).errors

    def test_automated_test_without_evidence_is_reported(self) -> None:
        errors = self._errors("execution: automated\n")
        self.assertTrue(any("automated_evidence" in error for error in errors), errors)

    def test_manual_test_without_evidence_is_reported(self) -> None:
        errors = self._errors("execution: manual\n")
        self.assertTrue(any("manual_evidence" in error for error in errors), errors)

    def test_automated_test_with_evidence_passes(self) -> None:
        self.assertEqual(
            self._errors("execution: automated\nautomated_evidence: runtime/test_output.txt\n"),
            [],
        )

    def test_blank_evidence_counts_as_missing(self) -> None:
        errors = self._errors("execution: manual\nmanual_evidence: '   '\n")
        self.assertTrue(any("manual_evidence" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
