<!-- generated file: do not edit manually -->
---
id: health_check_latest
type: generated_health_check
generation_state: generated
generated_at: 2026-08-26T12:36:00Z
version: 2.1
---

# Repository Health Check

## Статистика проверяемого запуска

| Метрика | Где фиксируется |
|---|---|
| Git SHA, ветка и UTC-время | `runtime/health_check_report.md` |
| Тесты: passed/failed, время, coverage | `runtime/health_check_report.md` |
| MyPy, Ruff и форматирование | `runtime/health_check_report.md` |
| Политика покрытия и её пороги | `runtime/health_check_report.md` |
| Размер, коммиты и состояние рабочей копии | `runtime/health_check_report.md` |

Этот файл показывает состав доступной статистики, но не выдаёт старый запуск за
статус текущей ревизии. Актуальный отчёт создаёт канонический
[`run_suite.py`](../operations/scripts/quality/run_suite.py) в
`runtime/health_check_report.md`; в CI он хранится как artifact точного SHA.

Отсутствие artifact, timeout или недоступность MyPy/Ruff/pytest означает
`INCOMPLETE`, а не зелёный статус.
