from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from operations.scripts.common.project import atomic_write, relative_posix
from operations.scripts.common.status_types import ChecklistItem, TaskItem, TasksReport, TestRef
from operations.scripts.documents.metadata import (
    load_document,
    metadata_list,
    require_unique_identifier,
)

GENERATED_HEADER = "<!-- generated file: do not edit manually -->"
TASK_ID_PATTERN = re.compile(r"^TASK_\d{3}$")
TEST_ID_PATTERN = re.compile(r"^TEST_\d{3}$")
TASK_STATES = {"planned", "in-progress", "blocked", "completed", "cancelled"}
TERMINAL_STATES = {"completed", "cancelled"}
ACTIVE_STATES = {"in-progress", "blocked"}
CHECKBOX = re.compile(r"(?m)^\s*-\s+\[([ xX])\]\s+(.+?)\s*$")
STATE_LABELS = {
    "planned": "запланирована",
    "in-progress": "выполняется",
    "blocked": "заблокирована",
    "completed": "выполнена",
    "cancelled": "отменена",
}
ACTOR_LABELS = {
    "owner": "владелец",
    "agent": "агент",
    "automation": "автоматика",
    "none": "—",
}


def _section(body: str, title: str) -> str:
    pattern = re.compile(rf"(?ms)^##\s+(?:\d+\.\s*)?{re.escape(title)}\s*$\n(.*?)(?=^##\s|\Z)")
    match = pattern.search(body)
    return match.group(1).strip() if match else ""


def _test_map(root: Path) -> dict[str, list[TestRef]]:
    result: dict[str, list[TestRef]] = {}
    for path in sorted((root / "work/tests").glob("test_*.md")):
        doc = load_document(path)
        test_id = str(doc.metadata.get("id", "")).strip()
        if not TEST_ID_PATTERN.fullmatch(test_id):
            continue
        for value in metadata_list(doc.metadata, "traces_to"):
            task_id = value.strip()
            if TASK_ID_PATTERN.fullmatch(task_id):
                result.setdefault(task_id, []).append(
                    {"id": test_id, "path": relative_posix(path, root)}
                )
    return result


def checklist_items(body: str) -> list[ChecklistItem]:
    plan = _section(body, "План выполнения")
    return [
        {"done": mark.lower() == "x", "text": text.strip()} for mark, text in CHECKBOX.findall(plan)
    ]


def _validate_task_sequence(items: list[TaskItem]) -> None:
    actual_ids = [str(item["id"]) for item in items]
    expected_ids = [f"TASK_{number:03d}" for number in range(1, len(items) + 1)]
    if actual_ids != expected_ids:
        raise ValueError(
            "Очередь TASK должна начинаться с TASK_001 и идти без пропусков: "
            f"ожидалось {', '.join(expected_ids)}, найдено {', '.join(actual_ids)}"
        )

    for position, item in enumerate(items):
        task_id = str(item["id"])
        expected_stem = f"work/tasks/task_{task_id.removeprefix('TASK_').lower()}"
        task_path = str(item["path"]).lower()
        if task_path != f"{expected_stem}.md" and not task_path.startswith(f"{expected_stem}_"):
            raise ValueError(f"{task_id}: имя файла должно начинаться с '{expected_stem}'")
        if position == 0:
            continue
        previous_id = str(items[position - 1]["id"])
        if previous_id not in item["depends_on"]:
            raise ValueError(
                f"{task_id}: очередь требует depends_on на непосредственно предыдущую {previous_id}"
            )

    active = [str(item["id"]) for item in items if item["work_state"] in ACTIVE_STATES]
    if len(active) > 1:
        raise ValueError(f"В очереди может быть только одна активная TASK: {', '.join(active)}")

    first_nonterminal_seen = False
    planned_seen = False
    for item in items:
        task_id = str(item["id"])
        state = str(item["work_state"])
        if state in TERMINAL_STATES:
            if first_nonterminal_seen:
                raise ValueError(
                    f"{task_id}: завершённые и отменённые TASK должны образовывать непрерывное начало очереди"
                )
            continue
        first_nonterminal_seen = True
        if state == "planned":
            planned_seen = True
        elif planned_seen:
            raise ValueError(f"{task_id}: активная TASK не может находиться после запланированной")


