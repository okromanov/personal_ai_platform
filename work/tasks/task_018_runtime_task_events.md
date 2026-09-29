---
id: TASK_018
type: task
title: Корреляция структурированных событий задачи
component: ARC_CMP_007
delivery_role: component
work_state: planned
version: 1.6
updated: 2026-09-29
depends_on:
  - TASK_017
next_actor: agent
owner_action: none
owner_followups: []
allowed_paths:
  - work/tasks/task_018_runtime_task_events.md
  - work/tests/test_019.md
  - src/channels/base.py
  - src/models/base.py
  - src/models/runtime_adapter.py
  - src/observability/__init__.py
  - src/observability/collector.py
  - src/observability/sqlite_store.py
  - src/observability/task_events.py
  - src/orchestration/orchestrator.py
  - src/operations/scheduler_state.py
  - src/task_state/sqlite_store.py
  - src/task_state/store.py
  - src/tools/base.py
  - src/tools/registry.py
  - operations/tests/product/test_model_gateway.py
  - operations/tests/product/test_observability.py
  - operations/tests/product/test_persistent_task_state.py
  - operations/tests/product/test_task_events.py
  - operations/tests/product/test_tool_gateway.py
traces_to:
  - m02
decides: []
implements:
  - ARC_CMP_007
---

# TASK_018 — Корреляция структурированных событий задачи

## 1. Зачем это делаем

Принятый [`ADR_004`](../../adr/adr_004_task_events_and_logging.md) требует, чтобы существенные события одного исполнения можно было собрать по единому `runtime_task_id`. Сейчас состояние, model/tool calls, решения правил и ошибки не образуют проверяемую коррелированную последовательность.

## 2. Результат

Каждое исполнение получает `runtime_task_id`; переходы состояния, вызовы модели и инструментов, решения правил, checkpoints, retries и ошибки создают безопасные структурированные события с тем же идентификатором. Автоматические тесты подтверждают корреляцию и отсутствие известных секретов.

## 3. Где мы сейчас

Хранилище жизненного цикла поставлено [`TASK_006`](task_006_arc_007.md), а базовая наблюдаемость — [`TASK_012`](task_012_inf_007.md). Однако обязательный поведенческий контракт [`ADR_004`](../../adr/adr_004_task_events_and_logging.md) не реализован целиком и не имеет отдельного evidence.

## 4. Что делать сейчас

### Агенту

1. Переносимая схема события и отдельный системный `runtime_task_id` реализованы без свободного текста в attributes.
2. Идентификатор проведён через оркестратор, модель, инструменты, правила, checkpoints, retries и ошибки.
3. Добавлены автоматические positive/negative tests, включая sentinel-проверку утечек.
4. [`TEST_019`](../tests/test_019.md) создан; завершение TASK требует SHA-bound evidence после [`TASK_017`](task_017_m02_live_e2e.md).

## 5. План выполнения

- [x] Определить минимальную схему структурированного события
- [x] Дополнить allowed_paths реальными путями реализации и TEST
- [x] Реализовать создание и распространение `runtime_task_id`
- [x] Связать ключевые события одного исполнения
- [x] Проверить ошибки, retries, checkpoints и redaction
- [x] Написать [`TEST_019`](../tests/test_019.md), связанный с TASK и требованиями компонента

## 6. Состав

Реализация включает минимальную модель событий, интеграционные точки оркестратора, model/tool gateway и lifecycle store, автоматические тесты и [`TEST_019`](../tests/test_019.md). Формальное завершение остаётся после [`TASK_017`](task_017_m02_live_e2e.md) согласно `depends_on`.

## 7. Проверки и доказательства

[`TEST_019`](../tests/test_019.md) собирает события одного исполнения, доказывает единый `runtime_task_id`, ожидаемые event types, нормализованную ошибку и отсутствие секретного sentinel. Отдельно проверяется, что события разных исполнений не смешиваются. Завершение требует evidence канонического gate на точном SHA.

## 8. Готово когда

- ✅ Все обязательные события [`ADR_004`](../../adr/adr_004_task_events_and_logging.md) связаны по `runtime_task_id`
- ✅ Автоматические positive/negative tests проходят
- ✅ Секретный sentinel отсутствует в стандартном событии
- ✅ TEST и evidence относятся к точному SHA

## 9. Что будет дальше

После этой TASK обязательный контракт событий [`ADR_004`](../../adr/adr_004_task_events_and_logging.md) имеет реализацию и evidence; очередь переходит к planned-работе следующего этапа.

## 10. Что это даёт владельцу

При ошибке можно будет увидеть последовательность одного конкретного выполнения, не смешивая её с другими задачами и не раскрывая секреты.
