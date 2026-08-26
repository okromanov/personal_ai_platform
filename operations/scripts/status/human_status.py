from __future__ import annotations

import re
from pathlib import Path

from operations.scripts.common.project import atomic_write_generated, iter_files, relative_posix
from operations.scripts.common.status_types import TaskItem
from operations.scripts.documents.metadata import load_document
from operations.scripts.status.generate_project_status import (
    build_owner_next_action,
    collect_milestones,
    v1_milestone_ids,
)
from operations.scripts.tasks.generate import ACTOR_LABELS, collect_tasks, select_current_task

_LINK_TARGET_PATTERN = re.compile(r"(\[[^\]]*\]\()([^)]+)(\))")


def _rebase_relative_links(text: str, source_dir: Path, root: Path) -> str:
    """TASK bodies link to other repo files relative to their own directory
    (e.g. work/tasks/); this file inlines their prose verbatim at repo root,
    so those relative targets must be re-expressed relative to root or they
    point at the wrong place once copied here."""

    def repl(match: re.Match[str]) -> str:
        target = match.group(2).strip()
        if not target or target.startswith(("http://", "https://", "mailto:", "#")):
            return match.group(0)
        path_part, _, anchor = target.partition("#")
        resolved = (source_dir / path_part).resolve()
        try:
            rebased = resolved.relative_to(root.resolve())
        except ValueError:
            return match.group(0)
        new_target = rebased.as_posix() + (f"#{anchor}" if anchor else "")
        return f"{match.group(1)}{new_target}{match.group(3)}"

    return _LINK_TARGET_PATTERN.sub(repl, text)


def _section(body: str, title: str) -> str:
    pattern = re.compile(rf"(?ms)^##\s+(?:\d+\.\s*)?{re.escape(title)}\s*$\n(.*?)(?=^##\s|\Z)")
    match = pattern.search(body)
    return match.group(1).strip() if match else ""


def _open_followups(tasks: list[TaskItem]) -> list[tuple[TaskItem, str]]:
    """Every open, non-blocking `owner_followups` entry across all TASK cards.

    Independent of the current milestone/TASK in progress -- an open
    followup on an already-`completed` TASK still needs to surface here
    until the owner resolves it (see `operations/templates/task_template.md`).
    """
    return [
        (item, str(followup["action"]))
        for item in tasks
        for followup in item.get("owner_followups", [])
        if str(followup.get("status")) == "open"
    ]


def _linked_tasks(tasks: list[TaskItem], milestone_id: str) -> list[TaskItem]:
    return [
        item for item in tasks if milestone_id.lower() in {v.lower() for v in item["traces_to"]}
    ]


def _task_context(tasks: list[TaskItem], milestone_id: str) -> TaskItem | None:
    current = select_current_task(tasks, milestone_id)
    if current:
        return current
    linked = _linked_tasks(tasks, milestone_id)
    owner_decisions = [item for item in linked if item["owner_action"] != "none"]
    if owner_decisions:
        return sorted(owner_decisions, key=lambda item: item["id"])[-1]
    return sorted(linked, key=lambda item: item["id"])[-1] if linked else None


def _checkbox(done: bool) -> str:
    return "[x]" if done else "[ ]"


def _component_link(component: str) -> str:
    if component.startswith("ARC_"):
        return f"[`{component}`](specifications/architecture_baseline.md#{component.lower()})"
    if component.startswith("INF_"):
        return f"[`{component}`](specifications/infrastructure_baseline.md#{component.lower()})"
    return f"`{component}`"

