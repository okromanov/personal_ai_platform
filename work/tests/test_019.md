---
id: TEST_019
type: test
title: "ARC_CMP_007 — Корреляция безопасных событий исполнения"
spec_state: current
execution: automated
automated_evidence: quality_suite
version: 1.0
updated: 2026-09-02
accepts:
  - m02
traces_to:
  - TASK_018
verifies:
  - SYS_024
  - SEC_CTL_014
depends_on:
  - TEST_018
---

# TEST_019 — Корреляция безопасных событий исполнения

Автоматическая проверка. Действия владельца не требуются.

## 1. Назначение

Доказать, что реализация [`ADR_004`](../../adr/adr_004_task_events_and_logging.md) связывает существенные события одного исполнения компонента [`ARC_CMP_007`](../../specifications/architecture_baseline.md#arc_cmp_007) единым `runtime_task_id` и не сохраняет пользовательское содержимое или секреты.

## 2. Что проверяется

События переходов состояния, решений правил, model/tool calls, checkpoints, retries и ошибок имеют переносимую схему, один системный идентификатор исполнения и безопасные технические атрибуты. Два исполнения не смешиваются; секретный sentinel из prompt, параметров инструмента, checkpoint и нормализованной ошибки отсутствует в событиях. Так проверяются [`SYS_024`](../../specifications/system_specification.md#sys_024) и [`SEC_CTL_014`](../../specifications/system_specification.md#sec_ctl_014).

## 3. Автоматический запуск

Канонический quality-suite запускает [`test_task_events.py`](../../operations/tests/product/test_task_events.py). Действий владельца нет.

## 4. Критерий успеха

Набор содержит все обязательные типы событий, каждое событие относится ровно к одному `runtime_task_id`, свободный текст в attributes отклоняется, а sentinel не появляется в сериализуемом представлении событий.

## 5. Состав доказательства

`automated_evidence: quality_suite`: результат unit-тестов входит в SHA-bound запись канонического серверного прогона.
