---
id: template_milestone_completion_report
type: document_template
document_state: current
version: 1.1
updated: 2026-09-10
depends_on: []
---

# Шаблон итогового отчёта этапа

```markdown
---
id: {{milestone_id}}_final_report
type: milestone_completion_report
completion_state: {{completion_state}}
version: 1.1
created: {{created}}
updated: {{updated}}
milestone: {{milestone_id}}
{{history_snapshot}}
---

# {{milestone_label}} — Итоговый отчёт

## 1. Состояние завершения

{{completion_section}}

## 2. Что реализовано функционально

{{functional_section}}

## 3. Изменения в репозитории

{{changes_section}}

## 4. Задачи и тесты этапа

{{tasks_section}}

## 5. Связанные требования

{{requirements_section}}

## 6. Известные ограничения

{{limitations_section}}

## 7. Рекомендации для следующего этапа

{{recommendations_section}}
```
