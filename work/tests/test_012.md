---
id: TEST_012
type: test
title: "ARC_CMP_007 — Состояние задач: контрольные точки, повтор, отмена, защита от дублей"
spec_state: current
execution: automated
automated_evidence: quality_suite
version: 1.0
updated: 2026-08-25
accepts:
  - m02
traces_to:
  - TASK_006
  - SYS_001
  - SYS_036
  - SYS_013
depends_on:
  - TEST_009
---

# TEST_012 — Состояние задач: контрольные точки, повтор, отмена, защита от дублей

Автоматическая проверка. Действия владельца не требуются.

## 1. Назначение

Доказать, что компонент [`ARC_CMP_007`](../../specifications/architecture_baseline.md#arc_cmp_007) (Состояние задач) хранит идентичность задачи и её состояние исполнения — контрольную точку, счётчик повторов, флаг отмены — независимо от конкретной реализации `RuntimePort` ([`ARC_CMP_003`](../../specifications/architecture_baseline.md#arc_cmp_003)), и что повтор одного и того же действия не выполняется дважды.

## 2. Что проверяется

Реализация стабильного контракта `TaskLifecycleStore` (`src/task_state/base.py`) и эталонной реализации `InMemoryTaskLifecycleStore` (`src/task_state/store.py`):

- Сохранённая задача (`TaskMessage`) извлекается по её `task_id`; неизвестный `task_id` возвращает `None`, а не исключение.
- Для задачи без предыдущих операций состояние по умолчанию — без контрольной точки, нулевой счётчик повторов, не отменена.
- Контрольная точка (`step`, `data`) извлекается в точности; новая контрольная точка заменяет предыдущую.
- Установка контрольной точки, увеличение счётчика повторов и отмена не затирают друг друга — каждая операция сохраняет значения, установленные другими.
- Отмена идемпотентна: повторная отмена уже отменённой задачи не является ошибкой.
- Защита от дублей: `action_id`, ещё не отмеченный как выполненный, даёт `has_executed() == False`; после `mark_executed()` — `True`; повторная отметка того же `action_id` не является ошибкой.
- Состояние разных задач независимо: операции над одной `task_id` не влияют на состояние другой.

## 3. Автоматический запуск

Часть канонического прогона юнит-тестов, выполняется в `Quality skills` на каждом push/PR:

```bash
python3 operations/scripts/quality/run_unittests.py
```

Отдельный прогон только этого компонента:

```bash
python3 -m unittest operations.tests.product.test_task_state -v
```

## 4. Критерий успеха

Все 13 тестов проходят, включая сценарии:

- ✓ saved_task_is_retrievable_by_id — сохранённая задача извлекается по `task_id`
- ✓ unknown_task_id_returns_none — неизвестный `task_id` не поднимает исключение
- ✓ new_task_has_default_state — состояние по умолчанию корректно
- ✓ checkpoint_is_retrievable — контрольная точка извлекается в точности
- ✓ new_checkpoint_replaces_the_previous_one — новая контрольная точка заменяет старую
- ✓ checkpoint_preserves_retry_count_and_cancelled_flag — контрольная точка не затирает счётчик повторов и флаг отмены
- ✓ increment_retry_increments_and_returns_the_new_count — счётчик повторов увеличивается и возвращается
- ✓ cancel_marks_state_cancelled — отмена помечает состояние как отменённое
- ✓ cancelling_twice_is_not_an_error — повторная отмена не является ошибкой
- ✓ cancel_preserves_checkpoint_and_retry_count — отмена не затирает контрольную точку и счётчик повторов
- ✓ has_executed_is_false_until_marked — защита от дублей до и после отметки
- ✓ marking_the_same_action_twice_does_not_error — повторная отметка того же действия не является ошибкой
- ✓ distinct_tasks_have_independent_state — состояние разных задач не смешивается

## 5. Состав доказательства

`automated_evidence: quality_suite`. Каждый запуск канонического набора юнит-тестов создаёт доказательство выполнения всех 13 тестов на текущем Git SHA. Результат успеха фиксируется в evidence записи с временем выполнения и версией платформы.

## 6. Реализованные компоненты

### Компонент: Состояние задач

**Стабильный контракт**: `TaskLifecycleStore` (абстрактный класс)

- `save_task(message)` / `load_task(task_id)`: хранение и извлечение самой задачи
- `get_state(task_id) → TaskLifecycleState`: текущее состояние исполнения
- `checkpoint(task_id, step, data)`: запись контрольной точки
- `increment_retry(task_id) → int`: увеличение счётчика повторов
- `cancel(task_id)`: пометка отмены (идемпотентна)
- `has_executed(action_id) → bool` / `mark_executed(action_id)`: защита от дублей

**Данные**: `Checkpoint` (`step`, `data`), `TaskLifecycleState` (`checkpoint`, `retry_count`, `cancelled`), исключение `TaskLifecycleError` (хранилище недоступно)

**Эталонная реализация**: `InMemoryTaskLifecycleStore` — минимальная рабочая реализация для [`m02`](../../milestones.md#m02) поверх памяти процесса; не переживает перезапуск — физическое постоянное хранилище ([`INF_CMP_005`](../../specifications/infrastructure_baseline.md#inf_cmp_005), [`TASK_011`](../tasks/task_011_inf_005.md)) подключится к тому же контракту позже без его изменения.

## 7. Структура кода

```
src/task_state/
├── __init__.py — публичный API
├── base.py — TaskLifecycleStore, TaskLifecycleError, Checkpoint, TaskLifecycleState
└── store.py — InMemoryTaskLifecycleStore (эталонная реализация)

operations/tests/product/
└── test_task_state.py — юнит-тесты, часть канонического run_unittests.py (CI/CD)
```

## 8. Соответствие требованиям

| Требование | Статус | Примечание |
|---|---|---|
| [`SYS_001`](../../specifications/system_specification.md#sys_001): Единый жизненный цикл задачи | ✅ | Контрольная точка и флаг отмены хранятся отдельно от состояния конкретной среды агента |
| [`SYS_036`](../../specifications/system_specification.md#sys_036): Единый жизненный цикл при смене канала | ✅ | Хранение ключуется по `task_id`, не зависит от канала-источника |
| [`SYS_013`](../../specifications/system_specification.md#sys_013): Плановые и регулярные задачи | ➖ | Хранилище готово для планировщика ([`ARC_CMP_009`](../../specifications/architecture_baseline.md#arc_cmp_009), [`TASK_007`](../tasks/task_007_arc_009.md)); сам планировщик — отдельная TASK |
| [`SEC_CTL_008`](../../specifications/system_specification.md#sec_ctl_008): Контроль чувствительного внешнего действия | ✅ | Защита от дублей (`has_executed`/`mark_executed`) подтверждена тестом |
| [`SEC_CTL_017`](../../specifications/system_specification.md#sec_ctl_017): Безопасное расписание | ➖ | Хранит намерение и контрольную точку, а не разрешение — повторная проверка личности/правил перед запуском остаётся ответственностью планировщика ([`TASK_007`](../tasks/task_007_arc_009.md)) |

## 9. Доказательства

- **Исходный код**: [`src/task_state/`](../../src/task_state/) — стабильный контракт и эталонная реализация
- **Тесты**: 13 юнит-тестов в [`operations/tests/product/test_task_state.py`](../../operations/tests/product/test_task_state.py), часть обязательного gate `Quality skills`
- **Отсутствие регрессий**: Запуск `check.py --all` прошёл успешно

## 10. Готово когда

- ✅ 13 тестов пройдено
- ✅ Контракт `TaskLifecycleStore` определён и используется
- ✅ Защита от дублей подтверждена тестом
- ✅ Отмена и повтор не искажают друг друга и контрольную точку

## 11. Что будет дальше

1. [`TASK_007`](../tasks/task_007_arc_009.md): Реализация [`ARC_CMP_009`](../../specifications/architecture_baseline.md#arc_cmp_009) (Эксплуатационные функции) — планировщик и работоспособность, опирающиеся на состояние отдельных задач из этого компонента
2. Физическое постоянное хранилище для этого контракта ([`INF_CMP_005`](../../specifications/infrastructure_baseline.md#inf_cmp_005)) остаётся отдельной, ещё не проведённой работой [`TASK_011`](../tasks/task_011_inf_005.md)

## 12. Примечания для разработчика

- `InMemoryTaskLifecycleStore` — рабочая реализация для [`m02`](../../milestones.md#m02), а не тестовая заглушка: контракт полностью реализован, просто не переживает перезапуск процесса. Это отличает её от `StubModelGateway`/`StubRuntimePort`, которые стоят на месте ещё не выбранного поставщика/среды.
- `Orchestrator` ([`TASK_003`](../tasks/task_003_arc_003.md)) пока не вызывает этот контракт — подключение контрольных точек к циклу выполнения задачи остаётся отдельной работой, а не частью этой TASK.

Действия владельца не требуются: тест полностью автоматизирован и не требует ручного вмешательства.
