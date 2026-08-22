---
id: template_security_control
type: document_template
document_state: current
version: 1.0
updated: 2026-08-22
depends_on: []
---

# Шаблон SEC_CTL

Все требуемые поля frontmatter должны соответствовать стандарту, описанному в [`operations/change_process.md#82`](../change_process.md).

```markdown
<a id="sec_ctl_xxx"></a>
### SEC_CTL_XXX — <Название контроля>

- `traces_to`: `SYS_XXX`

<Какое техническое свойство обязательно. Не фиксировать конкретное средство реализации без отдельного ADR.>
```

Угроза хранит каноническую связь `mitigated_by` с мерой защиты. Архитектурный компонент или инфраструктурное требование хранит свою связь `traces_to` с этой мерой. Обратные копии этих связей здесь не добавляются.
