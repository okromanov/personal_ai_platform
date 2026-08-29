---
id: template_threat
type: document_template
document_state: current
version: 1.1
updated: 2026-08-28
depends_on: []
---

# Шаблон THR

Все требуемые поля frontmatter должны соответствовать стандарту, описанному в [`operations/change_process.md#82`](../change_process.md).

```markdown
<a id="{{anchor}}"></a>
### {{threat_id}} — {{title}}

- `mitigated_by`: {{mitigated_by}}

- **Сценарий:** {{scenario}}
- **Активы:** {{assets}}
- **Последствие:** {{consequence}}
- **Остаточный риск:** {{residual_risk}}
```

Для применимой к текущему составу угрозы все четыре поля обязательны и проверяются автоматически. Описание остаётся кратким: THR фиксирует класс угрозы, а не проектирует конкретную реализацию защиты.
