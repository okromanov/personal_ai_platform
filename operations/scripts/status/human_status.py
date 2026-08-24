from __future__ import annotations

import re
from pathlib import Path

from operations.scripts.common.project import atomic_write
from operations.scripts.common.status_types import TaskItem
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


def _actor_action(body: str, actor: str) -> str:
    section = _section(body, "Что делать сейчас")
    label = {"owner": "Владельцу", "agent": "Агенту", "automation": "Автоматике"}.get(actor)
    if label:
        match = re.search(rf"(?ms)^###\s+{label}\s*$\n(.*?)(?=^###\s|\Z)", section)
        if match:
            return match.group(1).strip()
    return section


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


_CAPABILITY_PLACEHOLDER = "Функционал появится после завершения этой TASK."


def _capability_rows(tasks: list[TaskItem]) -> str:
    """One entry per completed TASK with a real (non-placeholder) "Что это
    даёт владельцу" section, in TASK id order — an accumulating, owner-facing
    changelog of what the solution can already do, built only from what each
    TASK itself claims, never invented here."""
    entries = []
    for task in sorted(tasks, key=lambda item: str(item["id"])):
        if str(task["work_state"]) != "completed":
            continue
        capability = _section(str(task.get("body", "")), "Что это даёт владельцу")
        if not capability or capability == _CAPABILITY_PLACEHOLDER:
            continue
        task_link = f"[`{task['id']}`](work/tasks/{Path(task['path']).name})"
        entries.append(f"- {task_link} — {capability}")
    if not entries:
        return "Пока ни одна завершённая TASK не добавила новую возможность для владельца."
    return "\n".join(entries)


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
    if current_tasks:
        task_lines = "\n".join(
            f"- {_checkbox(str(item['work_state']) == 'completed')} "
            f"[`{item['id']}` — {item['title']}](work/tasks/{Path(str(item['path'])).name})"
            for item in current_tasks
        )
    elif foundation_without_project_tasks:
        task_lines = (
            "Проектных TASK нет: `m01` посвящён подготовке и принятию основы. "
            "Служебная история репозитория здесь не хранится."
        )
    else:
        task_lines = "Проектные TASK для этого этапа ещё не созданы."

    if current_task:
        task_link = (
            f"[`{current_task['id']}` — {current_task['title']}]"
            f"(work/tasks/{Path(str(current_task['path'])).name})"
        )
        task_source_dir = root / Path(str(current_task["path"])).parent
        actor_key = str(current_task["next_actor"])
        actor = ACTOR_LABELS.get(actor_key, actor_key)
        action = _rebase_relative_links(
            _actor_action(str(current_task.get("body", "")), actor_key), task_source_dir, root
        )
        if actor_key == "owner" and str(current_task["owner_action"]) != "none":
            action = f"Выбрать решение по этапу: `{current_task['owner_action']}` или вернуть его на доработку."
        elif all_tasks_completed:
            actor = "агент после команды владельца"
            if current_id == "m01":
                action = (
                    "Проверить опубликованную редакцию, провести смысловую проверку, запросить явное "
                    "подтверждение состава V1 и затем показать выбор по этапу."
                )
            else:
                action = (
                    f"Проверить опубликованную редакцию этапа `{current_id}`, провести смысловую проверку "
                    "и при успехе показать выбор: принять этап или вернуть его на доработку."
                )
        if not action:
            action = "Продолжить работу по карточке текущей задачи."
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
        next_text = _rebase_relative_links(
            _section(str(current_task.get("body", "")), "Что будет дальше"), task_source_dir, root
        ) or "Следующий шаг будет определён после завершения текущей задачи."
    else:
        task_link = "—"
        if foundation_without_project_tasks:
            actor = "агент после команды владельца"
            action = "Проверить серверные доказательства и провести смысловую проверку опубликованной редакции."
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
            action = "Создать первую проектную задачу текущего этапа."
            step_lines = "- [ ] Создать проверяемый план первой проектной задачи."
            steps_done = 0
            steps_remaining = 1
            next_text = "После создания проектной задачи появится её проверяемый план."

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
        participation_text = (
            "Условие уже наступило: все обязательные проверки завершены, "
            "а следующим исполнителем указан **владелец**."
        )
        executor_action = "Ожидается одно из двух решений владельца, указанных в начале страницы."
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
> `{next_action["commands"][0]["value"]}`

Других действий от вас сейчас не требуется. Агент сам выполнит внутренние проверки и сообщит результат."""
        if review_route:
            if current_id == "m01":
                participation_text = f"""Путь до решения по этапу:

1. **Сейчас** откройте новый сеанс агента и отправьте команду `ПРОДОЛЖАЙ {current_id}`.
2. **Затем** агент проверит серверный результат опубликованной редакции.
3. **После этого** агент проведёт независимую смысловую проверку той же редакции.
4. **После проверки** агент попросит подтвердить текущий состав V1 или указать, что изменить.
5. **После подтверждения** агент покажет две точные команды: принять этап или вернуть его на доработку.

Вам не нужно запускать проверки, разбираться с ветками или менять состояния вручную."""
            else:
                participation_text = f"""Путь до решения по этапу:

1. **Сейчас** откройте новый сеанс агента и отправьте команду `ПРОДОЛЖАЙ {current_id}`.
2. **Затем** агент проверит серверный результат опубликованной редакции.
3. **После этого** агент проведёт независимую смысловую проверку той же редакции.
4. **При успехе** агент покажет две точные команды: принять этап или вернуть его на доработку.

Вам не нужно запускать проверки, разбираться с ветками или менять состояния вручную."""
        else:
            participation_text = f"""Путь до следующего результата:

1. **Сейчас** отправьте команду `ПРОДОЛЖАЙ {resume_target}`.
2. **Затем** агент выполнит оставшиеся шаги. Осталось: **{steps_remaining}**.
3. **После проверки** агент сообщит результат и покажет следующее действие.

Вам не нужно запускать проверки, разбираться с ветками или менять состояния вручную."""
        executor_action = action

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

## Текущее состояние

| Параметр | Значение |
|---|---|
| Текущий этап | `{current_id}` — {current["title"]} |
| Текущая проектная задача | {task_link} |
| Место в очереди проекта | {queue_position} |
| Следующий исполнитель | **{actor}** |

## Что произойдёт после вашей команды

{executor_action}

## Когда потребуется ваше участие

{participation_text}

## Прогресс

- Этапы: ✅ **{completed_milestones}** выполнено / ❌ **{remaining_milestones}** осталось
- Текущий этап: **{steps_done}** шагов из **{steps_done + steps_remaining}**

## Общая картина V1

V1 состоит из 6 этапов (m01–m06). Фундамент (m01) готовит инструменты и правила. Пять инкрементов разработки (m02–m06) добавляют функциональность от основного помощника к production-ready версии.

## Этапы V1

{milestone_lines}

## Проектные задачи текущего этапа

{task_lines}

## Шаги текущей работы

{step_lines}

## Блокеры

{blocker_text}

## Что будет дальше

{next_text}

## Что уже умеет решение

> Раздел пополняется по мере завершения проектных TASK: одна запись на каждую TASK, которая добавила владельцу новую возможность. Ничего не удаляется — это накопительная история того, что уже доступно.

{_capability_rows(tasks)}
"""


def generate_repository_project_status(root: Path) -> bool:
    return atomic_write(root / "project_status.md", render_repository_project_status(root))
