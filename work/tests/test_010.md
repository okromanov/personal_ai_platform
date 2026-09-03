---
id: TEST_010
type: test
title: "ARC_CMP_004 — Шлюз моделей: нормализованный вызов и интеграция с RuntimePort"
spec_state: current
execution: automated
automated_evidence: quality_suite
version: 1.1
updated: 2026-09-03
accepts:
  - m02
traces_to:
  - TASK_004
  - SYS_004
  - BR_034
depends_on:
  - TEST_009
---

# TEST_010 — Шлюз моделей: нормализованный вызов и интеграция с RuntimePort

Автоматическая проверка. Действия владельца не требуются.

## 1. Назначение

Доказать, что компонент [`ARC_CMP_004`](../../specifications/architecture_baseline.md#arc_cmp_004) (Шлюз моделей) нормализует запрос, ответ, ошибку и показатели использования модели через единый контракт `ModelGateway`, и что этот контракт подключается к границе `RuntimePort` ([`ARC_CMP_003`](../../specifications/architecture_baseline.md#arc_cmp_003), [`TASK_003`](../tasks/task_003_arc_003.md)) без изменения `Orchestrator`, канала или контроля владельца.

## 2. Что проверяется

Реализация стабильного контракта `ModelGateway` (`src/models/base.py`), тестового переходного слоя `StubModelGateway` (`src/models/stub_gateway.py`) и адаптера `ModelBackedRuntimePort` (`src/models/runtime_adapter.py`):

- Успешный вызов возвращает нормализованный текст и показатели использования (`ModelUsage`) ([`SYS_004`](../../specifications/system_specification.md#sys_004)).
- Заранее заданный ответ (`register_response`) доходит до вызывающей стороны без изменений.
- Управляемая ошибка вызова (`register_failure`) нормализуется в `ModelResponse(succeeded=False)` с исходным сообщением, а не пробрасывается как исключение конкретного SDK.
- Недоступность самого поставщика (`simulate_unavailable`) поднимает отдельное, отличимое от обычной ошибки исключение `ModelGatewayError`.
- `ModelBackedRuntimePort` реализует контракт `RuntimePort` ([`TASK_003`](../tasks/task_003_arc_003.md)) поверх `ModelGateway`: успех, управляемая ошибка и недоступность поставщика транслируются в `RuntimeResult`/`RuntimePortError` без изменения самого контракта.
- Полный цикл задачи ([`ARC_FLOW_001`](../../specifications/architecture_baseline.md#arc_flow_001)) через `Orchestrator` + `ModelBackedRuntimePort` завершается ожидаемым состоянием (`completed`/`failed`) и отправляет ответ через канал — без единого изменения в `Orchestrator`, `TelegramChannel` или `OwnerControlGate` ([`BR_034`](../../specifications/business_requirements.md#br_034)).

## 3. Автоматический запуск

Часть канонического прогона юнит-тестов, выполняется в `Quality skills` на каждом push/PR:

```bash
python3.12 operations/scripts/quality/run_unittests.py
```

Отдельный прогон только этого компонента:

```bash
python3.12 -m unittest operations.tests.product.test_model_gateway -v
```

## 4. Критерий успеха

Все 11 тестов проходят, включая сценарии:

- ✓ default_response_echoes_prompt — без заданного ответа `StubModelGateway` возвращает детерминированное эхо
- ✓ registered_response — заранее заданный ответ доходит без изменений
- ✓ usage_metrics — показатели использования присутствуют при успехе
- ✓ registered_failure — управляемая ошибка нормализуется в `ModelResponse(succeeded=False)`
- ✓ simulated_unavailable — недоступность поставщика поднимает `ModelGatewayError`
- ✓ model_gateway_error_is_a_distinct_type — тип исключения различим
- ✓ successful_completion_becomes_runtime_output — `ModelBackedRuntimePort` транслирует успех в `RuntimeResult`
- ✓ failed_completion_becomes_failed_runtime_result — управляемая ошибка модели становится проваленным `RuntimeResult`
- ✓ gateway_outage_raises_runtime_port_error — недоступность поставщика поднимает `RuntimePortError`, а не другое исключение
- ✓ full_cycle_completes_task_via_model_gateway — полный цикл `Orchestrator` завершает задачу через шлюз моделей
- ✓ model_failure_marks_task_failed_through_full_cycle — ошибка модели доходит до владельца через полный цикл как проваленная задача

## 5. Состав доказательства

`automated_evidence: quality_suite`. Каждый запуск канонического набора юнит-тестов создаёт доказательство выполнения всех 11 тестов на текущем Git SHA. Результат успеха фиксируется в evidence записи с временем выполнения и версией платформы.
