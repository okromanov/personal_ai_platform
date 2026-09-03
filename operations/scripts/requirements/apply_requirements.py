"""Применить результаты requirement_wizard: создать все документы в репозитории."""

from __future__ import annotations

import re
from pathlib import Path

if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from operations.scripts.common.project import find_project_root, today_iso
from operations.scripts.documents.template_contracts import (
    assert_registered_output,
    render_contract,
)
from operations.scripts.quality.registry import load_quality_registry


def _find_next_requirement_number(spec_file: Path, prefix: str) -> int:
    """Find next available number for a requirement type."""
    if not spec_file.exists():
        return 1

    content = spec_file.read_text(encoding="utf-8")
    numbers = [int(m.group(1)) for m in re.finditer(rf"\b{prefix}_(\d+)\b", content)]

    return max(numbers) + 1 if numbers else 1


def _format_yaml_multiline(text: str, indent: int = 0) -> str:
    """Format text for YAML multiline string."""
    lines = text.split("\n")
    prefix = " " * indent
    if len(lines) == 1:
        return f'"{lines[0]}"'
    return "|\n" + "\n".join(f"{prefix}  {line}" for line in lines)


def _next_card_number(directory: Path, prefix: str) -> int:
    numbers = [
        int(match.group(1))
        for path in directory.glob(f"{prefix.lower()}_*.md")
        if (match := re.match(rf"{prefix.lower()}_(\d{{3}})", path.name))
    ]
    return max(numbers, default=0) + 1


def apply_requirements_to_specifications(root: Path, wizard_result: dict) -> list[str]:
    """Append specification fragments rendered from protected templates."""
    created: list[str] = []
    br_data = wizard_result["br"]
    specification_paths = (
        root / "specifications/business_requirements.md",
        root / "specifications/system_specification.md",
        root / "specifications/threat_model.md",
        root / "specifications/architecture_baseline.md",
    )
    if not any(path.exists() for path in specification_paths):
        return []

    br_file = root / "specifications" / "business_requirements.md"
    br_num = _find_next_requirement_number(br_file, "BR")
    br_id = f"BR_{br_num:03d}"
    if br_file.exists():
        fragment = render_contract(
            root,
            "business_requirement",
            {
                "anchor": br_id.lower(),
                "requirement_id": br_id,
                "title": br_data["title"],
                "priority": "core",
                "description": br_data["description"],
            },
        )
        assert_registered_output(root, "business_requirement", br_file)
        br_file.write_text(
            br_file.read_text(encoding="utf-8").rstrip() + "\n\n" + fragment,
            encoding="utf-8",
        )
        created.append("specifications/business_requirements.md (BR добавлено)")

    sys_file = root / "specifications" / "system_specification.md"
    sys_base_num = _find_next_requirement_number(sys_file, "SYS")
    sys_ids: list[str] = []
    sys_fragments: list[str] = []
    for i, sys_req in enumerate(wizard_result["sys_requirements"]):
        sys_num = sys_base_num + i
        sys_id = f"SYS_{sys_num:03d}"
        sys_ids.append(sys_id)
        sys_req["id"] = sys_id
        sys_fragments.append(
            render_contract(
                root,
                "system_requirement",
                {
                    "anchor": sys_id.lower(),
                    "requirement_id": sys_id,
                    "title": sys_req["title"],
                    "traces_to": f"[`{br_id}`](business_requirements.md#{br_id.lower()})",
                    "requirement": sys_req["description"],
                    "observed_result": sys_req["description"],
                },
            )
        )

    threat_file = root / "specifications" / "threat_model.md"
    threat_base_num = _find_next_requirement_number(threat_file, "THR")
    control_base_num = _find_next_requirement_number(sys_file, "SEC_CTL")
    old_to_new_threat: dict[str, str] = {}
    for index, threat in enumerate(wizard_result["threats"]):
        old_to_new_threat[str(threat["id"])] = f"THR_{threat_base_num + index:03d}"

    control_fragments: list[str] = []
    controls_by_threat: dict[str, list[str]] = {}
    for i, control in enumerate(wizard_result["security_controls"]):
        control_num = control_base_num + i
        control_id = f"SEC_CTL_{control_num:03d}"
        old_threat_id = str(control.get("mitigates", ""))
        controls_by_threat.setdefault(old_threat_id, []).append(control_id)
        control["id"] = control_id
        control_fragments.append(
            render_contract(
                root,
                "security_control",
                {
                    "anchor": control_id.lower(),
                    "control_id": control_id,
                    "title": control["title"],
                    "traces_to": (
                        f"[`{sys_ids[0]}`](system_specification.md#{sys_ids[0].lower()})"
                        if sys_ids
                        else f"[`{br_id}`](business_requirements.md#{br_id.lower()})"
                    ),
                    "description": control["description"],
                },
            )
        )

    threat_fragments: list[str] = []
    for threat in wizard_result["threats"]:
        old_id = str(threat["id"])
        threat_id = old_to_new_threat[old_id]
        controls = controls_by_threat.get(old_id, [])
        if not controls:
            raise ValueError(f"{threat_id}: угроза не имеет связанного SEC_CTL")
        threat["id"] = threat_id
        links = ", ".join(
            f"[`{control_id}`](system_specification.md#{control_id.lower()})"
            for control_id in controls
        )
        threat_fragments.append(
            render_contract(
                root,
                "threat",
                {
                    "anchor": threat_id.lower(),
                    "threat_id": threat_id,
                    "title": threat["title"],
                    "mitigated_by": links,
                    "scenario": threat["description"],
                    "assets": f"Активы требования {br_id}.",
                    "consequence": "Нарушение требуемого поведения или конфиденциальности данных.",
                    "residual_risk": "Требуется проверка эффективности связанных мер защиты.",
                },
            )
        )

    if sys_file.exists():
        assert_registered_output(root, "system_requirement", sys_file)
        assert_registered_output(root, "security_control", sys_file)
        fragments = [*sys_fragments, *control_fragments]
        sys_file.write_text(
            sys_file.read_text(encoding="utf-8").rstrip() + "\n\n" + "\n".join(fragments),
            encoding="utf-8",
        )
        created.append(
            "specifications/system_specification.md "
            f"({len(sys_fragments)} SYS + {len(control_fragments)} SEC_CTL добавлено)"
        )
    if threat_file.exists():
        assert_registered_output(root, "threat", threat_file)
        threat_file.write_text(
            threat_file.read_text(encoding="utf-8").rstrip() + "\n\n" + "\n".join(threat_fragments),
            encoding="utf-8",
        )
        created.append(f"specifications/threat_model.md ({len(threat_fragments)} THR добавлено)")

    arch_file = root / "specifications" / "architecture_baseline.md"
    arch_base_num = _find_next_requirement_number(arch_file, "ARC_CMP")
    arch_fragments: list[str] = []
    for i, component in enumerate(wizard_result["architecture"]):
        arch_num = arch_base_num + i
        arch_id = f"ARC_CMP_{arch_num:03d}"
        component["id"] = arch_id
        if i < len(wizard_result["tasks"]):
            wizard_result["tasks"][i]["implements"] = arch_id
        arch_fragments.append(
            render_contract(
                root,
                "architecture_component",
                {
                    "anchor": arch_id.lower(),
                    "component_id": arch_id,
                    "title": component["title"],
                    "traces_to": f"[`{br_id}`](business_requirements.md#{br_id.lower()})",
                    "description": component["description"],
                    "responsibility": component["responsibility"],
                },
            )
        )

    if arch_file.exists():
        assert_registered_output(root, "architecture_component", arch_file)
        arch_file.write_text(
            arch_file.read_text(encoding="utf-8").rstrip() + "\n\n" + "\n".join(arch_fragments),
            encoding="utf-8",
        )
        created.append(
            f"specifications/architecture_baseline.md ({len(wizard_result['architecture'])} ARC добавлено)"
        )

    if sys_ids:
        for test in wizard_result["tests"]:
            if str(test.get("verifies", "")).startswith("SYS_"):
                test["verifies"] = sys_ids[0]

    return created


