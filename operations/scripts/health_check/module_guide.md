---
id: health_check_module
type: documentation
version: 1.5
document_state: current
applicability: normative
updated: 2026-09-04
depends_on:
  - quality_playbooks_readme
---

# Модуль health check

## Назначение

Модуль собирает диагностический снимок репозитория: Git, объём кода, тесты, покрытие, типы и формат. Он не заменяет quality gate и не исправляет состояние.

## Канонический запуск

```bash
python3.12 operations/scripts/health_check/generate.py --summary
python3.12 operations/scripts/health_check/generate.py \
  --json runtime/health_check.json \
  --report runtime/health_check_report.md
```

Полный quality-suite вызывает генератор сам:

```bash
python3.12 operations/scripts/quality/run_suite.py full
```

## Выходы

- JSON — машинные метрики и итоговый статус;
- Markdown report — человекочитаемое представление тех же данных;
- summary — краткий вывод в терминал.

Runtime-файлы являются доказательством только вместе с точным Git SHA, средой и командой запуска.

## Интерпретация

`HEALTHY` означает, что собранные метрики удовлетворяют текущей policy. `NEEDS ATTENTION` указывает на конкретное отклонение, например грязное дерево или ошибку тестов. Отсутствующая Git-история или инструмент делает соответствующую метрику недоступной, а не успешной.

Фактические пороги покрытия берутся из [`quality_baseline.json`](../../quality_baseline.json). Состав полного gate описывает [`run_suite.py`](../quality/run_suite.py).

## Диагностика

- Ошибка версии Python: использовать Python 3.12 и команду из [`document_contracts.json`](../../document_contracts.json).
- Нет Git-истории: запускать в полном checkout или явно пометить метрику недоступной.
- Report расходится с JSON: повторить генерацию и считать это дефектом renderer.
- Тесты не запускались: health report не даёт права заявлять их успех.

## Ограничения

Модуль не проверяет production availability, реальные внешние интеграции, безопасность архитектуры и действия владельца. Для этих утверждений нужны профильные TEST и отдельное SHA-bound evidence.
