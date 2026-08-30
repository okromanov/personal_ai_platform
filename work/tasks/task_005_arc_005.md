---
id: TASK_005
type: task
title: Реализация ARC_CMP_005
component: ARC_CMP_005
work_state: completed
version: 2.2
updated: 2026-08-30
next_actor: none
owner_action: none
depends_on:
  - TASK_004
allowed_paths:
  - work/tasks/task_005_arc_005.md
  - src/tools/
  - src/tools/__init__.py
  - src/tools/base.py
  - src/tools/registry.py
  - operations/tests/product/test_tool_gateway.py
  - work/tests/test_011.md
  - operations/tests/test_owner_usability.py
traces_to:
  - m02
implements:
  - ARC_CMP_005
tests:
  - TEST_011
---

# TASK_005 — Реализация ARC_CMP_005

## 1. Зачем это делаем

Реализовать единую точку технической авторизации вызовов инструментов. Без этого компонента любой код, вызывающий инструмент (файловую систему, сеть, внешний API), должен сам проверять, разрешено ли действие — это невозможно проверить и легко обойти. Шлюз инструментов централизует контракт возможности: разрешённый субъект, ресурс, область, класс воздействия, данные, секреты, сеть, ограничения, подтверждение и защиту от дублей.

## 2. Результат

Стабильный контракт `ToolGateway` (`src/tools/base.py`) и эталонная реализация `ToolGatewayImpl` (`src/tools/registry.py`), через которую проходит каждый вызов инструмента. Зарегистрированная возможность фиксирует разрешённых субъектов, ресурсы, имена параметров, ссылки на секреты, сетевые назначения, ограничения, учётные данные и класс воздействия. Полное неизменяемое описание действия передаётся в [`OwnerControl`](task_002_arc_002.md) ([`ARC_CMP_002`](../../specifications/architecture_baseline.md#arc_cmp_002)); аварийное состояние проверяется до авторизации и непосредственно перед dispatch. MCP и другие протоколы интеграции остаются лишь способом подключения, а не источником полномочий.

## 3. Где мы сейчас

Спецификация и реализация [`ARC_CMP_005`](../../specifications/architecture_baseline.md#arc_cmp_005) полностью завершены и покрыты [`TEST_011`](../tests/test_011.md) в части технической авторизации ([`SEC_CTL_007`](../../specifications/system_specification.md#sec_ctl_007)) и контроля чувствительного действия ([`SEC_CTL_008`](../../specifications/system_specification.md#sec_ctl_008)). Изолированное выполнение кода ([`SEC_CTL_009`](../../specifications/system_specification.md#sec_ctl_009)) не входит в эту TASK — оно требует рабочей области задачи ([`INF_CMP_004`](../../specifications/infrastructure_baseline.md#inf_cmp_004)), которая вне очереди [`m02`](../../milestones.md#m02).

## 4. Что делать сейчас

### Агенту

Работа завершена, следующего действия по этой TASK нет.

## 5. План выполнения

- [x] Изучить требования к [`ARC_CMP_005`](../../specifications/architecture_baseline.md#arc_cmp_005)
- [x] Дополнить allowed_paths реальными путями
- [x] Спроектировать реализацию
- [x] Реализовать компонент
- [x] Написать [`TEST_011`](../tests/test_011.md), связанный с TASK и требованиями компонента
- [x] Проверить покрытие путей в allowed_paths

## 6. Состав

[`src/tools/`](../../src/tools/) — стабильный контракт `ToolGateway` ([`base.py`](../../src/tools/base.py)) и эталонная реализация `ToolGatewayImpl` ([`registry.py`](../../src/tools/registry.py)), авторизующая каждый вызов через [`OwnerControl`](task_002_arc_002.md) перед выполнением. [`work/tests/test_011.md`](../tests/test_011.md) — описание проверок компонента. [`operations/tests/product/test_tool_gateway.py`](../../operations/tests/product/test_tool_gateway.py) — юнит-тесты, проверяющие компонент.

## 7. Проверки и доказательства

Автоматическая проверка подтверждает, что все изменённые пути входят в `allowed_paths`. Требования компонента проверяет [`TEST_011`](../tests/test_011.md): юнит-тесты [`operations/tests/product/test_tool_gateway.py`](../../operations/tests/product/test_tool_gateway.py), часть обязательного gate `Quality skills`.

Ручная проверка при код-ревью: авторизация проверяется до выполнения вызова (обработчик не вызывается при отказе — подтверждено тестом); класс воздействия фиксирован на возможности и не читается из параметров вызова или метаданных обнаружения; защита от дублей делегирована [`OwnerControl.authorize_sensitive_action`](task_002_arc_002.md), а не продублирована.

## 8. Готово когда

- ✅ Все шаги плана выполнены
- ✅ Локальные проверки успешны ([`operations/tests/product/test_tool_gateway.py`](../../operations/tests/product/test_tool_gateway.py): 17/17 тестов прошли, часть CI gate)
- ✅ Pre-commit валидация успешна
- ✅ CI успешен
- ✅ Код review (смысловая проверка) пройден

## 9. Что будет дальше

[`TASK_006`](task_006_arc_007.md) реализует Состояние задач ([`ARC_CMP_007`](../../specifications/architecture_baseline.md#arc_cmp_007)) — компонент, который отслеживает жизненный цикл задачи, пока оркестратор вызывает модель ([`TASK_004`](task_004_arc_004.md)) и инструменты (`TASK_005`). Три компонента вместе образуют рабочий цикл выполнения задачи.

## 10. Что это даёт владельцу

Пока напрямую ничего не доступно: это контракт и точка авторизации, а не подключённый реальный инструмент. Вызов проверяет личность, полный policy возможности, аварийное состояние и точное подтверждённое действие; подтверждение нельзя перенести на другой ресурс или возможность, а дубликат остаётся заблокирован после перезапуска. Реальные инструменты появятся в следующих TASK.
