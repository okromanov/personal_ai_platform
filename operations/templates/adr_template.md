---
id: template_adr
type: document_template
document_state: current
version: 1.0
updated: 2026-08-22
depends_on: []
---

# Шаблон ADR

Все требуемые поля frontmatter должны соответствовать стандарту, описанному в [`operations/change_process.md#82`](../change_process.md).

```markdown
---
id: ADR_XXX
type: adr
decision_state: proposed
version: 1.0
updated: <yyyy-mm-dd>
traces_to:
  - <SYS/ARC/SEC/INF ID>
traces_to_requirement:
  - <SYS_XXX>
---

# ADR_XXX — <Решение>

## 1. Назначение
## 2. Контекст
## 3. Решение
## 4. Альтернативы
## 5. Последствия
## 6. Проверка
```

ADR создаётся только после реального выбора между альтернативами.