def collect_tasks(root: Path) -> TasksReport:
    tests = _test_map(root)
    items: list[TaskItem] = []
    task_paths: dict[str, str] = {}
    for path in sorted((root / "work/tasks").glob("task_*.md")):
        doc = load_document(path)
        relative = relative_posix(path, root)
        task_id = str(doc.metadata.get("id", "")).strip()
        work_state = str(doc.metadata.get("work_state", "")).strip().lower()
        if not TASK_ID_PATTERN.fullmatch(task_id) or work_state not in TASK_STATES:
            raise ValueError(f"{relative}: некорректная TASK")
        require_unique_identifier(task_paths, task_id, relative, label="TASK ID")
        if "next_actor" not in doc.metadata or "owner_action" not in doc.metadata:
            raise ValueError(f"{relative}: TASK требует next_actor и owner_action")
        if "owner_action_required" in doc.metadata:
            raise ValueError(
                f"{relative}: owner_action_required устарело; используйте owner_action"
            )
        blocker = str(doc.metadata.get("blocker", "")).strip()
        if work_state == "blocked" and not blocker:
            raise ValueError(f"{relative}: заблокированная TASK требует поле blocker")
        if work_state != "blocked" and blocker:
            raise ValueError(f"{relative}: поле blocker допустимо только для заблокированной TASK")
        checklist = checklist_items(doc.body)
        done = sum(bool(item["done"]) for item in checklist)
        raw_owner_action = doc.metadata.get("owner_action", "none")
        owner_action = (
            "none" if raw_owner_action is None else (str(raw_owner_action).strip() or "none")
        )
        items.append(
            {
                "id": task_id,
                "title": str(doc.metadata.get("title", "")).strip() or doc.title,
                "work_state": work_state,
                "version": str(doc.metadata.get("version", "")).strip(),
                "path": relative,
                "depends_on": [x.strip() for x in metadata_list(doc.metadata, "depends_on")],
                "traces_to": [x.strip() for x in metadata_list(doc.metadata, "traces_to")],
                "implements": [x.strip() for x in metadata_list(doc.metadata, "implements")],
                "component": str(doc.metadata.get("component", "")).strip().upper(),
                "allowed_paths": [
                    x.strip() for x in metadata_list(doc.metadata, "allowed_paths") if x.strip()
                ],
                "blocker": blocker,
                "tests": tests.get(task_id, []),
                "next_actor": str(doc.metadata.get("next_actor", "none")).strip().lower(),
                "owner_action": owner_action,
                "checklist": checklist,
                "steps_done": done,
                "steps_total": len(checklist),
                "steps_remaining": len(checklist) - done,
                "body": doc.body,
            }
        )
    known = {str(item["id"]) for item in items}
    for item in items:
        for dep in item["depends_on"]:
            if dep not in known or dep == item["id"]:
                raise ValueError(f"{item['id']}: некорректная зависимость '{dep}'")
    items.sort(key=lambda item: str(item["id"]))
    _validate_task_sequence(items)
    return {
        "count": len(items),
        "states": dict(Counter(str(item["work_state"]) for item in items)),
        "tasks": items,
    }


def select_current_task(items: list[TaskItem], milestone_id: str | None = None) -> TaskItem | None:
    candidates = [
        item
        for item in items
        if item["work_state"] not in TERMINAL_STATES
        and (
            milestone_id is None
            or milestone_id.lower() in {str(value).lower() for value in item["traces_to"]}
        )
    ]
    candidates.sort(key=lambda item: str(item["id"]))
    return candidates[0] if candidates else None


def _ids(values: list[str]) -> str:
    return "<br>".join(f"`{value}`" for value in values) if values else "—"


