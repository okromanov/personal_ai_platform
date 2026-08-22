"""Применить результаты requirement_wizard: создать все документы в репозитории."""

from __future__ import annotations

import re
from pathlib import Path

if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from operations.scripts.common.project import find_project_root, today_iso


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


def apply_requirements_to_specifications(root: Path, wizard_result: dict) -> list[str]:
    """Apply wizard results to specification files."""
    created = []
    br_data = wizard_result["br"]

    # 1. Добавить BR в business_requirements.md
    br_file = root / "specifications" / "business_requirements.md"
    br_num = _find_next_requirement_number(br_file, "BR")
    br_id = f"BR_{br_num:03d}"

    br_entry = f"""
<a id="br_{br_num:03d}"></a>
### {br_id} — {br_data["title"]}

- priority: `core`

{br_data["description"]}

"""

    if br_file.exists():
        content = br_file.read_text(encoding="utf-8")
        # Find last BR entry and insert after it
        content += br_entry
        br_file.write_text(content, encoding="utf-8")
        created.append("specifications/business_requirements.md (BR добавлено)")

    # 2. Добавить SYS в system_specification.md
    sys_file = root / "specifications" / "system_specification.md"
    sys_base_num = _find_next_requirement_number(sys_file, "SYS")

    sys_entries = ""
    for i, sys_req in enumerate(wizard_result["sys_requirements"]):
        sys_num = sys_base_num + i
        sys_id = f"SYS_{sys_num:03d}"
        sys_entries += f"""
<a id="sys_{sys_num:03d}"></a>
### {sys_id} — {sys_req["title"]}

{sys_req["description"]}

- traces_to: {br_id}

"""

    if sys_file.exists():
        content = sys_file.read_text(encoding="utf-8")
        content += sys_entries
        sys_file.write_text(content, encoding="utf-8")
        created.append(
            f"specifications/system_specification.md ({len(wizard_result['sys_requirements'])} SYS добавлено)"
        )

    # 3. Добавить THR и SEC_CTL в threat_model.md
    threat_file = root / "specifications" / "threat_model.md"
    threat_base_num = _find_next_requirement_number(threat_file, "THR")
    control_base_num = _find_next_requirement_number(threat_file, "SEC_CTL")

    threat_entries = ""
    for i, threat in enumerate(wizard_result["threats"]):
        threat_num = threat_base_num + i
        threat_id = f"THR_{threat_num:03d}"
        threat_entries += f"""
<a id="thr_{threat_num:03d}"></a>
## {threat_id} — {threat["title"]}

{threat["description"]}

- mitigated_by: SEC_CTL_TBD

"""

    control_entries = ""
    for i, control in enumerate(wizard_result["security_controls"]):
        control_num = control_base_num + i
        control_id = f"SEC_CTL_{control_num:03d}"
        control_entries += f"""
<a id="sec_ctl_{control_num:03d}"></a>
## {control_id} — {control["title"]}

{control["description"]}

- protects: {br_id}

"""

    if threat_file.exists():
        content = threat_file.read_text(encoding="utf-8")
        content += threat_entries + control_entries
        threat_file.write_text(content, encoding="utf-8")
        created.append(
            f"specifications/threat_model.md ({len(wizard_result['threats'])} THR + {len(wizard_result['security_controls'])} SEC_CTL)"
        )

    # 4. Добавить ARC в architecture_baseline.md
    arch_file = root / "specifications" / "architecture_baseline.md"
    arch_base_num = _find_next_requirement_number(arch_file, "ARC")

    arch_entries = ""
    for i, component in enumerate(wizard_result["architecture"]):
        arch_num = arch_base_num + i
        arch_id = f"ARC_{arch_num:03d}"
        arch_entries += f"""
<a id="arc_{arch_num:03d}"></a>
### {arch_id} — {component["title"]}

{component["description"]}

- Responsibility: {component["responsibility"]}
- traces_to: {br_id}

"""

    if arch_file.exists():
        content = arch_file.read_text(encoding="utf-8")
        content += arch_entries
        arch_file.write_text(content, encoding="utf-8")
        created.append(
            f"specifications/architecture_baseline.md ({len(wizard_result['architecture'])} ARC добавлено)"
        )

    return created


