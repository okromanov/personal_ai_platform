from __future__ import annotations

import json
import tempfile
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

    def test_output_pattern_cannot_cross_directory_boundary(self) -> None:
        with self.assertRaisesRegex(TemplateContractError, "не разрешён реестром"):
            assert_registered_output(
                ROOT,
                "task",
                ROOT / "work" / "tasks" / "nested" / "task_999.md",
            )

    def test_registry_rejects_unprotected_or_bypassing_generator(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            template = root / "operations/templates/example.md"
            generator = root / "operations/scripts/example.py"
            test_path = root / "operations/tests/test_contract.py"
            codeowners = root / ".github/CODEOWNERS"
            for path in (template, generator, test_path, codeowners):
                path.parent.mkdir(parents=True, exist_ok=True)
            template.write_text("```markdown\n{{value}}\n```\n", encoding="utf-8")
            generator.write_text("Path('output.md').write_text('bypass')\n", encoding="utf-8")
            test_path.write_text("# contract test\n", encoding="utf-8")
            codeowners.write_text(
                "/.github/CODEOWNERS @owner\n"
                "/operations/template_registry.json @owner\n"
                "/operations/templates/ @owner\n"
                "/operations/tests/test_contract.py @owner\n",
                encoding="utf-8",
            )
            registry = {
                "version": 1,
                "required_owner": "@owner",
                "protected_paths": [
                    ".github/CODEOWNERS",
                    "operations/template_registry.json",
                ],
                "enforcement_tests": ["operations/tests/test_contract.py"],
                "contracts": {
                    "example": {
                        "template": "operations/templates/example.md",
                        "outputs": ["output.md"],
                        "mode": "committed",
                        "generators": ["operations/scripts/example.py"],
                    }
                },
            }
            registry_path = root / "operations/template_registry.json"
            registry_path.write_text(json.dumps(registry), encoding="utf-8")

            errors = validate_template_registry(root)
            self.assertTrue(any("обходит contract API" in error for error in errors))
            self.assertTrue(any("CODEOWNERS не защищает" in error for error in errors))

            generator.write_text(
                "assert_registered_output(root, 'example', output)\n", encoding="utf-8"
            )
            with codeowners.open("a", encoding="utf-8") as stream:
                stream.write("/operations/scripts/example.py @owner\n")
            self.assertEqual(validate_template_registry(root), [])

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

    def test_owner_status_keeps_dated_audit_section(self) -> None:
        rendered = render_repository_project_status(ROOT)
        self.assertIn("audit_register.md", rendered)


if __name__ == "__main__":
    unittest.main()