def _technical_coverage(tasks: list[TaskItem], root: Path) -> str:
    """Build the component-to-evidence table from TASK and TEST metadata."""
    tests_by_task: dict[str, list[tuple[str, str]]] = {}
    for path in iter_files(root, suffixes={".md"}, include_generated=False):
        relative = relative_posix(path, root)
        if not relative.startswith("work/tests/"):
            continue
        document = load_document(path)
        test_id = str(document.metadata.get("id", ""))
        for task_id in document.metadata.get("traces_to", []):
            tests_by_task.setdefault(str(task_id), []).append((test_id, relative))

    labels = {"completed": "выполнена", "in-progress": "выполняется", "planned": "запланирована", "blocked": "заблокирована"}
    rows: list[str] = []
    for task in tasks:
        component = str(task.get("component", "—"))
        task_path = Path(str(task["path"])).name
        task_link = f"[`{task['id']}`](work/tasks/{task_path})"
        linked = tests_by_task.get(str(task["id"]), [])
        evidence = ", ".join(f"[`{test_id}`]({path})" for test_id, path in linked) or "—"
        state = labels.get(str(task.get("work_state", "")), str(task.get("work_state", "")))
        rows.append(f"| {task_link} | {_component_link(component)} | {evidence} | {state} |")
    return "\n".join(rows) or "| — | — | — | — |"


