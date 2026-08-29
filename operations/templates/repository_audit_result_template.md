---
id: template_repository_audit_result
type: document_template
document_state: current
version: 1.0
updated: 2026-08-28
depends_on: []
---

# Шаблон результата аудита репозитория

Каждый запуск создаёт новый файл `work/audit/audit_baseline_YYYY_MM_DD.md`. Исторические результаты не перезаписываются и не удаляются регенерацией.

```markdown
---
id: audit_baseline_{{audit_date_compact}}
type: audit_baseline
document_state: current
version: 1.0
updated: {{audit_date}}
depends_on: []
---

# Аудит репозитория — {{audit_date}}

## 1. Проверенная редакция

- Git SHA: `{{git_sha}}`
- Ветка или тег: `{{git_ref}}`
- Применённый prompt: {{audit_prompt_link}}

## 2. Итог

{{summary}}

## 3. Реестр

| ID | Severity | State | First seen | Review date | Owner | Evidence | Resolution |
|---|---|---|---|---|---|---|---|
{{audit_rows}}

## 4. Карточки findings

{{finding_cards}}
```