def apply_tests_and_tasks(root: Path, wizard_result: dict) -> list[str]:
    """Create TEST and TASK documents."""
    created = []
    date = today_iso()
    milestone = wizard_result.get("milestone", "m02")

    # Создать TEST документы
    test_dir = root / "work" / "tests"
    test_dir.mkdir(parents=True, exist_ok=True)

    for i, test in enumerate(wizard_result["tests"]):
        test_num = 5000 + i  # Начиная с 5000, чтобы не пересекаться с основными
        test_file = test_dir / f"test_{test_num:04d}.md"

        test_content = f"""---
id: TEST_{test_num:04d}
type: test
title: {test["title"]}
spec_state: current
execution: manual
version: 1.0
updated: {date}
verifies:
  - {test["verifies"]}
accepts:
  - {milestone}
---

# TEST_{test_num:04d} — {test["title"]}

## 1. Назначение

{test["description"]}

## 2. Что проверяется

Требование `{test["verifies"]}`.

## 3. Как выполнить

Опишите пошаговую процедуру проверки требования.

## 4. Критерий успеха

Требование работает согласно спецификации.

## 5. Результат

Записать результат проверки.
"""

        test_file.write_text(test_content, encoding="utf-8")
        created.append(f"work/tests/test_{test_num:04d}.md")

    # Создать TASK документы
    task_dir = root / "work" / "tasks"
    task_dir.mkdir(parents=True, exist_ok=True)

    for i, task in enumerate(wizard_result["tasks"]):
        task_num = 5000 + i
        task_file = task_dir / f"task_{task_num:04d}_{milestone}_component.md"

        task_content = f"""---
id: TASK_{task_num:04d}
type: task
title: {task["title"]}
work_state: planned
version: 1.0
updated: {date}
next_actor: agent
owner_action: none
allowed_paths:
  - src/**
  - tests/**
traces_to:
  - {milestone}
implements:
  - {task["implements"]}
---

# TASK_{task_num:04d} — {task["title"]}

## 1. Зачем это делаем

{task["description"]}

## 2. Результат

Компонент полностью реализован, протестирован и интегрирован.

## 3. Где мы сейчас

Компонент определён в спецификации архитектуры.

## 4. Что делать сейчас

### Агенту

1. Изучить требования компонента в architecture_baseline.md
2. Спроектировать реализацию
3. Реализовать функциональность
4. Написать тесты
5. Проверить интеграцию

## 5. План выполнения

- [ ] Изучить требования
- [ ] Спроектировать
- [ ] Реализовать
- [ ] Написать тесты
- [ ] Провести интеграцию

## 6. Состав

- `src/` — исходный код компонента
- `tests/` — тесты компонента

## 7. Готово когда

- ✅ Все шаги плана выполнены
- ✅ Локальные проверки успешны
- ✅ CI успешен
"""

        task_file.write_text(task_content, encoding="utf-8")
        created.append(f"work/tasks/task_{task_num:04d}_{milestone}_component.md")

    return created


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
    milestone_file.write_text(content, encoding="utf-8")


def apply_wizard_result(root: Path, wizard_result: dict) -> None:
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
    print("1. Запустить: python operations/scripts/documents/generate.py --all")
    print("2. Проверить: python operations/scripts/documents/check.py --all")
    print("3. Откомитить и пушить на GitHub")
    print("=" * 60)


if __name__ == "__main__":
    root = find_project_root(Path.cwd())

    # Здесь должен быть результат от wizard
    # В реальном использовании это будет вызываться из AGENTS.md
    print("❌ Используйте этот скрипт через requirement_wizard.py")
    print("   Запустите: python operations/scripts/requirements/requirement_wizard.py")
