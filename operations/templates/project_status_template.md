---
id: template_project_status
type: document_template
document_state: current
version: 1.0
updated: 2026-08-28
depends_on: []
---

# Шаблон состояния проекта

Единственная структура [`project_status.md`](../../project_status.md). Renderer передаёт только значения токенов и не добавляет разделы самостоятельно.

```markdown
<!-- generated file: do not edit manually -->
---
id: project_status_current
type: generated_owner_status
generation_state: generated
version: 1.0
---

# Состояние проекта

> Это основной экран владельца. Он автоматически собирается из этапов и карточек задач.

## Ваше действие сейчас

{{owner_guidance}}

Вам не нужно запускать проверки, разбираться с ветками или менять состояния вручную.

## Текущее состояние

| Параметр | Значение |
|---|---|
| Текущий этап | `{{current_id}}` — {{current_title}} |
| Этапы V1 | ✅ **{{completed_milestones}}** выполнено / ❌ **{{remaining_milestones}}** осталось |
| Текущая проектная задача | {{task_link}} |
| Место в очереди проекта | {{queue_position}} |
| Шаги текущей задачи | **{{steps_done}}** из **{{steps_total}}** |
| Следующий исполнитель | **{{actor}}** |

## Этапы V1

{{milestone_lines}}

## Проектные задачи текущего этапа

| Задача | Компонент | Проверка | Состояние |
|---|---|---|---|
{{technical_coverage}}

## Шаги текущей работы

{{step_lines}}

## Блокеры

{{blocker_text}}

{{audit_status}}

## Что уже умеет решение

{{capability_summary}}

## Незакрытые действия владельца (необязательные)

> Эти пункты не блокируют работу агента и не требуют немедленного ответа — они остаются здесь, пока вы их не закроете, независимо от того, что сама задача уже сдана.

{{followups_text}}

## Что будет дальше

{{next_text}}
```
