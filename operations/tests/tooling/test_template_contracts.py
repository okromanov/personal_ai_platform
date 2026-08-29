from __future__ import annotations

import unittest
from pathlib import Path

from operations.scripts.documents.template_contracts import (
    TemplateContractError,
    assert_registered_output,
    render_contract,
    validate_template_registry,
)
from operations.scripts.status.human_status import render_repository_project_status

ROOT = Path(__file__).resolve().parents[3]


class TemplateContractTests(unittest.TestCase):
    def test_every_template_is_registered_and_resolvable(self) -> None:
        self.assertEqual(validate_template_registry(ROOT), [])

    def test_render_fails_closed_when_required_values_are_missing(self) -> None:
        with self.assertRaisesRegex(TemplateContractError, "не переданы значения"):
            render_contract(ROOT, "task", {})

    def test_output_outside_registered_contract_is_rejected(self) -> None:
        with self.assertRaisesRegex(TemplateContractError, "не разрешён реестром"):
            assert_registered_output(
                ROOT,
                "project_status",
                ROOT / "work" / "project_status_copy.md",
            )

    def test_general_generator_has_no_task_or_generated_side_effects(self) -> None:
        source = (ROOT / "operations/scripts/documents/generate.py").read_text(encoding="utf-8")
        self.assertNotIn("generate_task", source)
        self.assertNotIn('"generated/', source)
        self.assertNotIn("tasks.md", source)

    def test_task_contract_does_not_confirm_predecessor_as_plan_step(self) -> None:
        source = (ROOT / "operations/templates/task_template.md").read_text(encoding="utf-8")
        fenced = source.split("```markdown", 1)[1].split("```", 1)[0]
        self.assertNotIn("Подтвердить завершение", fenced)
        self.assertNotIn("предыдущей TASK", fenced)

    def test_owner_status_keeps_capability_and_dated_audit_sections(self) -> None:
        rendered = render_repository_project_status(ROOT)
        self.assertIn("Что уже умеет решение", rendered)
        self.assertIn("audit_baseline_2026_08_28.md", rendered)


if __name__ == "__main__":
    unittest.main()
