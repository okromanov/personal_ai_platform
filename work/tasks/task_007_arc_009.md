---
id: TASK_007
type: task
title: Реализация ARC_CMP_009
component: ARC_CMP_009
work_state: planned
version: 1.4
updated: 2026-08-24
next_actor: agent
owner_action: none
depends_on:
  - TASK_006
allowed_paths:
  - work/tasks/task_007_arc_009.md
traces_to:
  - m02
implements:
  - ARC_CMP_009
---

# TASK_007 — Реализация ARC_CMP_009

## 1. Зачем это делаем

Реализовать эксплуатационные функции системы: логическое состояние планировщика, работоспособности, версии, резервного копирования, восстановления и ограниченных действий восстановления. Без этого компонента невозможно ответить на базовые эксплуатационные вопросы — жива ли система, какая версия развёрнута, есть ли актуальная резервная копия — и нет управляемого способа восстановиться после инцидента.

## 2. Результат

Компонент, предоставляющий логическое состояние планировщика и работоспособности поверх состояния отдельных задач ([`TASK_006`](task_006_arc_007.md)). Физическая топология, средства наблюдения и механизм развёртывания сюда не входят — они принадлежат инфраструктуре ([`INF_CMP_007`](../../specifications/infrastructure_baseline.md#inf_cmp_007), [`INF_CMP_008`](../../specifications/infrastructure_baseline.md#inf_cmp_008), реализуются позже в [`TASK_012`](task_012_inf_007.md), [`TASK_013`](task_013_inf_008.md)) и ADR.

## 3. Где мы сейчас

Спецификация [`ARC_CMP_009`](../../specifications/architecture_baseline.md#arc_cmp_009) определяет требования ([`SYS_013`](../../specifications/system_specification.md#sys_013), [`SYS_024`](../../specifications/system_specification.md#sys_024), [`SYS_025`](../../specifications/system_specification.md#sys_025), [`SYS_026`](../../specifications/system_specification.md#sys_026), [`SYS_027`](../../specifications/system_specification.md#sys_027), [`SYS_030`](../../specifications/system_specification.md#sys_030)). Реализации нет. Зависит от [`TASK_006`](task_006_arc_007.md) (состояние задач) — эксплуатационные функции агрегируют состояние отдельных задач в общесистемную картину.

## 4. Что делать сейчас

### Агенту

1. Изучить спецификацию [`ARC_CMP_009`](../../specifications/architecture_baseline.md#arc_cmp_009)
2. Дополнить `allowed_paths` фактическими путями реализации
3. Создать план реализации
4. Реализовать функциональность и написать TEST с реальным evidence
5. Связать TASK с TEST, который проверяет требования компонента
6. Проверить интеграцию

## 5. План выполнения

- [ ] Изучить требования к [`ARC_CMP_009`](../../specifications/architecture_baseline.md#arc_cmp_009)
- [ ] Дополнить allowed_paths реальными путями
- [ ] Спроектировать реализацию
- [ ] Реализовать компонент
- [ ] Написать TEST, связанный с TASK и требованиями компонента
- [ ] Проверить покрытие путей в allowed_paths

## 6. Состав

**При начале:** агент определит реальные файлы (вероятно `src/operations/`), добавит в `allowed_paths`, создаст TEST.

**Ожидаемые файлы:**
- `src/operations/health.py` — агрегированное состояние работоспособности
- `src/operations/scheduler_state.py` — логическое состояние планировщика
- `work/tests/test_00X.md` — описание проверок

## 7. Проверки и доказательства

**Автоматические:**
1. Все файлы в `allowed_paths` (CI проверяет)
2. Все тесты в связанном TEST проходят
3. MyPy type check успешен
4. Форматирование соответствует

**Ручные (code review):**
1. Компонент не дублирует физическую инфраструктуру (наблюдаемость, развёртывание)
2. Действия восстановления явно ограничены и не дают полного административного доступа
3. Состояние планировщика согласовано с состоянием отдельных задач ([`TASK_006`](task_006_arc_007.md))

## 8. Готово когда

- ✅ Все шаги плана выполнены
- ✅ Локальные проверки успешны
- ✅ CI успешен
- ✅ Код review завершен

## 9. Что будет дальше

Этим завершается блок архитектурных компонентов ([`ARC_CMP_001`](../../specifications/architecture_baseline.md#arc_cmp_001)–[`ARC_CMP_009`](../../specifications/architecture_baseline.md#arc_cmp_009), кроме [`ARC_CMP_002`](../../specifications/architecture_baseline.md#arc_cmp_002), [`ARC_CMP_006`](../../specifications/architecture_baseline.md#arc_cmp_006), [`ARC_CMP_008`](../../specifications/architecture_baseline.md#arc_cmp_008), которые не входят в текущую очередь TASK). [`TASK_008`](task_008_inf_001.md) начинает блок инфраструктурных компонентов с Вычислительной среды выполнения ([`INF_CMP_001`](../../specifications/infrastructure_baseline.md#inf_cmp_001)) — физической или виртуальной основы, на которой запускаются уже реализованные сервисы.

## 10. Что это даёт владельцу

Функционал появится после завершения этой TASK.
