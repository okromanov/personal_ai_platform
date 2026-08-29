---
id: TASK_006
type: task
title: Реализация ARC_CMP_007
component: ARC_CMP_007
work_state: completed
version: 2.2
updated: 2026-08-29
next_actor: none
owner_action: none
depends_on:
  - TASK_005
allowed_paths:
  - work/tasks/task_006_arc_007.md
  - operations/scripts/status/human_status.py
  - operations/tests/test_owner_usability.py
  - src/task_state/
  - src/task_state/__init__.py
  - src/task_state/base.py
  - src/task_state/store.py
  - operations/tests/product/test_task_state.py
  - work/tests/test_012.md
traces_to:
  - m02
implements:
  - ARC_CMP_007
tests:
  - TEST_012
---

# TASK_006 — Реализация ARC_CMP_007

## 1. Зачем это делаем

Реализовать хранение идентичности и жизненного цикла исполняемой задачи: отмену, повтор, контрольную точку, возобновление и защиту от дублей. Без этого компонента при сбое или перезапуске оркестратора ([`TASK_003`](task_003_arc_003.md)) прогресс задачи теряется, и её нельзя ни отменить, ни возобновить с контрольной точки, ни защититься от повторного исполнения одного и того же действия.

## 2. Результат

Стабильный контракт `TaskLifecycleStore`: хранит саму задачу как сообщение и её состояние исполнения — текущий шаг, контрольные точки, счётчик повторов, флаг отмены. [`TASK_002`](task_002_arc_002.md) реализует не хранилище задач, а [`ARC_CMP_002`](../../specifications/architecture_baseline.md#arc_cmp_002) (Контроль владельца) — более ранняя редакция этой карточки ошибочно предполагала обратное. Состояние задачи явно не является внутренним состоянием конкретной среды агента (`RuntimePort`), поэтому переживает смену реализации среды.

## 3. Где мы сейчас

Спецификация и реализация [`ARC_CMP_007`](../../specifications/architecture_baseline.md#arc_cmp_007) полностью завершены и покрыты [`TEST_012`](../tests/test_012.md). Хранилище готово для планировщика ([`ARC_CMP_009`](../../specifications/architecture_baseline.md#arc_cmp_009), [`TASK_007`](task_007_arc_009.md)), но `Orchestrator` ([`TASK_003`](task_003_arc_003.md)) пока не вызывает этот контракт — подключение контрольных точек к циклу выполнения задачи остаётся отдельной, ещё не проведённой работой.

## 4. Что делать сейчас

### Агенту

Работа завершена, следующего действия по этой TASK нет.

## 5. План выполнения

- [x] Изучить требования к [`ARC_CMP_007`](../../specifications/architecture_baseline.md#arc_cmp_007)
- [x] Дополнить allowed_paths реальными путями
- [x] Спроектировать реализацию
- [x] Реализовать компонент
- [x] Написать TEST, связанный с TASK и требованиями компонента
- [x] Проверить покрытие путей в allowed_paths

## 6. Состав

[`src/task_state/`](../../src/task_state/) — стабильный контракт `TaskLifecycleStore` ([`base.py`](../../src/task_state/base.py)) и эталонная реализация `InMemoryTaskLifecycleStore` ([`store.py`](../../src/task_state/store.py)). [`work/tests/test_012.md`](../tests/test_012.md) — описание проверок компонента. [`operations/tests/product/test_task_state.py`](../../operations/tests/product/test_task_state.py) — юнит-тесты, проверяющие компонент.

`capability_summary.md`, [`operations/scripts/status/human_status.py`](../../operations/scripts/status/human_status.py) и [`operations/tests/test_owner_usability.py`](../../operations/tests/test_owner_usability.py) добавлены в `allowed_paths` по отдельному решению владельца, не относящемуся к реализации [`ARC_CMP_007`](../../specifications/architecture_baseline.md#arc_cmp_007): раздел «Что уже умеет решение» в [`project_status.md`](../../project_status.md) заменён с автосписка по TASK на связную сводку, вручную поддерживаемую в `capability_summary.md` — карточки TASK свой текст «Что это даёт владельцу» не меняют. `capability_summary.md` и раздел «Что уже умеет решение» позже удалены отдельным решением владельца.

## 7. Проверки и доказательства

Автоматическая проверка подтверждает, что все изменённые пути входят в `allowed_paths`. Требования компонента проверяет [`TEST_012`](../tests/test_012.md): юнит-тесты [`operations/tests/product/test_task_state.py`](../../operations/tests/product/test_task_state.py), часть обязательного gate `Quality skills`.

Ручная проверка при код-ревью: повторный вызов `mark_executed`/`checkpoint`/`cancel` не искажает уже сохранённое состояние (подтверждено тестами); `has_executed`/`mark_executed` защищают от повторного выполнения одного и того же действия; контракт не импортирует и не предполагает конкретную реализацию `RuntimePort`.

## 8. Готово когда

- ✅ Все шаги плана выполнены
- ✅ Локальные проверки успешны ([`operations/tests/product/test_task_state.py`](../../operations/tests/product/test_task_state.py): 13/13 тестов прошли, часть CI gate)
- ✅ Pre-commit валидация успешна
- ✅ CI успешен
- ✅ Код review (смысловая проверка) пройден

## 9. Что будет дальше

[`TASK_007`](task_007_arc_009.md) реализует Эксплуатационные функции ([`ARC_CMP_009`](../../specifications/architecture_baseline.md#arc_cmp_009)) — логическое состояние планировщика, работоспособности и восстановления, которое опирается на состояние отдельных задач из этого компонента для принятия решений на уровне всей системы.

## 10. Что это даёт владельцу

Пока напрямую ничего не доступно: контракт и работающая реализация хранения, ещё не подключённая к циклу выполнения задачи. Появилось место, где прогресс задачи (шаг, счётчик повторов, отмена) может сохраняться так, чтобы его можно было корректно возобновить, и где действие, уже выполненное однажды, не выполнится повторно по той же причине. Подключение к реальному циклу оркестратора и переживание перезапуска процесса появятся в следующих TASK.
