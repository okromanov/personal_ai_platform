---
id: TASK_004
type: task
title: Реализация ARC_CMP_004
component: ARC_CMP_004
work_state: completed
version: 2.2
updated: 2026-09-02
next_actor: none
owner_action: none
depends_on:
  - TASK_003
allowed_paths:
  - work/tasks/task_004_arc_004.md
  - src/models/
  - src/models/__init__.py
  - src/models/base.py
  - src/models/stub_gateway.py
  - src/models/runtime_adapter.py
  - operations/tests/product/test_model_gateway.py
  - work/tests/test_010.md
traces_to:
  - m02
implements:
  - ARC_CMP_004
tests:
  - TEST_010
---

# TASK_004 — Реализация ARC_CMP_004

## 1. Зачем это делаем

Реализовать единый шлюз к языковым моделям — нормализованный контракт запросов, ответов, ошибок и доступных показателей модели. Без этого компонента каждая часть системы, вызывающая модель, должна знать особенности конкретного поставщика (формат запроса, коды ошибок, лимиты), и смена поставщика или добавление второго требует правок по всему коду. Шлюз изолирует эту специфику в одном месте.

## 2. Результат

Стабильный контракт `ModelGateway` (`src/models/base.py`), нормализующий запрос/ответ/ошибку/показатели использования в единый формат, и адаптер `ModelBackedRuntimePort` (`src/models/runtime_adapter.py`), позволяющий оркестратору ([`TASK_003`](task_003_arc_003.md)) вызывать модель через границу `RuntimePort` без единого изменения самого оркестратора. Конкретный поставщик модели (например, Anthropic Claude) ещё не выбран — сравнение кандидатов зафиксировано как `proposed` в [`ADR_005`](../../adr/adr_005_first_model_provider_selection.md) и не входит в эту TASK; здесь подключается тестовый переходный слой `StubModelGateway`, соответствующий контракту `ModelGateway` из [`ADR_003`](../../adr/adr_003_model_provider_interface.md).

## 3. Где мы сейчас

Спецификация и реализация [`ARC_CMP_004`](../../specifications/architecture_baseline.md#arc_cmp_004) полностью завершены и покрыты [`TEST_010`](../tests/test_010.md). Не зависит от выбора реального поставщика: как и `RuntimePort` в [`TASK_003`](task_003_arc_003.md), контракт `ModelGateway` проверен тестовым переходным слоем, а подключение поставщика остаётся отдельной работой подэтапа 4 [`m02`](../../milestones.md#m02) с использованием хранилища секретов из [`TASK_010`](task_010_inf_003.md).

## 4. Что делать сейчас

### Агенту

Работа завершена, следующего действия по этой TASK нет.

## 5. План выполнения

- [x] Изучить требования к [`ARC_CMP_004`](../../specifications/architecture_baseline.md#arc_cmp_004)
- [x] Дополнить allowed_paths реальными путями
- [x] Спроектировать реализацию
- [x] Реализовать компонент
- [x] Написать [`TEST_010`](../tests/test_010.md), связанный с TASK и требованиями компонента
- [x] Проверить покрытие путей в allowed_paths

## 6. Состав

[`src/models/`](../../src/models/) — стабильный контракт `ModelGateway` ([`base.py`](../../src/models/base.py)), тестовый переходный слой `StubModelGateway` ([`stub_gateway.py`](../../src/models/stub_gateway.py)) и адаптер к границе `RuntimePort` `ModelBackedRuntimePort` ([`runtime_adapter.py`](../../src/models/runtime_adapter.py)). [`work/tests/test_010.md`](../tests/test_010.md) — описание проверок компонента. [`operations/tests/product/test_model_gateway.py`](../../operations/tests/product/test_model_gateway.py) — юнит-тесты, проверяющие компонент, включая полный цикл задачи через [`Orchestrator`](task_003_arc_003.md).

## 7. Проверки и доказательства

Автоматическая проверка подтверждает, что все изменённые пути входят в `allowed_paths`. Требования компонента проверяет [`TEST_010`](../tests/test_010.md): юнит-тесты [`operations/tests/product/test_model_gateway.py`](../../operations/tests/product/test_model_gateway.py), часть обязательного gate `Quality skills`.

Ручная проверка при код-ревью: `ModelGateway` не содержит специфики конкретного поставщика и не импортирует SDK; ошибки нормализованы в `ModelResponse`/`ModelGatewayError`, а не проброшены как есть; секреты (API-ключи) в коде отсутствуют — реального поставщика ещё нет.

## 8. Готово когда

- ✅ Все шаги плана выполнены
- ✅ Локальные проверки успешны ([`operations/tests/product/test_model_gateway.py`](../../operations/tests/product/test_model_gateway.py): 11/11 тестов прошли, часть CI gate)
- ✅ Pre-commit валидация успешна
- ✅ CI успешен
- ✅ Код review (смысловая проверка) пройден

## 9. Что будет дальше

[`TASK_005`](task_005_arc_005.md) реализует Шлюз инструментов ([`ARC_CMP_005`](../../specifications/architecture_baseline.md#arc_cmp_005)) — второй ключевой шлюз, необходимый оркестратору для полного цикла выполнения задачи (модель рассуждает, инструмент действует). После `TASK_004` и [`TASK_005`](task_005_arc_005.md) оркестратор из [`TASK_003`](task_003_arc_003.md) получает оба внешних контракта, нужных для реального выполнения задач.

## 10. Что это даёт владельцу

Пока напрямую ничего не доступно: контракт и тестовый переходный слой, а не реальный доступ к модели. Оркестратор теперь может завершить цикл задачи, вызвав шлюз моделей, а не только эхо-ответ, — но ответ пока детерминированный (тестовая заглушка), не от реальной языковой модели. Реальное подключение поставщика появится после сравнительного evidence и решения владельца по [`ADR_005`](../../adr/adr_005_first_model_provider_selection.md).
