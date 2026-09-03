---
id: python_lint_check
type: guide
document_state: current
applicability: normative
version: 1.1
updated: 2026-09-04
---

# Python lint и формат

## Запуск

```bash
python3.12 -m ruff check operations/scripts operations/tests src
python3.12 -m ruff format operations/scripts operations/tests src --check
```

Фактические пути и параметры полного профиля находятся в [`run_suite.py`](../../scripts/quality/run_suite.py).

## Критерий успеха

Обе команды возвращают 0. Правило не отключается ради отдельного файла; сначала исправляется причина, а изменение конфигурации рассматривается как изменение общего quality-контракта.
