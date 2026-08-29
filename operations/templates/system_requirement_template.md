---
id: template_system_requirement
type: document_template
document_state: current
version: 1.1
updated: 2026-08-28
depends_on: []
---

# Шаблон SYS

Все требуемые поля frontmatter должны соответствовать стандарту, описанному в [`operations/change_process.md#82`](../change_process.md).

```markdown
<a id="{{anchor}}"></a>
### {{requirement_id}} — {{title}}

- `traces_to`: {{traces_to}}

**Требование.** {{requirement}}

**Наблюдаемый результат:** {{observed_result}}
```

SYS не содержит план этапов или конкретный выбор технологии, если он не является частью наблюдаемого обязательного поведения.
