---
id: TEST_009
type: test
title: "ARC_CMP_003 — Оркестрация и RuntimePort: обычный цикл задачи"
spec_state: current
execution: automated
automated_evidence: quality_suite
version: 1.3
updated: 2026-09-04
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
python3.12 operations/scripts/quality/run_unittests.py
```

Отдельный прогон только этого компонента:

```bash
python3.12 -m unittest operations.tests.product.test_orchestration -v
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
