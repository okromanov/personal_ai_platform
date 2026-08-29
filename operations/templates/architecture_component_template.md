---
id: template_architecture_component
type: document_template
document_state: current
version: 1.0
updated: 2026-08-28
depends_on: []
---

# Шаблон ARC_CMP

Шаблон задаёт устойчивую логическую роль, а не конкретный процесс, контейнер
или поставщика.

```markdown
<a id="{{anchor}}"></a>
### {{component_id}} — {{title}}

- `traces_to`: {{traces_to}}

{{description}}

**Ответственность:** {{responsibility}}
```
