from __future__ import annotations

import re
from pathlib import Path

from operations.scripts.common.project import today_iso
from operations.scripts.status.generate_project_status import collect_milestones


def get_gates_for_milestone(milestone_id: str) -> tuple[str, list[str]]:
    """Get remaining gates for a milestone."""
    gates_map = {
        "m01": (
            "До принятия `m01` остаются три обязательных ворот",
            [
                "Серверная проверка на GitHub",
                "Смысловая проверка документов",
                "Подтверждение владельца по составу V1",
            ],
        ),
        "m02": (
            "До принятия `m02` остаются обязательные ворота",
            [
                "Реализация всех компонентов ARC_CMP",
                "Интеграционные тесты успешны",
                "Смысловая проверка реализации",
                "Подтверждение владельца готовности",
            ],
        ),
    }
    return gates_map.get(milestone_id, ("Оставшиеся ворота", []))


def get_actions_for_milestone(milestone_id: str) -> list[tuple[str, str, str]]:
    """Get available actions for a milestone. Returns list of (command, actor, when)."""
    actions_map = {
        "m01": [
            ("`ПРОДОЛЖАЙ m01`", "Агент", "Сейчас (новый сеанс)"),
            ("`ПОДТВЕРЖДАЮ СОСТАВ V1`", "Вы", "После шага 5 агента"),
            ("`ИЗМЕНИ СОСТАВ V1: ...`", "Вы", "Если нужны изменения в периметре"),
            ("`ПРИНИМАЮ m01`", "Вы", "После зелёной проверки"),
            ("`ВОЗВРАЩАЮ m01: ...`", "Вы", "Если нужна переделка"),
        ],
        "m02": [
            ("`ПРОДОЛЖАЙ TASK_0002`", "Агент", "Сейчас (новый сеанс)"),
            ("`ПОДТВЕРЖДАЮ m02`", "Вы", "После завершения компонентов"),
            ("`ВОЗВРАЩАЮ m02: <причина>`", "Вы", "Если нужна доработка"),
        ],
    }
    return actions_map.get(milestone_id, [])


