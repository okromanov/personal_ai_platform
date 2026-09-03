---
id: unit_tests
type: guide
document_state: current
applicability: normative
version: 1.1
updated: 2026-09-03
---

# Unit tests и покрытие

## Запуск

```bash
python3.12 operations/scripts/quality/run_unittests.py
```

Полный suite запускает тот же runner с branch coverage и затем применяет [`check_coverage.py`](../../scripts/quality/check_coverage.py).

## Критерий успеха

Нет failures, errors, skips и unexpected successes; coverage не ниже общего и поимённых порогов. Тест обязан проверять наблюдаемое поведение и падать при целевом дефекте.

## Нестабильность

Повтор до случайного успеха запрещён. Источник времени, порядка, сети или гонки устраняется либо тест удаляется до слияния.
