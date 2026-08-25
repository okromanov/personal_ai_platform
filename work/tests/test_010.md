---
id: TEST_010
type: test
title: "ARC_CMP_004 — Шлюз моделей: нормализованный вызов и интеграция с RuntimePort"
spec_state: current
execution: automated
automated_evidence: quality_suite
version: 1.0
updated: 2026-08-25
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
python3 operations/scripts/quality/run_unittests.py
```

Отдельный прогон только этого компонента:

```bash
python3 -m unittest operations.tests.product.test_model_gateway -v
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

## 6. Реализованные компоненты

### Компонент: Шлюз моделей

**Стабильный контракт**: `ModelGateway` (абстрактный класс)

- `async complete(request: ModelRequest) → ModelResponse`: выполнить один вызов модели

**Данные**: `ModelRequest` (`prompt`, `timeout_seconds`), `ModelResponse` (`text`, `succeeded`, `error_message`, `usage`), `ModelUsage` (`input_tokens`, `output_tokens`), исключение `ModelGatewayError` (поставщик недоступен)

**Тестовый переходный слой**: `StubModelGateway` — детерминированная реализация `ModelGateway` для проверки контракта и цикла задачи до выбора реального поставщика (сравнение кандидатов остаётся `proposed` в [`ADR_005`](../../adr/adr_005_first_model_provider_selection.md))

**Интеграция с оркестрацией**: `ModelBackedRuntimePort` — реализация `RuntimePort` ([`TASK_003`](../tasks/task_003_arc_003.md)), исполняющая задачу через `ModelGateway`; доказывает, что граница `RuntimePort` совместима со шлюзом моделей без изменений выше границы.

## 7. Структура кода

```
src/models/
├── __init__.py — публичный API
├── base.py — ModelGateway, ModelGatewayError, ModelRequest, ModelResponse, ModelUsage
├── stub_gateway.py — StubModelGateway (тестовый переходный слой)
└── runtime_adapter.py — ModelBackedRuntimePort (адаптер к RuntimePort)

operations/tests/product/
└── test_model_gateway.py — юнит-тесты, часть канонического run_unittests.py (CI/CD)
```

## 8. Соответствие требованиям

| Требование | Статус | Примечание |
|---|---|---|
| [`SYS_004`](../../specifications/system_specification.md#sys_004): Нормализованный интерфейс поставщика моделей | ✅ | Запрос, ответ, ошибка, таймаут и показатели использования нормализованы одним контрактом |
| [`BR_034`](../../specifications/business_requirements.md#br_034): Адаптивный выбор модели | ✅ | Контракт не зависит от конкретного поставщика; смена реализации не меняет `Orchestrator` |
| [`SEC_CTL_015`](../../specifications/system_specification.md#sec_ctl_015): Допуск данных к модели и поставщику | ➖ | Реального поставщика ещё нет — допуск данных проверяется на уровне вызывающей стороны до вызова контракта; предметно проверяется, когда появится реальный поставщик ([`ADR_005`](../../adr/adr_005_first_model_provider_selection.md)) |

## 9. Доказательства

- **Исходный код**: [`src/models/`](../../src/models/) — стабильный контракт, тестовый переходный слой и адаптер к `RuntimePort`
- **Тесты**: 11 юнит-тестов в [`operations/tests/product/test_model_gateway.py`](../../operations/tests/product/test_model_gateway.py), часть обязательного gate `Quality skills`
- **Отсутствие регрессий**: Запуск `check.py --all` прошёл успешно

## 10. Готово когда

- ✅ 11 тестов пройдено
- ✅ Контракт `ModelGateway` определён и используется
- ✅ `ModelBackedRuntimePort` подтверждает совместимость с границей `RuntimePort` без изменения `Orchestrator`
- ✅ Полный цикл задачи через шлюз моделей проверен end-to-end

## 11. Что будет дальше

1. [`TASK_005`](../tasks/task_005_arc_005.md): Реализация [`ARC_CMP_005`](../../specifications/architecture_baseline.md#arc_cmp_005) (Шлюз инструментов) — второй внешний контракт, нужный оркестратору для полного цикла выполнения задачи
2. Сравнение кандидатов поставщика модели для [`ADR_005`](../../adr/adr_005_first_model_provider_selection.md) остаётся отдельной, ещё не проведённой работой подэтапа 4 [`m02`](../../milestones.md#m02)

## 12. Примечания для разработчика

- `StubModelGateway` — тестовый переходный слой по [`ADR_003`](../../adr/adr_003_model_provider_interface.md), а не заготовка реальной интеграции: он не обращается к сети и не содержит специфики какого-либо SDK поставщика.
- Реальное подключение поставщика (например, Anthropic Claude по [`ADR_005`](../../adr/adr_005_first_model_provider_selection.md)) остаётся отдельной работой подэтапа 4 [`m02`](../../milestones.md#m02): она требует явного сравнительного evidence и решения владельца о переходе [`ADR_005`](../../adr/adr_005_first_model_provider_selection.md) в `accepted`, а также хранилища секретов ([`INF_CMP_003`](../../specifications/infrastructure_baseline.md#inf_cmp_003), [`TASK_010`](../tasks/task_010_inf_003.md)) для API-ключа поставщика — этой TASK она не входит, как `StubRuntimePort` не была заготовкой реальной среды агента в [`TASK_003`](../tasks/task_003_arc_003.md).

Действия владельца не требуются: тест полностью автоматизирован и не требует ручного вмешательства.
