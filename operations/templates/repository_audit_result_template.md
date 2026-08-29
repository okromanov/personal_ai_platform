---
id: template_repository_audit_result
type: document_template
document_state: current
version: 1.0
updated: 2026-08-28
depends_on: []
---

# Шаблон результата аудита репозитория

Каждый запуск создаёт новый файл `work/audit/audit_baseline_YYYY_MM_DD.md`, содержащий **только новые находки этого запуска** (со своим `## 3. Реестр` и `## 4. Карточки findings`, ограниченными новыми ID). Этот файл — неизменяемый точечный отчёт: после публикации он не редактируется и не удаляется регенерацией.

Текущее состояние **всех** находок (включая перенесённые из более ранних датированных отчётов) ведётся отдельно и непрерывно в [`work/audit/audit_register.md`](../../work/audit/audit_register.md) — фиксированном, не датированном файле, который не создаётся заново при каждом аудите, а редактируется на месте. Именно [`audit_register.md`](../../work/audit/audit_register.md) — единственный источник, который читают канонический gate (`validate_audit_baseline()` в `operations/scripts/quality/run_suite.py`) и owner dashboard (`_audit_status()` в `operations/scripts/status/human_status.py`). После публикации датированного отчёта его новые находки добавляются в [`audit_register.md`](../../work/audit/audit_register.md); состояние существующих строк обновляется там же по мере исправления, а не пересозданием файла.

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
