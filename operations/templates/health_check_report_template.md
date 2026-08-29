---
id: template_health_check_report
type: document_template
document_state: current
version: 1.0
updated: 2026-08-28
depends_on: []
---

# Шаблон runtime health report

Отчёт существует только как SHA-bound runtime/CI artifact и не коммитится в репозиторий.

```markdown
<!-- generated file: do not edit manually -->
---
id: health_check_latest
type: generated_health_check
generation_state: generated
version: 2.0
---

# Repository health snapshot

## Состояние

- Репозиторий: {{remote_url}}
- Ветка: `{{branch_name}}`
- SHA: `{{head_sha}}`
- Собрано: {{collected_at}}
- Итог: {{overall_status}}

## Метрики репозитория

| Метрика | Значение |
|---|---:|
| Коммиты | {{total_commits}} |
| Python-файлы | {{python_files}} |
| Строки кода | {{lines_of_code}} |
| Размер проекта, MB | {{project_size_mb}} |
| Рабочее дерево чистое | {{working_tree_clean}} |

## Тесты и качество

| Метрика | Значение |
|---|---:|
| Тесты пройдены | {{tests_passed}} |
| Тесты провалены | {{tests_failed}} |
| Покрытие, % | {{coverage_percent}} |
| Время тестов, сек | {{test_duration}} |
| MyPy issues | {{mypy_issues}} |
| Ruff issues | {{ruff_issues}} |
| Форматирование | {{formatting_compliant}} |
| Coverage policy | {{coverage_policy}} |

## Слепок комплексного аудита

| Столп | Evidence status |
|---|---|
{{rows}}

Проверено для SHA `{{head_sha}}`. Отчёт агрегирует результаты комплексной
проверки; отсутствие отдельного artifact означает `UNAVAILABLE`, а не успех.

{{recommendations}}
```