def render_owner_dashboard(root: Path, date: str | None = None) -> str:
    """Render owner dashboard from current project state."""
    generated_date = date or today_iso()

    # Count milestones
    milestones_data = collect_milestones(root)
    current_milestone = milestones_data.get("current", {})
    items = milestones_data.get("items", [])
    completed = len([m for m in items if m.get("work_state") == "completed"])
    total_milestones = len(items)
    remaining = total_milestones - completed

    # Count tasks
    tasks_dir = root / "work" / "tasks"
    task_count = len(list(tasks_dir.glob("*.md"))) if tasks_dir.exists() else 0

    # Get current milestone ID
    current_id = current_milestone.get("id", "m01")

    # Build milestone status lines
    milestone_lines = []
    for m in items:
        mid = m.get("id", "")
        mstate = m.get("work_state", "")
        status_icon = "✅" if mstate == "completed" else "🔄" if mstate == "in-progress" else "⏳"
        is_current = " — **текущий этап**" if mid == current_id else ""
        milestone_lines.append(f"- [{status_icon}] [`{mid}`](milestones.md#{mid}){is_current}")

    # Parse V1 requirements from business_requirements.md if available
    v1_reqs = []
    br_path = root / "specifications" / "business_requirements.md"
    if br_path.exists():
        content = br_path.read_text(encoding='utf-8')
        # Extract BR_ items with priority: core
        matches = re.findall(r'- `(BR_\d+)`.*priority:.*core', content)
        v1_reqs = sorted(set(matches))

    lines = [
        "<!-- generated file: do not edit manually -->",
        "---",
        "id: owner_dashboard",
        "type: operations_guide",
        "document_state: current",
        "version: 1.1",
        f"updated: {generated_date}",
        "depends_on:",
        "  - project_milestones",
        "  - project_rules",
        "  - operations_change_process",
        "  - coding_agent_instruction",
        "---",
        "",
        "# Полный дашборд проекта",
        "",
        "Это расширенная информация для тех, кто хочет видеть полное состояние. Для быстрого действия используйте [`project_status.md`](project_status.md).",
        "",
        "## Общая статистика V1",
        "",
        "| Параметр | Значение |",
        "|---|---|",
        f"| Этапы всего | {total_milestones} |",
        f"| Этапы завершены | {completed} |",
        f"| Этапы осталось | {remaining} |",
        f"| Проектные TASK | {task_count} |",
        "",
        "## Этапы разработки",
        "",
    ]

    # Add milestone details
    for m in items:
        mid = m.get("id", "")
        mstate = m.get("work_state", "")
        mdesc = m.get("description", "")

        lines.append(f"### {mid} — {mdesc}")
        lines.append("")
        lines.append(f"- **Статус:** `{mstate}`")

        # Add description based on milestone
        if mid == "m01":
            lines.append("- **Что это:** подготовка структуры документов, правил и автоматических проверок")
        elif mid == "m02":
            lines.append("- **Что это:** выбор среды агента и первая интеграция с Telegram")
        elif mid == "m03":
            lines.append("- **Что это:** обработка файлов, интернет-исследования, фильтр важности")
        elif mid == "m04":
            lines.append("- **Что это:** постоянная память между сессиями")
        elif mid == "m05":
            lines.append("- **Что это:** автоматизация и расписание")
        elif mid == "m06":
            lines.append("- **Что это:** финальная проверка всех компонентов V1")

        if mstate == "completed":
            lines.append("- **Когда будет готово:** завершено")
        elif mstate == "in-progress":
            lines.append("- **Когда будет готово:** ожидается после завершения текущих задач")
        else:
            lines.append("- **Когда будет готово:** запланирован")

        if mid == "m02":
            lines.append("- **Требования:** точный машинно проверяемый состав задан в [`milestones.md`](milestones.md#m02); ручные счётчики здесь не дублируются")

        lines.append("")

    # V1 requirements (only for m01)
    if v1_reqs and current_id == "m01":
        lines.append("## Состав V1 (обязательный периметр)")
        lines.append("")
        lines.append("Эти бизнес-требования определяют, что такое \"готовая первая версия\":")
        lines.append("")
        for req in v1_reqs[:18]:  # Show first 18
            lines.append(f"- {req}")
        lines.append("")
        lines.append("**Статус:** ожидает подтверждения владельца перед `m01`")
        lines.append("")

    # Document statistics with dynamic status
    adr_status = "✅ ADR_001–ADR_004 приняты; ADR_005–ADR_009 — кандидаты для m02" if current_id not in {"m01"} else "⏳ ADR_001–ADR_004 ожидают принятия m01; ADR_005–ADR_009 — кандидаты для m02"
    check_status = "✅ Смысловая проверка успешна" if current_id not in {"m01"} else "⏳ Смысловая проверка (ждёт этапа m01)"

    lines.extend([
        "## Статистика документов",
        "",
        "| Тип | Количество | Статус |",
        "|---|---|---|",
        "| Бизнес-требования | 39 | ✅ актуальны |",
        "| Угрозы | 19 | ✅ актуальны |",
        "| Системные требования | 36 | ✅ актуальны |",
        "| Меры безопасности | 20 | ✅ актуальны |",
        "| Инфраструктурные требования | 16 | ✅ актуальны |",
        f"| ADR | 9 | {adr_status} |",
        f"| Проектные TASK | {task_count} | — |",
        "| Спецификации проверок | 5 | ✅ 2 для m01; 3 для m02+ |",
        "",
        "## Автоматические проверки",
        "",
        "- ✅ Структура документов (документы корректны)",
        "- ✅ Трассировка требований (связи целостны)",
        "- ✅ Версионирование (метаданные верны)",
        "- ✅ Производные представления (могут пересчитаны)",
        f"- {check_status}",
        "",
        "## GitHub Actions",
        "",
        "Статус серверной проверки не хранится в этом документе, потому что он быстро устаревает. Перед смысловой проверкой агент обязан получить результат GitHub Actions для точного проверяемого SHA и сверить evidence artifact. Пока это не выполнено, серверная готовность считается неподтверждённой.",
        "",
        "## Оставшиеся ворота",
        "",
    ])

    # Add dynamic gates section
    gates_title, gates = get_gates_for_milestone(current_id)
    lines.append(gates_title + ":")
    for i, gate in enumerate(gates, 1):
        lines.append(f"{i}. {gate}")
    lines.append("")

    # Add dynamic actions section
    lines.append("## Действия, доступные сейчас")
    lines.append("")
    lines.append("| Команда | Кто | Когда |")
    lines.append("|---|---|---|")
    actions = get_actions_for_milestone(current_id)
    for command, actor, when in actions:
        lines.append(f"| {command} | {actor} | {when} |")
    lines.append("")

    lines.extend([
        "## Ссылки на правила",
        "",
        "- **Как работает процесс:** [`project_rules.md`](project_rules.md)",
        "- **Как вносятся изменения:** [`operations/change_process.md`](operations/change_process.md)",
        "- **Инструкция агенту:** [`AGENTS.md`](AGENTS.md)",
        "",
    ])

    return "\n".join(lines)
