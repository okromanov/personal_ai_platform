"""Автоматическое создание TASK документов для новых архитектурных компонентов."""

from __future__ import annotations

import re
from pathlib import Path

if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from operations.scripts.common.project import find_project_root, today_iso
from operations.scripts.quality.registry import load_quality_registry, profiles_for_milestone
from operations.scripts.status.generate_project_status import collect_milestones

RELATION_ID_PATTERN = re.compile(r"\b([A-Z]+(?:_[A-Z]+)*_\d{3})\b")


def _extract_components_with_targets(text: str, prefix: str) -> dict[str, set[str]]:
    """Отобразить ID компонента на множество требований из его traces_to/implements.

    Компонент попадает в состав этапа только через требование, на которое он
    ссылается: milestones.md намеренно не перечисляет ARC_*/INF_CMP_* в `состав`.
    """
    heading = re.compile(rf"^###\s+({prefix}_\d{{3}})\s+—.*$", re.MULTILINE)
    matches = list(heading.finditer(text))
    result: dict[str, set[str]] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        section = text[match.end() : end]
        relation = re.search(r"`(?:traces_to|implements)`:\s*(.+)", section)
        targets = set(RELATION_ID_PATTERN.findall(relation.group(1))) if relation else set()
        result[match.group(1)] = targets
    return result


def _extract_architecture_components(root: Path) -> dict[str, set[str]]:
    """ARC_CMP_* -> требования из его `traces_to`."""
    arch_file = root / "specifications" / "architecture_baseline.md"
    if not arch_file.exists():
        return {}
    return _extract_components_with_targets(arch_file.read_text(encoding="utf-8"), "ARC_CMP")


def _extract_infrastructure_components(root: Path) -> dict[str, set[str]]:
    """INF_CMP_* -> требования из его `implements`."""
    inf_file = root / "specifications" / "infrastructure_baseline.md"
    if not inf_file.exists():
        return {}
    return _extract_components_with_targets(inf_file.read_text(encoding="utf-8"), "INF_CMP")


def _find_next_task_number(root: Path) -> int:
    """Find next available TASK_XXX number."""
    numbers = []
    for task_file in (root / "work" / "tasks").glob("task_*.md"):
        match = re.search(r"^id:\s*TASK_(\d+)", task_file.read_text(encoding="utf-8"), re.MULTILINE)
        if match:
            numbers.append(int(match.group(1)))
    return max(numbers) + 1 if numbers else 1


def _last_task_id(root: Path) -> str | None:
    """ID последней TASK в очереди по номеру, для цепочки depends_on."""
    best: tuple[int, str] | None = None
    for task_file in (root / "work" / "tasks").glob("task_*.md"):
        match = re.search(r"^id:\s*(TASK_\d+)", task_file.read_text(encoding="utf-8"), re.MULTILINE)
        if not match:
            continue
        number = int(match.group(1).removeprefix("TASK_"))
        if best is None or number > best[0]:
            best = (number, match.group(1))
    return best[1] if best else None


def _extract_pending_components(root: Path) -> set[str]:
    """Component ID -> уже упомянут в title существующей TASK.

    Специально НЕ читает `implements`: TASK-заглушка не заявляет формальное
    `implements`, пока для компонента нет ни одного TEST с `verifies` —
    acceptance_model требует эту пару одновременно, а честно завести TEST
    раньше реализации нельзя (нет automated_evidence/manual_evidence).
    Название заголовка — единственный безопасный способ отследить, что
    заглушка на компонент уже создана, не делая при этом формальную заявку.
    """
    covered: set[str] = set()
    for task_file in (root / "work" / "tasks").glob("task_*.md"):
        front_matter = task_file.read_text(encoding="utf-8").split("\n---", 1)[0]
        match = re.search(r"(?m)^title:\s*Реализация\s+(\S+)\s*$", front_matter)
        if match:
            covered.add(match.group(1))
    return covered


