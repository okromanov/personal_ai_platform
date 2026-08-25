---
id: TEST_009
type: test
title: "ARC_CMP_003 — Оркестрация и RuntimePort: обычный цикл задачи"
spec_state: current
execution: automated
automated_evidence: quality_suite
version: 1.2
updated: 2026-08-25
accepts:
  - m02
traces_to:
  - TASK_003
  - SYS_001
  - SYS_036
  - SYS_003
  - BR_033
depends_on: []
---

# TEST_009 — Оркестрация и RuntimePort: обычный цикл задачи

Автоматическая проверка. Действия владельца не требуются.

## 1. Назначение

Доказать, что компонент [`ARC_CMP_003`](../../specifications/architecture_baseline.md#arc_cmp_003) (Оркестрация и `RuntimePort`) проводит нормализованную задачу через обычный цикл ([`ARC_FLOW_001`](../../specifications/architecture_baseline.md#arc_flow_001)): проверка личности и аварийного выключателя → состояние задачи → выполнение через подключённый `RuntimePort` → ответ, и что смена реализации `RuntimePort` не требует изменений выше этой границы.

## 2. Что проверяется

Реализация стабильного контракта `RuntimePort` (`src/orchestration/runtime_port.py`), тестового переходного слоя `StubRuntimePort` (`src/orchestration/stub_runtime.py`) и `Orchestrator` (`src/orchestration/orchestrator.py`):

- Успешное выполнение отмечает задачу завершённой и отправляет результат через канал ([`SYS_001`](../../specifications/system_specification.md#sys_001), [`SYS_036`](../../specifications/system_specification.md#sys_036)).
- Задача отмечается выполняющейся до вызова `RuntimePort.execute`, а не после.
- Чужая личность отменяет задачу до вызова `RuntimePort` — оркестратор обращается к [`OwnerControl`](../tasks/task_002_arc_002.md) на каждом запуске, а не полагается на проверку канала.
- Активный аварийный выключатель отменяет задачу до вызова `RuntimePort`; проверка личности выполняется раньше проверки выключателя.
- Ошибка выполнения на уровне задачи (`RuntimeResult(succeeded=False)`) отмечает задачу проваленной с исходным сообщением об ошибке — исход контролируемый, а не зависшая операция.
- Недоступность самой среды выполнения (`RuntimePortError`) отмечает задачу проваленной с отдельным, отличимым от обычной ошибки сообщением.
- Замена реализации `RuntimePort` на независимую альтернативу не меняет поведение `Orchestrator`, канала или контроля владельца ([`SYS_003`](../../specifications/system_specification.md#sys_003), [`BR_033`](../../specifications/business_requirements.md#br_033)).

## 3. Автоматический запуск

Часть канонического прогона юнит-тестов, выполняется в `Quality skills` на каждом push/PR:

```bash
python3 operations/scripts/quality/run_unittests.py
```

Отдельный прогон только этого компонента:

```bash
python3 -m unittest operations.tests.product.test_orchestration -v
```

## 4. Критерий успеха

Все 10 тестов проходят, включая сценарии:

- ✓ successful_task — успешное выполнение отмечает задачу завершённой, ответ отправлен через канал
- ✓ canned_runtime_response — ответ `RuntimePort` доходит до канала без изменений
- ✓ message_is_marked_running_before_execute — состояние задачи в момент вызова `execute` — `running`
- ✓ unrecognized_identity — чужая личность отменяет задачу, `RuntimePort` не вызывается
- ✓ active_emergency_switch — активный выключатель отменяет задачу, `RuntimePort` не вызывается
- ✓ identity_checked_before_emergency_switch — при обоих условиях сообщение — об отклонённой личности
- ✓ task_level_runtime_failure — ошибка выполнения отмечает задачу проваленной с исходным сообщением
- ✓ unavailable_environment — недоступность среды даёт отдельное сообщение, отличное от обычной ошибки
- ✓ runtime_swap — альтернативная реализация `RuntimePort` работает по тому же контракту

## 5. Состав доказательства

`automated_evidence: quality_suite`. Каждый запуск канонического набора юнит-тестов создаёт доказательство выполнения всех 10 тестов на текущем Git SHA. Результат успеха фиксируется в evidence записи с временем выполнения и версией платформы.

## 6. Реализованные компоненты

### Компонент: Оркестрация и RuntimePort

**Стабильный контракт**: `RuntimePort` (абстрактный класс)

- `async execute(message: TaskMessage) → RuntimeResult`: выполнить задачу через подключённую среду

**Данные**: `RuntimeResult` (`output`, `succeeded`, `error_message`), исключение `RuntimePortError` (среда недоступна)

**Реализация**: `Orchestrator`

- `async handle(message, *, subject_id, channel) → TaskMessage`: полный обычный цикл задачи
- Обращается к `OwnerControl` за каждой проверкой личности и выключателя — не хранит правила владельца сам
- Не содержит специфики канала: `subject_id` передаётся вызывающей стороной, а не читается из внутреннего формата метаданных конкретного канала

**Тестовый переходный слой**: `StubRuntimePort` — детерминированная реализация `RuntimePort` для проверки цикла до выбора реальной среды агента (сравнение кандидатов остаётся `proposed` в [`ADR_006`](../../adr/adr_006_agent_environment_framework.md))

## 7. Структура кода

```
src/orchestration/
├── __init__.py — публичный API
├── runtime_port.py — RuntimePort, RuntimePortError, RuntimeResult
├── stub_runtime.py — StubRuntimePort (тестовый переходный слой)
└── orchestrator.py — Orchestrator реализация

operations/tests/product/
└── test_orchestration.py — юнит-тесты, часть канонического run_unittests.py (CI/CD)
```

## 8. Соответствие требованиям

| Требование | Статус | Примечание |
|---|---|---|
| [`SYS_001`](../../specifications/system_specification.md#sys_001): Единый жизненный цикл задачи | ✅ | `Orchestrator` доводит задачу до completed/failed/cancelled, без зависаний |
| [`SYS_036`](../../specifications/system_specification.md#sys_036): Единый жизненный цикл при смене канала | ✅ | Цикл не зависит от конкретного канала — `subject_id` и `channel` передаются параметрами |
| [`SYS_003`](../../specifications/system_specification.md#sys_003): Переносимая граница среды агента | ✅ | Проверка проведена с двумя независимыми реализациями `RuntimePort` |
| [`BR_033`](../../specifications/business_requirements.md#br_033): Независимость от поставщика и агентского фреймворка | ✅ | `RuntimePort` не импортирует и не предполагает конкретный SDK |

## 9. Доказательства

- **Исходный код**: [`src/orchestration/`](../../src/orchestration/) — стабильный контракт, тестовый переходный слой и оркестратор
- **Тесты**: 10 юнит-тестов в [`operations/tests/product/test_orchestration.py`](../../operations/tests/product/test_orchestration.py), часть обязательного gate `Quality skills`
- **Отсутствие регрессий**: Запуск `check.py --all` прошёл успешно

## 10. Готово когда

- ✅ 10 тестов пройдено
- ✅ Контракт `RuntimePort` определён и используется
- ✅ `Orchestrator` реализован и обращается к `OwnerControl` на каждом запуске
- ✅ Смена реализации `RuntimePort` подтверждена тестом без изменения контракта выше границы
- ✅ Структура готова для подключения [`ARC_CMP_004`](../../specifications/architecture_baseline.md#arc_cmp_004) (Шлюз моделей) внутри тестового переходного слоя или реальной среды агента

## 11. Что будет дальше

1. [`TASK_004`](../tasks/task_004_arc_004.md): Реализация [`ARC_CMP_004`](../../specifications/architecture_baseline.md#arc_cmp_004) (Шлюз моделей) — нормализованный доступ к LLM, который `RuntimePort` сможет вызывать вместо эхо-ответа
2. [`TASK_005`](../tasks/task_005_arc_005.md): Реализация [`ARC_CMP_005`](../../specifications/architecture_baseline.md#arc_cmp_005) (Шлюз инструментов)
3. [`TASK_006`](../tasks/task_006_arc_007.md): Реализация [`ARC_CMP_007`](../../specifications/architecture_baseline.md#arc_cmp_007) (Состояние задач) — контрольные точки и возобновление после сбоя поверх цикла, построенного здесь
4. Сравнение кандидатов среды агента для [`ADR_006`](../../adr/adr_006_agent_environment_framework.md) остаётся отдельной, ещё не проведённой работой подэтапа 1 [`m02`](../../milestones.md#m02)

## 12. Примечания для разработчика

- `StubRuntimePort` — тестовый переходный слой по [`ADR_002`](../../adr/adr_002_core_runtime_boundary.md)§6, а не заготовка реальной интеграции: он не обращается к модели и не содержит специфики какого-либо SDK.
- Реальное подключение Telegram (`TelegramChannel` → `Orchestrator`) остаётся сквозной интеграцией подэтапа 5 [`m02`](../../milestones.md#m02), а не частью этой TASK — как и [`TASK_001`](../tasks/task_001_arc_001.md)/[`TASK_002`](../tasks/task_002_arc_002.md), эта TASK строит компонент и его контракт, а не боевую проводку.

Действия владельца не требуются: тест полностью автоматизирован и не требует ручного вмешательства.
