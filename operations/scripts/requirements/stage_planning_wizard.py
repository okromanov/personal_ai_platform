"""Интерактивный wizard для планирования следующего этапа проекта."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from operations.scripts.common.project import find_project_root
from operations.scripts.status.generate_project_status import collect_milestones


@dataclass
class StageContext:
    """Контекст для планирования нового этапа."""

    current_stage: str  # "m01", "m02", etc
    next_stage: str  # "m02", "m03", etc
    focus_areas: list[str]  # ["integration", "storage", "ui", etc]
    key_features: list[str]  # High-level features for the stage
    dependencies: list[str]  # External systems, libraries
    risk_areas: list[str]  # Known risks to address
    success_criteria: list[str]  # How to measure success


STAGE_DESCRIPTIONS = {
    "m01": "Фундамент — документы, правила, автоматизация",
    "m02": "V1 инкремент 1 — основная функциональность",
    "m03": "V1 инкремент 2 — интеграции и расширения",
    "m04": "V1 инкремент 3 — масштабирование и оптимизация",
    "m05": "V1 инкремент 4 — безопасность и надёжность",
    "m06": "V1 инкремент 5 — deployment и production-ready",
    "m07": "V2 инкремент 1 — новые возможности",
}

AREA_TEMPLATES = {
    "integration": {
        "description": "Интеграции с внешними сервисами",
        "typical_features": ["API подключение", "Webhook обработка", "Синхронизация данных"],
        "risks": ["Недоступность сервиса", "Rate limiting", "Authentication issues"],
    },
    "storage": {
        "description": "Хранение и управление данными",
        "typical_features": ["База данных", "Кэширование", "Резервное копирование"],
        "risks": ["Потеря данных", "Производительность при масштабировании", "Data consistency"],
    },
    "ui": {
        "description": "Пользовательский интерфейс",
        "typical_features": ["Web interface", "Mobile support", "Real-time updates"],
        "risks": ["Производительность", "Cross-browser compatibility", "Accessibility"],
    },
    "automation": {
        "description": "Автоматизация процессов",
        "typical_features": ["Task scheduling", "Workflow orchestration", "Error handling"],
        "risks": ["Бесконечные циклы", "Ресурс consumption", "Debugging complexity"],
    },
    "security": {
        "description": "Безопасность и protection",
        "typical_features": ["Authentication", "Authorization", "Audit logging"],
        "risks": ["Privilege escalation", "Data breaches", "Compliance violations"],
    },
}


def _ask_question(question: str, question_type: str = "text") -> Any:
    """Ask user a question and return the answer."""
    print(f"\n❓ {question}")

    if question_type == "text":
        return input("→ ").strip()
    elif question_type == "multiline":
        print("   (Введите текст, затем пустую строку для завершения)")
        lines = []
        while True:
            line = input("→ ").strip()
            if not line:
                break
            lines.append(line)
        return "\n".join(lines)
    elif question_type == "list":
        print("   (Через запятую, или Enter для пропуска)")
        return [x.strip() for x in input("→ ").split(",") if x.strip()]
    elif question_type == "checkbox":
        print("   (Несколько вариантов, через пробел: 0 1 2 / через запятую: a, b, c)")
        return [x.strip() for x in input("→ ").replace(",", " ").split() if x.strip()]

    return ""


def _get_next_stage(root: Path) -> tuple[str, str]:
    """Get current and next stage from milestones."""
    milestone_state = collect_milestones(root)
    current_id = str(milestone_state.get("current", {}).get("id", "m01"))

    # Calculate next stage
    match = re.match(r"m(\d+)", current_id)
    if match:
        num = int(match.group(1)) + 1
        next_id = f"m{num:02d}"
    else:
        next_id = "m02"

    return current_id, next_id


def collect_stage_info(root: Path) -> StageContext:
    """Collect information for planning the next stage."""

    print("\n" + "=" * 60)
    print("🎯 WIZARD: Планирование следующего инкремента")
    print("=" * 60)

    # Get current and next stages
    current_stage, next_stage = _get_next_stage(root)
    current_desc = STAGE_DESCRIPTIONS.get(current_stage, current_stage)
    next_desc = STAGE_DESCRIPTIONS.get(next_stage, f"Этап {next_stage}")

    print(f"\n📍 Текущий этап: `{current_stage}` — {current_desc}")
    print(f"📍 Следующий этап: `{next_stage}` — {next_desc}")

    # Check if we're completing V1 (m06 → m07)
    if current_stage == "m06":
        print("\n🎉 ВАЖНО: Вы завершаете V1!")
        print("   Этапы m02-m06 составляют первую версию проекта.")
        print("   После этого начнётся планирование V2 (следующей версии).")
        print("   Этот wizard поможет определить состав V2 и первого инкремента `m07`.")

    # 1. Выбор областей фокуса
    print("\n📋 ШАГ 1: Области фокуса для этапа `{}`".format(next_stage))
    print("   Выберите 1-3 основные области:")
    print("   0. integration — Интеграции с внешними сервисами")
    print("   1. storage — Хранение и управление данными")
    print("   2. ui — Пользовательский интерфейс")
    print("   3. automation — Автоматизация процессов")
    print("   4. security — Безопасность и protection")

    selected_indices = _ask_question(
        "Выберите номера (через пробел): 0 1 2 / или через запятую: integration, storage",
        "checkbox",
    )

    area_keys = ["integration", "storage", "ui", "automation", "security"]
    focus_areas = []

    for idx_str in selected_indices:
        try:
            idx = int(idx_str)
            if 0 <= idx < len(area_keys):
                focus_areas.append(area_keys[idx])
        except ValueError:
            # Попытка прямого имени области
            if idx_str in area_keys:
                focus_areas.append(idx_str)

    if not focus_areas:
        focus_areas = ["integration"]  # По умолчанию

    print(f"   ✅ Выбрано: {', '.join(focus_areas)}")

    # 2. Ключевые функции для этапа
    print(f"\n🎯 ШАГ 2: Ключевые функции для `{next_stage}`")
    print("   Какие основные функции или функциональности нужны?")
    print("   (Просто перечислите через запятую, например: API, WebUI, Notifications)")

    key_features = _ask_question("Основные функции:", "list")
    if not key_features:
        # Подсказать на основе выбранных областей
        typical = []
        for area in focus_areas:
            typical.extend(AREA_TEMPLATES[area]["typical_features"][:2])
        print(f"   Подсказка: {', '.join(typical)}")
        key_features = _ask_question("Основные функции (повторно):", "list")

    # 3. Зависимости и интеграции
    print(f"\n🔌 ШАГ 3: Внешние системы и зависимости для `{next_stage}`")
    print("   (Telegram, GitHub, PostgreSQL, Redis, и т.д.)")

    dependencies = _ask_question("Внешние системы и библиотеки:", "list")

    # 4. Области риска
    print(f"\n⚠️  ШАГ 4: Потенциальные риски для `{next_stage}`")
    print("   Какие проблемы могут возникнуть?")
    print("   (Примеры: performance issues, data loss, security vulnerabilities)")

    risk_areas = _ask_question("Области риска:", "list")
    if not risk_areas:
        # Подсказать на основе выбранных областей
        typical_risks = []
        for area in focus_areas:
            typical_risks.extend(AREA_TEMPLATES[area]["risks"][:2])
        if typical_risks:
            print(f"   Подсказка: {', '.join(typical_risks)}")
            risk_areas = _ask_question("Области риска (повторно):", "list")

    # 5. Критерии успеха
    print(f"\n✅ ШАГ 5: Критерии успеха для `{next_stage}`")
    print("   Как понять, что этап выполнен успешно?")

    success_criteria = _ask_question("Критерии успеха:", "list")
    if not success_criteria:
        success_criteria = [
            "Все требования спецификации реализованы",
            "Прошли все тесты и проверки CI",
            "Документация актуальна",
        ]
        print(f"   По умолчанию: {success_criteria[0]}, и т.д.")

    context = StageContext(
        current_stage=current_stage,
        next_stage=next_stage,
        focus_areas=focus_areas,
        key_features=key_features,
        dependencies=dependencies,
        risk_areas=risk_areas,
        success_criteria=success_criteria,
    )

    # Подтверждение
    print("\n✅ Собранная информация:")
    print(f"   Текущий этап: {context.current_stage}")
    print(f"   Следующий этап: {context.next_stage}")
    print(f"   Области фокуса: {', '.join(context.focus_areas)}")
    print(f"   Ключевые функции: {len(context.key_features)} позиций")
    print(f"   Внешние системы: {len(context.dependencies)} позиций")
    print(f"   Области риска: {len(context.risk_areas)} позиций")
    print(f"   Критерии успеха: {len(context.success_criteria)} позиций")

    return context


def generate_stage_plan(context: StageContext) -> dict[str, Any]:
    """Generate stage composition plan from context."""

    print("\n🔄 Генерация плана этапа...")

    # Примерное количество требований на основе функций и зависимостей
    estimated_br_count = max(3, len(context.key_features) + len(context.dependencies) // 2)
    estimated_sys_count = estimated_br_count * 2
    estimated_threats = estimated_br_count * 3
    estimated_components = len(context.focus_areas) * 2

    result = {
        "stage": context.next_stage,
        "current_stage": context.current_stage,
        "focus_areas": context.focus_areas,
        "key_features": context.key_features,
        "dependencies": context.dependencies,
        "risk_areas": context.risk_areas,
        "success_criteria": context.success_criteria,
        "plan": {
            "estimated_br_count": estimated_br_count,
            "estimated_sys_count": estimated_sys_count,
            "estimated_threat_count": estimated_threats,
            "estimated_component_count": estimated_components,
            "estimated_test_count": estimated_br_count * 2,
            "estimated_task_count": estimated_components,
        },
        "composition_outline": {
            "business_requirements": [
                f"BR для: {', '.join(context.key_features[:3])}"
                if context.key_features
                else "Основная функция"
            ],
            "areas_to_cover": context.focus_areas,
            "external_integrations": context.dependencies,
            "security_measures": [
                risk for risk in context.risk_areas if "security" in risk.lower()
            ][:3],
        },
    }

    return result


def interactive_stage_planning_wizard(root: Path) -> dict[str, Any]:
    """Run interactive wizard and return stage plan."""

    context = collect_stage_info(root)
    plan = generate_stage_plan(context)

    print("\n" + "=" * 60)
    print("📊 ПЛАН ЭТАПА")
    print("=" * 60)
    print(f"\nЭтап: `{plan['stage'].upper()}`")
    print(f"Области фокуса: {', '.join(plan['focus_areas'])}")
    print("\nПредварительный состав:")
    print(f"  ~ {plan['plan']['estimated_br_count']} бизнес-требований (BR)")
    print(f"  ~ {plan['plan']['estimated_sys_count']} системных требований (SYS)")
    print(f"  ~ {plan['plan']['estimated_threat_count']} угроз/мер защиты (THR/SEC_CTL)")
    print(f"  ~ {plan['plan']['estimated_component_count']} архитектурных компонентов (ARC)")
    print(f"  ~ {plan['plan']['estimated_test_count']} тестов (TEST)")
    print(f"  ~ {plan['plan']['estimated_task_count']} рабочих задач (TASK)")

    print(f"\nОсновные функции: {', '.join(plan['key_features'][:5])}")
    if len(plan["key_features"]) > 5:
        print(f"  ...и ещё {len(plan['key_features']) - 5}")

    print(f"\nВнешние системы: {', '.join(plan['dependencies'][:5])}")
    if len(plan["dependencies"]) > 5:
        print(f"  ...и ещё {len(plan['dependencies']) - 5}")

    print("\n" + "=" * 60)
    print("🎯 СЛЕДУЮЩИЕ ШАГИ")
    print("=" * 60)
    print("1. Обсудить этот план с командой / владельцем")
    print(f"2. Создавать требования для `{plan['stage']}` через requirement_wizard.py")
    print("3. Использовать этот план как roadmap для эффективного добавления BR")
    print("=" * 60)

    return plan


if __name__ == "__main__":
    root = find_project_root(Path.cwd())
    plan = interactive_stage_planning_wizard(root)

    print("\n💾 План сохранён и готов к использованию.")
    print("   Начните добавлять требования через requirement_wizard.py")
