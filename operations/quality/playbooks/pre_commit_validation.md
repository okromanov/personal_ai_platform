---
id: pre_commit_validation
type: guide
document_state: current
applicability: normative
version: 1.1
updated: 2026-09-04
---

# Обязательная проверка перед коммитом

## Установка

Выполнить инструкцию [`setup_precommit.md`](../../setup_precommit.md). Hook обязателен для каждого локального коммита.

## Поведение

Hook проверяет защищённые шаблоны, обновляет версию только если staged-документ ещё несёт версию из HEAD, проставляет безопасные ссылки, пересобирает owner dashboard и запускает fast gate после изменений.

## Критерий успеха

Коммит создаётся только при коде 0. Изменённые hook'ом файлы входят в тот же staged snapshot и проверяются повторно.
