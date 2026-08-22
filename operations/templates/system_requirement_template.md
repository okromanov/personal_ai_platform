---
id: template_system_requirement
type: document_template
document_state: current
version: 1.0
updated: 2026-08-22
depends_on: []
---

# Шаблон SYS

Все требуемые поля frontmatter должны соответствовать стандарту, описанному в [`operations/change_process.md#82`](../change_process.md).

```markdown
<a id="sys_xxx"></a>
### SYS_XXX — <Название проверяемого поведения>

- `traces_to`: `BR_XXX`

**Требование.** Система должна...

**Наблюдаемый результат:** ...
```

SYS не содержит план этапов или конкретный выбор технологии, если он не является частью наблюдаемого обязательного поведения.
