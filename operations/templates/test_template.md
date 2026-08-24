---
id: template_test
type: document_template
document_state: current
version: 1.3
updated: 2026-08-24
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

Каждое упоминание в тексте карточки элемента из [`generated/traceability_matrix.md`](../../generated/traceability_matrix.md) (`BR_XXX`, `SYS_XXX`, `THR_XXX`, `SEC_CTL_XXX`, `ARC_CMP_XXX`, `ARC_FLOW_XXX`, `INF_REQ_XXX`, `INF_CMP_XXX`, `INF_FLOW_XXX`, `ADR_XXX`, `TASK_XXX`, другой `TEST_XXX`, этап `mXX`) оформляется как код-спан и ссылка на исходный документ. Исключение: раздел «1. Назначение» может цитироваться целиком как описание файла в [`project_status.md`](../../project_status.md) на уровне корня репозитория — относительная ссылка, посчитанная для `work/tests/`, там ведёт мимо проекта, поэтому в нём элементы оставляют без ссылки (обычным код-спаном).
