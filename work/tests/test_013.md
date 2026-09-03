---
id: TEST_013
type: test
title: "ARC_CMP_009 — Эксплуатационные функции: работоспособность и логическое состояние планировщика"
spec_state: current
execution: automated
automated_evidence: quality_suite
version: 1.1
updated: 2026-09-04
accepts:
  - m02
traces_to:
  - TASK_007
  - SYS_024
  - SYS_027
depends_on:
  - TEST_012
---

# TEST_013 — Эксплуатационные функции: работоспособность и логическое состояние планировщика

Автоматическая проверка. Действия владельца не требуются.

## 1. Назначение

Доказать, что компонент [`ARC_CMP_009`](../../specifications/architecture_baseline.md#arc_cmp_009) (Эксплуатационные функции) агрегирует работоспособность так, что типовой сбой локализуется до конкретной зависимости, и что логическое состояние планировщика — регистрация намерения, пауза/возобновление — остаётся согласованным с состоянием отдельных задач ([`ARC_CMP_007`](../../specifications/architecture_baseline.md#arc_cmp_007)), а действие восстановления (пауза) явно ограничено.

## 2. Что проверяется

Реализация `HealthAggregator`/`HealthReport`/`DependencyStatus` (`src/operations/health.py`) и `SchedulerState`/`ScheduledIntent` (`src/operations/scheduler_state.py`):

- Отчёт о работоспособности здоров, только если здоровы все зарегистрированные проверки; при сбое хотя бы одной проверки общий отчёт нездоров.
- `unhealthy_dependencies` называет только реально упавшие зависимости — сбой локализуется, а не смешивается с работающими ([`SYS_024`](../../specifications/system_specification.md#sys_024)).
- Исключение внутри одной проверки не прерывает сбор остальных: упавшая проверка становится нездоровой записью, а не аварийно завершает весь отчёт.
- Повторная регистрация проверки/намерения с тем же именем/`intent_id` заменяет предыдущую запись, а не создаёт дубликат.
- Новый планировщик не поставлен на паузу; намерение с активной (не отменённой) задачей — исполнимо.
- Намерение, ссылающееся на отменённую в [`TaskLifecycleStore`](../../src/task_state/base.py) задачу, не исполнимо — состояние планировщика согласовано с состоянием задачи, а не хранит устаревшее намерение.
- Пауза останавливает все намерения независимо от состояния их задач; возобновление восстанавливает исполнимость. Пауза — ограниченное действие восстановления: она не отменяет задачи и не даёт административного доступа.

## 3. Автоматический запуск

Часть канонического прогона юнит-тестов, выполняется в `Quality skills` на каждом push/PR:

```bash
python3.12 operations/scripts/quality/run_unittests.py
```

Отдельный прогон только этого компонента:

```bash
python3.12 -m unittest operations.tests.product.test_operations_state -v
```

## 4. Критерий успеха

Все 12 тестов проходят, включая сценарии:

- ✓ report_is_healthy_when_every_check_is_healthy / report_is_unhealthy_when_any_check_fails
- ✓ unhealthy_dependencies_localizes_to_the_failing_ones_only
- ✓ a_raising_check_is_isolated_as_that_dependencys_failure
- ✓ registering_the_same_name_twice_replaces_the_check
- ✓ new_scheduler_is_not_paused
- ✓ active_task_intent_is_runnable / cancelled_task_intent_is_not_runnable
- ✓ pause_stops_all_intents_regardless_of_task_state / resume_restores_runnable_intents
- ✓ multiple_intents_are_filtered_independently_by_task_state
- ✓ registering_the_same_intent_id_twice_replaces_it

## 5. Состав доказательства

`automated_evidence: quality_suite`. Каждый запуск канонического набора юнит-тестов создаёт доказательство выполнения всех 12 тестов на текущем Git SHA. Результат успеха фиксируется в evidence записи с временем выполнения и версией платформы.
