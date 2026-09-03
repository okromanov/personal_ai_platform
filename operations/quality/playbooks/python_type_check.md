---
id: python_type_check
type: guide
document_state: current
applicability: normative
version: 1.1
updated: 2026-09-04
---

# Проверка типов Python

## Запуск

```bash
python3.12 operations/scripts/quality/run_mypy_baseline.py
```

Wrapper сравнивает результат MyPy с [`quality_baseline.json`](../../quality_baseline.json) по общему числу и сочетанию «файл + код ошибки».

## Критерий успеха

Новая ошибка, новый код ошибки в файле или рост общего budget блокируют gate. Уменьшение долга уменьшает baseline; baseline не расширяется для прохождения конкретного PR.
