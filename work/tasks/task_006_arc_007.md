---
id: TASK_006
type: task
title: Реализация ARC_CMP_007
component: ARC_CMP_007
work_state: planned
version: 1.9
updated: 2026-08-25
next_actor: agent
owner_action: none
depends_on:
  - TASK_005
allowed_paths:
  - work/tasks/task_006_arc_007.md
  - operations/capability_summary.md
  - operations/scripts/status/human_status.py
  - operations/tests/test_owner_usability.py
traces_to:
  - m02
implements:
  - ARC_CMP_007
---

# TASK_006 — Реализация ARC_CMP_007

## 1. Зачем это делаем

Реализовать хранение идентичности и жизненного цикла исполняемой задачи: отмену, повтор, контрольную точку, возобновление и защиту от дублей. Без этого компонента при сбое или перезапуске оркестратора ([`TASK_003`](task_003_arc_003.md)) прогресс задачи теряется, и её нельзя ни отменить, ни возобновить с контрольной точки, ни защититься от повторного исполнения одного и того же действия.

## 2. Результат

Стабильный контракт `TaskLifecycleStore`: хранит саму задачу как сообщение и её состояние исполнения — текущий шаг, контрольные точки, счётчик повторов, флаг отмены. [`TASK_002`](task_002_arc_002.md) реализует не хранилище задач, а [`ARC_CMP_002`](../../specifications/architecture_baseline.md#arc_cmp_002) (Контроль владельца) — более ранняя редакция этой карточки ошибочно предполагала обратное. Состояние задачи явно не является внутренним состоянием конкретной среды агента (`RuntimePort`), поэтому переживает смену реализации среды.

## 3. Где мы сейчас

Спецификация [`ARC_CMP_007`](../../specifications/architecture_baseline.md#arc_cmp_007) определяет требования ([`SYS_001`](../../specifications/system_specification.md#sys_001), [`SYS_036`](../../specifications/system_specification.md#sys_036), [`SYS_013`](../../specifications/system_specification.md#sys_013), [`SYS_020`](../../specifications/system_specification.md#sys_020), [`SEC_CTL_008`](../../specifications/system_specification.md#sec_ctl_008), [`SEC_CTL_017`](../../specifications/system_specification.md#sec_ctl_017)). Реализации нет. Зависит от [`TASK_005`](task_005_arc_005.md) (шлюз инструментов) — оба компонента используются оркестратором ([`TASK_003`](task_003_arc_003.md)) на каждом шаге цикла выполнения.

## 4. Что делать сейчас

### Агенту

1. Изучить спецификацию [`ARC_CMP_007`](../../specifications/architecture_baseline.md#arc_cmp_007)
2. Дополнить `allowed_paths` фактическими путями реализации
3. Создать план реализации
4. Реализовать функциональность и написать TEST с реальным evidence
5. Связать TASK с TEST, который проверяет требования компонента
6. Проверить интеграцию

## 5. План выполнения

- [ ] Изучить требования к [`ARC_CMP_007`](../../specifications/architecture_baseline.md#arc_cmp_007)
- [ ] Дополнить allowed_paths реальными путями
- [ ] Спроектировать реализацию
- [ ] Реализовать компонент
- [ ] Написать TEST, связанный с TASK и требованиями компонента
- [ ] Проверить покрытие путей в allowed_paths

## 6. Состав

**При начале:** агент определит реальные файлы (вероятно `src/task_state/`), добавит в `allowed_paths`, создаст TEST.

**Ожидаемые файлы:**
- `src/task_state/base.py` — контракт `TaskLifecycleStore`
- `src/task_state/checkpoint.py` — модель контрольной точки и защита от дублей
- `work/tests/test_00X.md` — описание проверок

[`operations/capability_summary.md`](../../operations/capability_summary.md), [`operations/scripts/status/human_status.py`](../../operations/scripts/status/human_status.py) и [`operations/tests/test_owner_usability.py`](../../operations/tests/test_owner_usability.py) добавлены в `allowed_paths` по отдельному решению владельца, не относящемуся к реализации [`ARC_CMP_007`](../../specifications/architecture_baseline.md#arc_cmp_007): раздел «Что уже умеет решение» в [`project_status.md`](../../project_status.md) заменён с автосписка по TASK на связную сводку, вручную поддерживаемую в [`operations/capability_summary.md`](../../operations/capability_summary.md) — карточки TASK свой текст «Что это даёт владельцу» не меняют.

## 7. Проверки и доказательства

**Автоматические:**
1. Все файлы в `allowed_paths` (CI проверяет)
2. Все тесты в связанном TEST проходят, включая сценарий возобновления с контрольной точки после сбоя
3. MyPy type check успешен
4. Форматирование соответствует

**Ручные (code review):**
1. Повторный запуск одного и того же действия не выполняется дважды (защита от дублей)
2. Отмена задачи останавливает исполнение на ближайшей безопасной точке
3. Состояние не привязано к конкретной реализации `RuntimePort`

## 8. Готово когда

- ✅ Все шаги плана выполнены
- ✅ Локальные проверки успешны
- ✅ CI успешен
- ✅ Код review завершен

## 9. Что будет дальше

[`TASK_007`](task_007_arc_009.md) реализует Эксплуатационные функции ([`ARC_CMP_009`](../../specifications/architecture_baseline.md#arc_cmp_009)) — логическое состояние планировщика, работоспособности и восстановления, которое опирается на состояние отдельных задач из этого компонента для принятия решений на уровне всей системы.

## 10. Что это даёт владельцу

Функционал появится после завершения этой TASK.