def _generate_task_document(
    task_number: int,
    component_id: str,
    milestone: str,
    depends_on: str | None,
    task_path: str,
) -> str:
    """Generate TASK document content.

    `allowed_paths` намеренно ограничен собственным файлом TASK (точным путём,
    не маской): реальный путь реализации не определён ни одним ADR на момент
    авто-генерации, и придумывать его здесь означало бы предрешать
    архитектурное решение вместо владельца/агента, которые примут его при
    фактическом начале работы над TASK.

    TASK сразу называет собственный component и включает его в `implements`.
    До атомарного старта этапа агент обязан связать эту карточку с TEST,
    проверяющим требования из канонической цепочки компонента.
    """
    date = today_iso()
    depends_lines = f"  - {depends_on}\n" if depends_on else ""

    return f"""---
id: TASK_{task_number:03d}
type: task
title: Реализация {component_id}
component: {component_id}
work_state: planned
version: 1.0
updated: {date}
next_actor: agent
owner_action: none
depends_on:
{depends_lines}allowed_paths:
  - {task_path}
traces_to:
  - {milestone}
implements:
  - {component_id}
---

# TASK_{task_number:03d} — Реализация {component_id}

## 1. Зачем это делаем

Реализовать компонент `{component_id}` согласно спецификации архитектуры.

## 2. Результат

Компонент `{component_id}` полностью реализован, протестирован и интегрирован.

## 3. Где мы сейчас

Компонент определён в спецификации, но не реализован. `allowed_paths` намеренно
сужен до собственного файла TASK: перед началом работы агент обязан явно
дополнить `allowed_paths` реальными путями реализации, а не полагаться на
угаданный заранее каталог.

## 4. Что делать сейчас

### Агенту

1. Изучить спецификацию `{component_id}` в соответствующем документе
2. Дополнить `allowed_paths` фактическими путями реализации
3. Создать план реализации
4. Реализовать функциональность и написать TEST с реальным evidence
5. Связать TASK с TEST, который проверяет требования компонента
6. Проверить интеграцию

## 5. План выполнения

- [ ] Изучить требования к {component_id}
- [ ] Дополнить allowed_paths реальными путями
- [ ] Спроектировать реализацию
- [ ] Реализовать компонент
- [ ] Написать TEST, связанный с TASK и требованиями компонента
- [ ] Проверить покрытие путей в allowed_paths

## 6. Состав

Затрагиваемые пути определяются при начале работы и фиксируются в `allowed_paths`.

## 7. Проверки и доказательства

Автоматическая проверка подтверждает, что все изменённые пути входят в `allowed_paths`.

## 8. Готово когда

- ✅ Все шаги плана выполнены
- ✅ Локальные проверки успешны
- ✅ CI успешен
- ✅ Код review завершен

## 9. Что будет дальше

После завершения этой TASK перейти к следующему компоненту или интеграционным испытаниям.

## 10. Что это даёт владельцу

Функционал появится после завершения этой TASK.
"""


def auto_generate_tasks(root: Path) -> list[str]:
    """Generate missing TASK documents for architecture/infrastructure components.

    Генерация допустима для первого незавершённого этапа после создания его
    профиля качества. Это позволяет подготовить TASK и TEST до атомарного
    перехода `planned → in-progress`.
    Компонент попадает в выдачу только если хотя бы одно его целевое требование
    входит в объявленный `состав` этапа — иначе создавались бы задачи на весь
    оставшийся бэклог продукта разом, а не на периметр текущего этапа.
    """
    created: list[str] = []

    milestone_state = collect_milestones(root)
    raw_current = milestone_state["current"]
    if not isinstance(raw_current, dict):
        return created
    current = raw_current
    current_id = str(current["id"])
    if current_id == "m01" or str(current["work_state"]) not in {"planned", "in-progress"}:
        return created
    if str(current["work_state"]) == "planned":
        try:
            if not profiles_for_milestone(load_quality_registry(root), current_id):
                return created
        except (OSError, ValueError):
            return created

    scope = {str(value) for value in current.get("scope", [])}
    if not scope:
        return created

    arc_components = _extract_architecture_components(root)
    inf_components = _extract_infrastructure_components(root)
    already_covered = _extract_pending_components(root)

    next_task_num = _find_next_task_number(root)
    depends_on = _last_task_id(root)

    in_scope: list[str] = [
        component_id
        for component_id, targets in {**arc_components, **inf_components}.items()
        if targets & scope and component_id not in already_covered
    ]

    for component_id in sorted(in_scope):
        task_num = next_task_num
        prefix = "arc" if component_id.startswith("ARC_") else "inf"
        suffix = component_id.rsplit("_", 1)[-1].lower()
        task_path = f"work/tasks/task_{task_num:03d}_{prefix}_{suffix}.md"
        content = _generate_task_document(task_num, component_id, current_id, depends_on, task_path)
        task_file = root / task_path

        task_file.write_text(content, encoding="utf-8")
        created.append(task_file.relative_to(root).as_posix())
        depends_on = f"TASK_{task_num:03d}"
        next_task_num += 1

    return created


if __name__ == "__main__":
    root = find_project_root(Path.cwd())
    created = auto_generate_tasks(root)
    if created:
        print("Созданы TASK документы:")
        for path in created:
            print(f"  + {path}")
    else:
        print("Все компоненты уже имеют TASK документы либо этап не in-progress.")
