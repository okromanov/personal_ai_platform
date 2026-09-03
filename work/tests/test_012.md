---
id: TEST_012
type: test
title: "ARC_CMP_007 — Состояние задач: контрольные точки, повтор, отмена, защита от дублей"
spec_state: current
execution: automated
automated_evidence: quality_suite
version: 1.1
updated: 2026-09-03
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
python3.12 operations/scripts/quality/run_unittests.py
```

Отдельный прогон только этого компонента:

```bash
python3.12 -m unittest operations.tests.product.test_task_state -v
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
