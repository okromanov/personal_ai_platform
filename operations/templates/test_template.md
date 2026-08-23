---
id: template_test
type: document_template
document_state: current
version: 1.2
updated: 2026-08-23
depends_on: []
---

# Шаблон TEST

Все требуемые поля frontmatter должны соответствовать стандарту, описанному в [`operations/change_process.md#82`](../change_process.md).

```markdown
---
id: TEST_XXX
type: test
spec_state: current
execution: automated
version: 1.0
updated: <yyyy-mm-dd>
traces_to:
  - TASK_XXX
# Для продуктового TEST:
verifies:
  - <SYS/SEC/ARC/INF/document ID>
# Для TEST основы проекта, если продуктовая цель отсутствует:
accepts:
  - <mXX>
automated_evidence: <evidence_id, если execution=automated>
# Для execution=manual вместо automated_evidence:
manual_evidence: <evidence_id структурированной записи результата>
---

# TEST_XXX — <Название доказательства>

## 1. Назначение
## 2. Что проверяется
## 3. Автоматический запуск
## 4. Критерий успеха
## 5. Состав доказательства
```

Для `execution: automated` раздел 3 описывает автоматический запуск и прямо сообщает, что действий владельца нет. Инструкции владельцу в автоматическом TEST запрещены.

Для неприводимой к автоматике пользовательской проверки указывается `execution: manual`, удаляется `automated_evidence`, задаётся `manual_evidence`, а раздел 3 называется `Действия владельца`. Эти действия должны быть безопасными и не могут требовать Git, PowerShell или внутренних скриптов. Результат сохраняется в структурированной записи, указанной каталогом доказательств; отсутствие записи даёт `missing`.

TEST должен иметь `verifies` конкретного трассируемого свойства либо `accepts` этапа основы проекта. Нельзя придумывать продуктовую цель только ради заполнения метаданных.

`spec_state` описывает актуальность спецификации и не хранит результат запуска. Каждый запуск создаёт отдельную запись доказательства с `result`, Git SHA, временем, средой, источником и целями. Результат не записывается обратно в первичный документ.
