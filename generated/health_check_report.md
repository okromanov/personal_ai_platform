<!-- generated file: do not edit manually -->
---
id: health_check_latest
type: generated_health_check
generation_state: generated
version: 2.0
---

# Repository Health Check

Этот файл намеренно не содержит статуса `HEALTHY`: результат проверки нельзя
честно хранить в той же ревизии, SHA которой он должен подтверждать.

Актуальный отчёт создаёт канонический
[`run_suite.py`](../operations/scripts/quality/run_suite.py) в
`runtime/health_check_report.md`. Отчёт содержит точный Git SHA, ветку, UTC-время
сбора и становится доказательством только как artifact успешного запуска
[`Project check`](../.github/workflows/project_check.yml) для этого SHA.

Отсутствие artifact, timeout или недоступность MyPy/Ruff/pytest означает
`INCOMPLETE`, а не зелёный статус.
