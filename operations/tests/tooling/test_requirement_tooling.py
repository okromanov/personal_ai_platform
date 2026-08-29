from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from operations.scripts.requirements.apply_requirements import (
    _find_next_requirement_number,
    _format_yaml_multiline,
    apply_requirements_to_specifications,
    apply_tests_and_tasks,
    apply_wizard_result,
    update_milestones,
)
from operations.scripts.requirements.prompting import ask_question
from operations.scripts.requirements.requirement_wizard import (
    RequirementContext,
    collect_requirement_info,
    generate_architecture_components,
    generate_system_requirements,
    generate_task_documents,
    generate_test_documents,
    generate_threats_and_controls,
    interactive_requirement_wizard,
)
from operations.scripts.requirements.stage_planning_wizard import (
    StageContext,
    _get_next_stage,
    collect_stage_info,
    generate_stage_plan,
    interactive_stage_planning_wizard,
)


def requirement_context(**overrides: object) -> RequirementContext:
    values: dict[str, object] = {
        "milestone": "m02",
        "br_id": "BR_019",
        "br_title": "Telegram adapter",
        "br_description": "Process an authenticated update.",
        "category": "integration",
        "integrations": ["telegram", "model_api"],
        "data_types": ["message"],
        "security_level": "sensitive",
        "external_systems": ["telegram"],
        "performance_needs": ["realtime"],
        "arch_components": ["API Gateway", "Rate Limiter"],
        "potential_threats": [
            "Несанкционированный доступ через внешний сервис",
            "Утечка данных при передаче",
        ],
    }
    values.update(overrides)
    return RequirementContext(**values)  # type: ignore[arg-type]


def wizard_result() -> dict[str, object]:
    context = requirement_context(integrations=["telegram"], arch_components=["Gateway"])
    threats, controls = generate_threats_and_controls(context)
    return {
        "milestone": "m02",
        "br": {
            "id": context.br_id,
            "title": context.br_title,
            "description": context.br_description,
        },
        "sys_requirements": generate_system_requirements(context),
        "threats": threats,
        "security_controls": controls,
        "architecture": generate_architecture_components(context),
        "tests": generate_test_documents(context, 1),
        "tasks": generate_task_documents(context, 1),
    }


class SharedPromptingTests(unittest.TestCase):
    def test_supported_question_types_are_normalized(self) -> None:
        with patch("builtins.input", return_value="  answer  "):
            self.assertEqual(ask_question("Text"), "answer")
        with patch("builtins.input", side_effect=[" first ", "second", ""]):
            self.assertEqual(ask_question("Body", "multiline"), "first\nsecond")
        with patch("builtins.input", return_value=" alpha, , beta "):
            self.assertEqual(ask_question("Items", "list"), ["alpha", "beta"])
        with patch("builtins.input", return_value=" YES "):
            self.assertEqual(ask_question("Choice", "choice"), "yes")
        with patch("builtins.input", return_value="0, second  3"):
            self.assertEqual(ask_question("Checks", "checkbox"), ["0", "second", "3"])

    def test_unsupported_question_type_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported question type"):
            ask_question("Unknown", "unsupported")


class RequirementWizardTests(unittest.TestCase):
    def test_generators_create_complete_related_artifacts(self) -> None:
        context = requirement_context()

        systems = generate_system_requirements(context)
        threats, controls = generate_threats_and_controls(context)
        architecture = generate_architecture_components(context)
        tests = generate_test_documents(context, len(systems))
        tasks = generate_task_documents(context, len(architecture))

        self.assertEqual(len(systems), 4)
        self.assertEqual(len(threats), 2)
        self.assertGreaterEqual(len(controls), 6)
        self.assertEqual([row["id"] for row in architecture], ["ARC_001", "ARC_002"])
        self.assertEqual(len(tests), len(systems) + 1)
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[1]["implements"], "ARC_002")

    def test_context_uses_an_independent_acceptance_criteria_list(self) -> None:
        first = requirement_context()
        second = requirement_context()
        first.acceptance_criteria.append("first only")
        self.assertEqual(second.acceptance_criteria, [])

    def test_collect_requirement_info_normalizes_defaults(self) -> None:
        answers = iter(
            [
                "",
                "br_019",
                "Adapter",
                "Description",
                "Story",
                "unknown",
                ["telegram"],
                ["message"],
                "unknown",
                ["realtime"],
            ]
        )
        with patch(
            "operations.scripts.requirements.requirement_wizard._ask_question",
            side_effect=lambda *_args: next(answers),
        ):
            result = collect_requirement_info()

        self.assertEqual(result.milestone, "m02")
        self.assertEqual(result.br_id, "BR_019")
        self.assertEqual(result.category, "integration")
        self.assertEqual(result.security_level, "internal")

    def test_interactive_wizard_builds_summary(self) -> None:
        context = requirement_context()
        with patch(
            "operations.scripts.requirements.requirement_wizard.collect_requirement_info",
            return_value=context,
        ):
            result = interactive_requirement_wizard(Path("."))

        self.assertEqual(result["milestone"], "m02")
        self.assertEqual(result["summary"]["sys_count"], 4)
        self.assertEqual(result["summary"]["arch_count"], 2)


