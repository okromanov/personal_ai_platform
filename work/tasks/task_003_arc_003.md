---
id: TASK_003
type: task
title: Реализация ARC_CMP_003
component: ARC_CMP_003
work_state: completed
version: 1.9
updated: 2026-08-25
next_actor: none
owner_action: none
depends_on:
  - TASK_002
allowed_paths:
  - work/tasks/task_003_arc_003.md
  - src/orchestration/
  - src/orchestration/__init__.py
  - src/orchestration/runtime_port.py
  - src/orchestration/stub_runtime.py
  - src/orchestration/orchestrator.py
  - operations/tests/product/test_orchestration.py
  - work/tests/test_009.md
traces_to:
  - m02
implements:
  - ARC_CMP_003
tests:
  - TEST_009
---

# TASK_003 — Реализация ARC_CMP_003

## 1. Зачем это делаем

Реализовать оркестрацию задач и границу `RuntimePort` — слой, который превращает принятую задачу (нормализованную [`TASK_001`](task_001_arc_001.md)) в исполнимый цикл: проверяет личность и правила владельца ([`TASK_002`](task_002_arc_002.md)), подключает конкретную среду выполнения агента через стабильный контракт и возвращает ответ через канал. Без этого компонента система не может довести задачу от «принята» до «выполняется»: некому решить, какая среда агента обрабатывает задачу, и как переключить реализацию, не затронув остальную систему.

## 2. Результат

Стабильный контракт `RuntimePort` и `Orchestrator`, который проводит `TaskMessage` от [`TASK_001`](task_001_arc_001.md) через обычный цикл задачи ([`ARC_FLOW_001`](../../specifications/architecture_baseline.md#arc_flow_001)): проверка личности и аварийного выключателя через [`OwnerControl`](task_002_arc_002.md) → отметка состояния → выполнение через подключённый `RuntimePort` → отметка результата → ответ через канал. Конкретная среда агента (Claude Agent SDK или альтернатива) ещё не выбрана — сравнение кандидатов зафиксировано как `proposed` в [`ADR_006`](../../adr/adr_006_agent_environment_framework.md) и не входит в эту TASK; здесь подключается тестовый переходный слой, соответствующий контракту `RuntimePort` из [`ADR_002`](../../adr/adr_002_core_runtime_boundary.md)§6.

## 3. Где мы сейчас

Спецификация и реализация [`ARC_CMP_003`](../../specifications/architecture_baseline.md#arc_cmp_003) полностью завершены и покрыты [`TEST_009`](../tests/test_009.md). Не зависит от хранения состояния задачи ([`ARC_CMP_007`](../../specifications/architecture_baseline.md#arc_cmp_007), [`TASK_006`](task_006_arc_007.md)): та TASK ещё не выполнена и отвечает за отдельную заботу — контрольные точки, повтор и возобновление после сбоя, а не за проведение задачи через один цикл выполнения.

## 4. Что делать сейчас

### Агенту

Работа завершена, следующего действия по этой TASK нет.

## 5. План выполнения

- [x] Изучить требования к [`ARC_CMP_003`](../../specifications/architecture_baseline.md#arc_cmp_003)
- [x] Дополнить allowed_paths реальными путями
- [x] Спроектировать реализацию
- [x] Реализовать компонент
- [x] Написать TEST, связанный с TASK и требованиями компонента
- [x] Проверить покрытие путей в allowed_paths

## 6. Состав

[`src/orchestration/`](../../src/orchestration/) — стабильный контракт `RuntimePort` ([`runtime_port.py`](../../src/orchestration/runtime_port.py)), тестовый переходный слой `StubRuntimePort` ([`stub_runtime.py`](../../src/orchestration/stub_runtime.py)) и `Orchestrator` ([`orchestrator.py`](../../src/orchestration/orchestrator.py)), проводящий задачу через [`ARC_FLOW_001`](../../specifications/architecture_baseline.md#arc_flow_001). [`work/tests/test_009.md`](../tests/test_009.md) — описание проверок компонента. [`operations/tests/product/test_orchestration.py`](../../operations/tests/product/test_orchestration.py) — юнит-тесты, проверяющие компонент.

## 7. Проверки и доказательства

Автоматическая проверка подтверждает, что все изменённые пути входят в `allowed_paths`. Требования компонента проверяет [`TEST_009`](../tests/test_009.md): юнит-тесты [`operations/tests/product/test_orchestration.py`](../../operations/tests/product/test_orchestration.py), часть обязательного gate `Quality skills`.

Ручная проверка при код-ревью: `RuntimePort` не содержит специфики конкретной среды агента и не импортирует SDK; `Orchestrator` не хранит секреты, правила владельца или каноническую долговременную память напрямую — обращается к [`OwnerControl`](task_002_arc_002.md) за каждой проверкой.

## 8. Готово когда

- ✅ Все шаги плана выполнены
- ✅ Локальные проверки успешны ([`operations/tests/product/test_orchestration.py`](../../operations/tests/product/test_orchestration.py): 10/10 тестов прошли, часть CI gate)
- ✅ Pre-commit валидация успешна
- ✅ CI успешен
- ✅ Код review (смысловая проверка) пройден

## 9. Что будет дальше

`TASK_004` реализует Шлюз моделей (`ARC_CMP_004`) — нормализованный доступ к LLM, который тестовый переходный слой (а затем и выбранная среда агента) будет вызывать в цикле выполнения задачи. `TASK_005` реализует Шлюз инструментов (`ARC_CMP_005`), необходимый оркестратору для авторизованных вызовов инструментов.

## 10. Что это даёт владельцу

Пока напрямую ничего не доступно: это внутренний цикл выполнения, а не готовый к использованию сценарий. Сообщение, прошедшее проверку личности, теперь доводится до конца одним предсказуемым путём — выполнено, провалено с понятной причиной или отменено, а не зависает и не теряется где-то между приёмом и ответом. Отменённая по чужой личности или по аварийному выключателю задача получает понятный ответ, а не тишину. Реального ответа модели и подключения к боевому Telegram ещё нет: пока используется тестовая заглушка среды выполнения, реальная среда и модель появятся в следующих TASK.
