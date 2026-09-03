---
id: integration_tests
type: guide
document_state: current
applicability: normative
version: 1.3
updated: 2026-09-03
---

# Интеграционные проверки

## Запуск

```bash
python3.12 -m unittest discover -s operations/tests/integration -p 'test_*.py' -v
python3.12 operations/scripts/quality/run_suite.py full
```

## Что проверяется

Проверяются границы между модулями и quality pipeline. Внешняя сеть, реальные credentials и production-провайдеры не считаются покрытыми, если test profile явно их не запускает.

## Критерий успеха

Тесты проходят без skip, используют изолированное состояние и не оставляют внешних эффектов. Для live-проверки требуется отдельный профиль, точный SHA и отдельное evidence.