def apply_tests_and_tasks(root: Path, wizard_result: dict) -> list[str]:
    """Create TEST and TASK documents from protected registered templates."""
    task_created: list[str] = []
    test_created: list[str] = []
    date = today_iso()
    milestone = wizard_result.get("milestone", "m02")
    task_dir = root / "work" / "tasks"
    test_dir = root / "work" / "tests"
    task_dir.mkdir(parents=True, exist_ok=True)
    test_dir.mkdir(parents=True, exist_ok=True)

    tasks = wizard_result["tasks"]
    tests = wizard_result["tests"]
    if not tasks and tests:
        raise ValueError("TEST нельзя создать без связанной TASK")

    first_task_number = _next_card_number(task_dir, "task")
    existing_previous = f"TASK_{first_task_number - 1:03d}" if first_task_number > 1 else None
    task_ids = [f"TASK_{first_task_number + index:03d}" for index in range(len(tasks))]

    for index, task in enumerate(tasks):
        task_id = task_ids[index]
        task_number = first_task_number + index
        component = str(task["implements"])
        task_file = task_dir / f"task_{task_number:03d}_{milestone}_component.md"
        previous = task_ids[index - 1] if index else existing_previous
        task_content = render_contract(
            root,
            "task",
            {
                "task_id": task_id,
                "title": task["title"],
                "component": component,
                "delivery_role": "component",
                "updated": date,
                "depends_on_block": (
                    f"depends_on:\n  - {previous}" if previous else "depends_on: []"
                ),
                "task_path": task_file.relative_to(root).as_posix(),
                "milestone": milestone,
                "why": task["description"],
                "result": "Компонент полностью реализован, протестирован и интегрирован.",
                "current_state": "Компонент определён в спецификации архитектуры.",
                "agent_actions": "1. Уточнить фактические пути реализации\n2. Реализовать компонент и доказательство",
                "plan": "- [ ] Уточнить требования и allowed_paths\n- [ ] Реализовать компонент\n- [ ] Создать связанный TEST\n- [ ] Проверить результат",
                "scope": "Фактические пути поставки добавляются в `allowed_paths` перед реализацией.",
                "evidence": "Связанный TEST должен проверить требования компонента реальным evidence.",
                "done_when": "- ✅ План выполнен\n- ✅ Локальные и серверные проверки успешны",
                "next_step": "Перейти к следующей карточке очереди.",
                "owner_value": "Функционал появится после завершения этой TASK.",
                "owner_followups_block": "",
            },
        )
        assert_registered_output(root, "task", task_file)
        task_file.write_text(task_content, encoding="utf-8")
        task_created.append(task_file.relative_to(root).as_posix())

    catalog = load_quality_registry(root).get("evidence_catalog", {})
    evidence_ids = set(catalog) if isinstance(catalog, dict) else set()
    first_test_number = _next_card_number(test_dir, "test")
    for index, test in enumerate(tests):
        test_number = first_test_number + index
        test_id = f"TEST_{test_number:03d}"
        test_file = test_dir / f"test_{test_number:03d}.md"
        evidence_id = str(test.get("manual_evidence", f"{milestone}_e2e_tests"))
        if evidence_id not in evidence_ids:
            raise ValueError(f"TEST {test_id}: evidence {evidence_id} отсутствует в реестре")
        task_id = task_ids[min(index, len(task_ids) - 1)]
        test_content = render_contract(
            root,
            "test",
            {
                "test_id": test_id,
                "execution": "manual",
                "updated": date,
                "task_id": task_id,
                "verifies": test["verifies"],
                "milestone": milestone,
                "evidence_field": f"manual_evidence: {evidence_id}",
                "title": test["title"],
                "purpose": test["description"],
                "checked": f"Требование `{test['verifies']}`.",
                "execution_heading": "Действия владельца",
                "execution_steps": "Выполнить пользовательский сценарий без внутренних инструментов разработки.",
                "success": "Наблюдаемый результат соответствует спецификации.",
                "evidence_composition": "Структурированная запись результата с SHA, средой и временем проверки.",
            },
        )
        assert_registered_output(root, "test", test_file)
        test_file.write_text(test_content, encoding="utf-8")
        test_created.append(test_file.relative_to(root).as_posix())

    return [*test_created, *task_created]