class StageWizardTests(unittest.TestCase):
    def test_get_next_stage_handles_current_and_invalid_ids(self) -> None:
        with patch(
            "operations.scripts.requirements.stage_planning_wizard.collect_milestones",
            return_value={"current": {"id": "m06"}},
        ):
            self.assertEqual(_get_next_stage(Path(".")), ("m06", "m07"))
        with patch(
            "operations.scripts.requirements.stage_planning_wizard.collect_milestones",
            return_value={"current": {"id": "invalid"}},
        ):
            self.assertEqual(_get_next_stage(Path(".")), ("invalid", "m02"))

    def test_collect_stage_info_accepts_indices_names_and_defaults(self) -> None:
        answers = iter(
            [
                ["1", "security", "99"],
                [],
                ["Storage API"],
                ["postgres"],
                [],
                ["security boundary"],
                [],
            ]
        )
        with (
            patch(
                "operations.scripts.requirements.stage_planning_wizard._get_next_stage",
                return_value=("m06", "m07"),
            ),
            patch(
                "operations.scripts.requirements.stage_planning_wizard._ask_question",
                side_effect=lambda *_args: next(answers),
            ),
        ):
            context = collect_stage_info(Path("."))

        self.assertEqual(context.focus_areas, ["storage", "security"])
        self.assertEqual(context.key_features, ["Storage API"])
        self.assertEqual(len(context.success_criteria), 3)

    def test_stage_plan_and_interactive_report(self) -> None:
        context = StageContext(
            current_stage="m01",
            next_stage="m02",
            focus_areas=["integration", "security"],
            key_features=["one", "two", "three", "four", "five", "six"],
            dependencies=["a", "b", "c", "d", "e", "f"],
            risk_areas=["security boundary", "latency"],
            success_criteria=["tests pass"],
        )
        result = generate_stage_plan(context)
        self.assertEqual(result["plan"]["estimated_br_count"], 9)
        self.assertEqual(result["composition_outline"]["security_measures"], ["security boundary"])

        with patch(
            "operations.scripts.requirements.stage_planning_wizard.collect_stage_info",
            return_value=context,
        ):
            interactive = interactive_stage_planning_wizard(Path("."))
        self.assertEqual(interactive["stage"], "m02")


class ApplyRequirementsTests(unittest.TestCase):
    @staticmethod
    def _install_contracts(root: Path) -> None:
        source_root = Path(__file__).resolve().parents[3]
        (root / "operations/templates").mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_root / "operations/template_registry.json", root / "operations")
        shutil.copy2(source_root / "operations/quality_registry.json", root / "operations")
        for name in (
            "architecture_component_template.md",
            "business_requirement_template.md",
            "security_control_template.md",
            "system_requirement_template.md",
            "task_template.md",
            "test_template.md",
            "threat_template.md",
        ):
            shutil.copy2(source_root / "operations/templates" / name, root / "operations/templates")

    def test_number_and_yaml_helpers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "spec.md"
            self.assertEqual(_find_next_requirement_number(path, "BR"), 1)
            path.write_text("BR_001 BR_009", encoding="utf-8")
            self.assertEqual(_find_next_requirement_number(path, "BR"), 10)
        self.assertEqual(_format_yaml_multiline("one"), '"one"')
        self.assertEqual(_format_yaml_multiline("one\ntwo", 2), "|\n    one\n    two")

    def test_apply_writes_specifications_tests_tasks_and_milestone(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._install_contracts(root)
            specs = root / "specifications"
            specs.mkdir()
            (specs / "business_requirements.md").write_text("BR_018\n", encoding="utf-8")
            (specs / "system_specification.md").write_text("SYS_036\n", encoding="utf-8")
            (specs / "threat_model.md").write_text("THR_020 SEC_CTL_020\n", encoding="utf-8")
            (specs / "architecture_baseline.md").write_text("ARC_020\n", encoding="utf-8")
            (root / "milestones.md").write_text(
                "## M02 — Increment\n\nсостав: `BR_001`\n", encoding="utf-8"
            )

            result = wizard_result()
            spec_changes = apply_requirements_to_specifications(root, result)
            created = apply_tests_and_tasks(root, result)
            update_milestones(root, result, "BR_019")

            self.assertEqual(len(spec_changes), 4)
            tests = result["tests"]
            tasks = result["tasks"]
            self.assertIsInstance(tests, list)
            self.assertIsInstance(tasks, list)
            assert isinstance(tests, list)
            assert isinstance(tasks, list)
            self.assertEqual(len(created), len(tests) + len(tasks))
            self.assertIn("BR_019", (specs / "business_requirements.md").read_text("utf-8"))
            self.assertIn("SYS_037", (specs / "system_specification.md").read_text("utf-8"))
            self.assertIn("`BR_019`", (root / "milestones.md").read_text("utf-8"))

    def test_missing_optional_specifications_are_not_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(apply_requirements_to_specifications(root, wizard_result()), [])

    def test_apply_wizard_result_reports_the_complete_operation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "specifications").mkdir()
            (root / "milestones.md").write_text("", encoding="utf-8")
            with (
                patch(
                    "operations.scripts.requirements.apply_requirements.apply_requirements_to_specifications",
                    return_value=["spec"],
                ) as apply_specs,
                patch(
                    "operations.scripts.requirements.apply_requirements.apply_tests_and_tasks",
                    return_value=["test", "task"],
                ) as apply_work,
                patch(
                    "operations.scripts.requirements.apply_requirements.update_milestones"
                ) as update_milestones,
            ):
                result = apply_wizard_result(root, wizard_result())

            self.assertEqual(result, ["spec", "test", "task", "milestones.md"])
            apply_specs.assert_called_once()
            apply_work.assert_called_once()
            update_milestones.assert_called_once()


if __name__ == "__main__":
    unittest.main()