def render_task_index(root: Path, generated_date: str | None = None) -> str:
    state = collect_tasks(root)
    current = select_current_task(state["tasks"])
    if current:
        current_position = next(
            index
            for index, item in enumerate(state["tasks"], start=1)
            if item["id"] == current["id"]
        )
        actor = ACTOR_LABELS.get(str(current["next_actor"]), str(current["next_actor"]))
        owner_action = "нет" if current["owner_action"] == "none" else str(current["owner_action"])
        now_lines = [
            f"- **Текущая задача:** [`{current['id']}` — {current['title']}]"
            f"(work/tasks/{Path(str(current['path'])).name})",
            f"- **Положение в очереди:** `{current_position}` из `{state['count']}`",
            f"- **Сейчас действует:** {actor}",
            f"- **Действие владельца:** {owner_action}",
            f"- **Шаги:** выполнено `{current['steps_done']}`, осталось `{current['steps_remaining']}`",
        ]
        if current["blocker"]:
            now_lines.append(f"- **Причина блокировки:** {current['blocker']}")
        now = "\n".join(now_lines)
    else:
        now = (
            "Сейчас проектных TASK нет. Служебные изменения репозитория и правил управления "
            "в этот список не попадают. Текущий рубеж показан в [`project_status.md`](project_status.md)."
        )
    queue_rows = []
    relation_rows = []
    for position, item in enumerate(state["tasks"], start=1):
        evidence = (
            "<br>".join(
                f"[`{test['id']}`](work/tests/{Path(str(test['path'])).name})"
                for test in item["tests"]
            )
            or "—"
        )
        state_label = STATE_LABELS[str(item["work_state"])]
        if current and item["id"] == current["id"]:
            state_label += " — **текущая**"
        queue_rows.append(
            f"| `{position}` | [`{item['id']}` — {item['title']}](work/tasks/{Path(str(item['path'])).name}) | "
            f"{state_label} | `{item['steps_done']}` из `{item['steps_total']}` | "
            f"{ACTOR_LABELS.get(str(item['next_actor']), str(item['next_actor']))} |"
        )
        relation_rows.append(
            f"| `{item['id']}` | {_ids(item['depends_on'])} | "
            f"{_ids([x for x in item['traces_to'] if x.lower().startswith('m')])} | "
            f"{_ids(item['implements'])} | {evidence} |"
        )
    if queue_rows:
        queue = f"""| № | Задача | Состояние | Выполнено шагов | Следующий исполнитель |
|---|---|---|---|---|
{chr(10).join(queue_rows)}

## Технические связи

| Задача | Предыдущая задача | Этап | Реализует | Проверки |
|---|---|---|---|---|
{chr(10).join(relation_rows)}"""
    else:
        queue = (
            "Очередь пуста. Первая TASK появится перед началом конкретной работы по поставке "
            "продуктового результата."
        )

    if current:
        total_count = state["count"]
        current_position = next(
            index
            for index, item in enumerate(state["tasks"], start=1)
            if item["id"] == current["id"]
        )
        status = f"`{current_position}` из `{total_count}`"
    else:
        status = "—"

    metadata_table = f"""| Параметр | Значение |
|---|---|
| Статус очереди | {status} |
| Текущая задача | {f"[`{current['id']}` — {current['title']}](work/tasks/{Path(str(current['path'])).name})" if current else "—"} |
| Состояние | {STATE_LABELS.get(str(current["work_state"]), str(current["work_state"])) if current else "—"} |
| Следующий исполнитель | {ACTOR_LABELS.get(str(current["next_actor"]), str(current["next_actor"])) if current else "—"} |"""

    return f"""{GENERATED_HEADER}
---
id: task_index
type: generated_task_index
generation_state: generated
version: 1.0
---

# Проектные задачи

{metadata_table}

## Что делать сейчас

{now}

## Рабочая очередь

Задачи выполняются сверху вниз. Номер TASK является её постоянным местом в очереди.

{queue}
"""


def generate_task_index(root: Path, generated_date: str | None = None) -> bool:
    return atomic_write(root / "tasks.md", render_task_index(root, generated_date))