def update_milestones(root: Path, wizard_result: dict, br_id: str) -> None:
    """Update milestones.md to include the new requirement in the specified stage."""
    milestone_file = root / "milestones.md"
    if not milestone_file.exists():
        return

    milestone = wizard_result.get("milestone", "m02")
    content = milestone_file.read_text(encoding="utf-8")

    # Find the milestone section and add BR to its состав
    pattern = rf"(## {milestone.upper()} —.*?\n.*?состав:.*?`)(.*?)(`\n)"

    def add_br_to_composition(match):
        prefix = match.group(1)
        composition = match.group(2)
        suffix = match.group(3)

        if br_id not in composition:
            # Add to the end of composition list
            composition = composition.rstrip() + f", `{br_id}`"

        return prefix + composition + suffix

    content = re.sub(pattern, add_br_to_composition, content, flags=re.DOTALL)
    assert_registered_output(root, "milestone", milestone_file)
    milestone_file.write_text(content, encoding="utf-8")


def apply_wizard_result(root: Path, wizard_result: dict) -> list[str]:
    """Apply all wizard results to the repository."""

    print("\n" + "=" * 60)
    print("📝 ПРИМЕНЕНИЕ РЕЗУЛЬТАТОВ")
    print("=" * 60)

    br_id = wizard_result["br"]["id"]
    spec_changes = apply_requirements_to_specifications(root, wizard_result)
    test_task_changes = apply_tests_and_tasks(root, wizard_result)

    # Update milestones.md to include new requirement
    update_milestones(root, wizard_result, br_id)

    print("\n✅ Созданы документы спецификации:")
    for change in spec_changes:
        print(f"   {change}")

    print("\n✅ Созданы TEST документы:")
    for change in test_task_changes[: len(wizard_result["tests"])]:
        print(f"   {change}")

    print("\n✅ Созданы TASK документы:")
    for change in test_task_changes[len(wizard_result["tests"]) :]:
        print(f"   {change}")

    print(f"\n✅ Обновлён milestones.md для этапа {wizard_result.get('milestone', 'm02').upper()}")

    print("\n" + "=" * 60)
    print("🎯 СЛЕДУЮЩИЕ ШАГИ:")
    print("=" * 60)
    print("1. Запустить: python3.12 operations/scripts/documents/generate.py --all")
    print("2. Проверить: python3.12 operations/scripts/documents/check.py --all")
    print("3. Откомитить и пушить на GitHub")
    print("=" * 60)
    return [*spec_changes, *test_task_changes, "milestones.md"]


if __name__ == "__main__":
    root = find_project_root(Path.cwd())

    # Здесь должен быть результат от wizard
    # В реальном использовании это будет вызываться из AGENTS.md
    print("❌ Используйте этот скрипт через requirement_wizard.py")
    print("   Запустите: python3.12 operations/scripts/requirements/requirement_wizard.py")
