---
id: pre_push_validation
type: guide
document_state: current
applicability: normative
version: 1.1
updated: 2026-09-03
---

# Локальная проверка перед push

Pre-push hook — опциональная локальная страховка; обязательными остаются pre-commit, полный локальный gate и серверный Project check.

## Запуск

```bash
bash operations/hooks/pre_push_hook.sh
```

Hook запускает канонический `full` profile. Сетевые и platform-specific шаги остаются в CI и не имитируются локальным успехом.

## Критерий успеха

Push продолжается только при коде 0. Установка pre-push hook не является условием корректности репозитория и не меняет серверную политику.
