---
id: security_audit
type: guide
document_state: current
applicability: normative
version: 1.1
updated: 2026-09-03
---

# Проверка безопасности

## Запуск

```bash
python3.12 -m bandit -r operations/scripts src --severity-level medium -f json -q
python3.12 operations/scripts/quality/run_suite.py full
```

CI дополнительно выполняет проверки, указанные непосредственно в [`project_check.yml`](../../../.github/workflows/project_check.yml), включая секреты и supply-chain шаги.

## Критерий успеха

Нет неразрешённых findings средней и высокой severity, секретов в охватываемом scope и fail-open шагов. Разрешение ложного срабатывания должно быть точным, минимальным и объяснимым.

## Границы

Bandit не доказывает безопасность архитектуры, внешних интеграций или истории Git. Эти области проверяются threat review и аудитом репозитория.