def render_repository_project_status(root: Path) -> str:
    milestone_state = collect_milestones(root)
    tasks = collect_tasks(root)["tasks"]
    v1_ids = set(v1_milestone_ids(root))
    milestones = [item for item in milestone_state["items"] if str(item["id"]) in v1_ids]
    completed_milestones = sum(str(item["work_state"]) == "completed" for item in milestones)
    remaining_milestones = len(milestones) - completed_milestones

    current = milestone_state["current"]
    current_id = str(current["id"])
    current_tasks = _linked_tasks(tasks, current_id)
    completed_tasks = sum(str(item["work_state"]) == "completed" for item in current_tasks)
    remaining_tasks = len(current_tasks) - completed_tasks
    all_tasks_completed = bool(current_tasks) and remaining_tasks == 0
    foundation_without_project_tasks = current_id == "m01" and not current_tasks
    current_task = _task_context(tasks, current_id)
    current_task_position = next(
        (
            position
            for position, item in enumerate(current_tasks, start=1)
            if current_task and item["id"] == current_task["id"]
        ),
        None,
    )
    queue_position = (
        f"**{current_task_position} из {len(current_tasks)}**"
        if current_task_position is not None
        else "—"
    )

    milestone_lines = "\n".join(
        f"- {_checkbox(str(item['work_state']) == 'completed')} "
        f"[`{item['id']}` — {item['title']}](milestones.md#{item['id']})"
        + (" — **текущий этап**" if item["id"] == current_id else "")
        for item in milestones
    )
    technical_coverage = _technical_coverage(current_tasks, root)

    if current_task:
        task_link = (
            f"[`{current_task['id']}` — {current_task['title']}]"
            f"(work/tasks/{Path(str(current_task['path'])).name})"
        )
        task_source_dir = root / Path(str(current_task["path"])).parent
        actor_key = str(current_task["next_actor"])
        actor = ACTOR_LABELS.get(actor_key, actor_key)
        if all_tasks_completed:
            actor = "агент после команды владельца"
        step_lines = (
            "\n".join(
                f"- {_checkbox(bool(item['done']))} "
                f"{_rebase_relative_links(str(item['text']), task_source_dir, root)}"
                for item in current_task["checklist"]
            )
            or "- [ ] План шагов ещё не заполнен."
        )
        steps_done = int(current_task["steps_done"])
        steps_remaining = int(current_task["steps_remaining"])
        next_text = (
            _rebase_relative_links(
                _section(str(current_task.get("body", "")), "Что будет дальше"),
                task_source_dir,
                root,
            )
            or "Следующий шаг будет определён после завершения текущей задачи."
        )
    else:
        task_link = "—"
        if foundation_without_project_tasks:
            actor = "агент после команды владельца"
            foundation_steps = [
                (
                    True,
                    "Подготовить структуру документов, правила и автоматические проверки основы.",
                ),
                (False, "Подтвердить успешную серверную проверку опубликованной редакции."),
                (False, "Провести независимую смысловую проверку этой же редакции."),
                (False, "Получить подтверждение владельца по составу V1."),
                (False, "Показать выбор: принять `m01` или вернуть его на доработку."),
            ]
            step_lines = "\n".join(f"- {_checkbox(done)} {text}" for done, text in foundation_steps)
            steps_done = sum(done for done, _ in foundation_steps)
            steps_remaining = len(foundation_steps) - steps_done
            next_text = (
                "После успешных технических и смысловых проверок агент покажет владельцу "
                "две точные команды по `m01`."
            )
        else:
            actor = "агент"
            step_lines = "- [ ] Создать проверяемый план первой проектной задачи."
            steps_done = 0
            steps_remaining = 1
            next_text = "После создания проектной задачи появится её проверяемый план."

    open_followups = _open_followups(tasks)
    if open_followups:
        followups_text = "\n".join(
            f"- [`{item['id']}`](work/tasks/{Path(str(item['path'])).name}): {action}"
            for item, action in open_followups
        )
    else:
        followups_text = "Нет незакрытых необязательных действий владельца."

    blockers = [item for item in current_tasks if str(item["work_state"]) == "blocked"]
    if blockers:
        blocker_text = "\n".join(
            f"- `{item['id']}` — {item['title']}. Причина: {item.get('blocker') or 'не указана'}"
            for item in blockers
        )
    elif all_tasks_completed or foundation_without_project_tasks:
        blocker_text = (
            "В проектных TASK блокеров нет. Перед решением агент подтвердит серверный результат "
            "и смысловую проверку опубликованной редакции."
        )
    else:
        blocker_text = (
            "В карточках задач блокеры не зафиксированы. Итоговую готовность проверит агент."
        )

    owner_is_next = bool(
        current_task
        and str(current_task["next_actor"]) == "owner"
        and str(current_task["owner_action"]) != "none"
    )
    if owner_is_next:
        assert current_task is not None
        next_action = build_owner_next_action(
            current_id,
            resume_target=current_id,
            requires_fresh_session=False,
            owner_action=str(current_task["owner_action"]),
        )
        owner_guidance = f"""> **Сейчас требуется ваше решение по этапу `{current_id}`.**

- [ ] {next_action["commands"][0]["label"]}: `{next_action["commands"][0]["value"]}`.
- [ ] {next_action["commands"][1]["label"]}: `{next_action["commands"][1]["value"]}`."""
    else:
        review_route = all_tasks_completed or foundation_without_project_tasks
        resume_target = current_id if review_route or not current_task else str(current_task["id"])
        next_action = build_owner_next_action(
            current_id,
            resume_target=resume_target,
            requires_fresh_session=review_route,
        )
        owner_guidance = f"""> **Чтобы продолжить, {next_action["instruction"].lower()}**
>
> `{next_action["commands"][0]["value"]}`"""

    # Build remaining work summary
    remaining_summary = ""
    if steps_remaining > 0:
        remaining_summary = f"\n\n**Осталось:** {steps_remaining} шаг(ов) в текущей работе."

    return f"""<!-- generated file: do not edit manually -->
---
id: project_status_current
type: generated_owner_status
generation_state: generated
version: 1.0
---

# Состояние проекта

> Это основной экран владельца. Он автоматически собирается из этапов и карточек задач.

## Ваше действие сейчас

{owner_guidance}{remaining_summary}

Вам не нужно запускать проверки, разбираться с ветками или менять состояния вручную.

## Текущее состояние

| Параметр | Значение |
|---|---|
| Текущий этап | `{current_id}` — {current["title"]} |
| Этапы V1 | ✅ **{completed_milestones}** выполнено / ❌ **{remaining_milestones}** осталось |
| Текущая проектная задача | {task_link} |
| Место в очереди проекта | {queue_position} |
| Шаги текущей задачи | **{steps_done}** из **{steps_done + steps_remaining}** |
| Следующий исполнитель | **{actor}** |

## Этапы V1

{milestone_lines}

## Задачи и техническое покрытие текущего этапа

| Задача | Компонент | Проверка | Состояние |
|---|---|---|---|
{technical_coverage}

## Шаги текущей работы

{step_lines}

## Блокеры

{blocker_text}

## Незакрытые действия владельца (необязательные)

> Эти пункты не блокируют работу агента и не требуют немедленного ответа — они остаются здесь, пока вы их не закроете, независимо от того, что сама задача уже сдана.

{followups_text}

## Что будет дальше

{next_text}

"""


def generate_repository_project_status(root: Path) -> bool:
    return atomic_write_generated(root / "project_status.md", render_repository_project_status(root))
