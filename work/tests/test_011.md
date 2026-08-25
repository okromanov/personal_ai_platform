---
id: TEST_011
type: test
title: "ARC_CMP_005 — Шлюз инструментов: техническая авторизация вызова"
spec_state: current
execution: automated
automated_evidence: quality_suite
version: 1.0
updated: 2026-08-25
accepts:
  - m02
traces_to:
  - TASK_005
  - SYS_020
  - SYS_021
depends_on:
  - TEST_009
---

# TEST_011 — Шлюз инструментов: техническая авторизация вызова

Автоматическая проверка. Действия владельца не требуются.

## 1. Назначение

Доказать, что компонент [`ARC_CMP_005`](../../specifications/architecture_baseline.md#arc_cmp_005) (Шлюз инструментов) является единой точкой технической авторизации вызова инструмента: разрешённый ресурс и класс воздействия проверяются до выполнения, чувствительное действие требует решения владельца через [`OwnerControl`](../tasks/task_002_arc_002.md) ([`ARC_CMP_002`](../../specifications/architecture_baseline.md#arc_cmp_002)), а повтор не создаёт второй эффект.

## 2. Что проверяется

Реализация стабильного контракта `ToolGateway` (`src/tools/base.py`) и эталонной реализации `ToolGatewayImpl` (`src/tools/registry.py`):

- Возможность класса `READ` авторизуется немедленно, без подтверждения владельца.
- Возможность чувствительного класса (`WRITE_EXTERNAL`, `DESTRUCTIVE`, `ADMIN`) при первом вызове без подтверждения отклоняется, а обработчик инструмента не вызывается ([`SEC_CTL_008`](../../specifications/system_specification.md#sec_ctl_008)).
- Повторный вызов с тем же `action_id`/параметрами и `confirmed=True` авторизуется и выполняется.
- Третий вызов с тем же `action_id` после авторизации отклоняется как дубликат — повтор не создаёт второй эффект ([`SEC_CTL_008`](../../specifications/system_specification.md#sec_ctl_008)).
- Неизвестная возможность и ресурс вне списка разрешённых для возможности отклоняются без вызова обработчика.
- Класс воздействия, заявленный в параметрах вызова, не может подменить зарегистрированный класс возможности — авторизация управляется только тем, что было зарегистрировано технической стороной, а не тем, что утверждает вызывающая сторона или обнаруженные метаданные инструмента ([`SEC_CTL_007`](../../specifications/system_specification.md#sec_ctl_007)).
- Сбой самого обработчика инструмента поднимает отдельное, отличимое от отказа авторизации исключение `ToolGatewayError`.

## 3. Автоматический запуск

Часть канонического прогона юнит-тестов, выполняется в `Quality skills` на каждом push/PR:

```bash
python3 operations/scripts/quality/run_unittests.py
```

Отдельный прогон только этого компонента:

```bash
python3 -m unittest operations.tests.product.test_tool_gateway -v
```

## 4. Критерий успеха

Все 9 тестов проходят, включая сценарии:

- ✓ read_capability_authorized_immediately_without_confirmation — класс `READ` не требует подтверждения
- ✓ sensitive_capability_requires_confirmation_first — первый вызов чувствительной возможности отклонён, обработчик не вызван
- ✓ sensitive_capability_authorized_on_matching_confirmation — подтверждённый повтор с теми же параметрами выполняется
- ✓ duplicate_action_id_rejected_after_authorization — повторное использование `action_id` после авторизации отклонено
- ✓ unknown_capability_returns_failed_result — неизвестная возможность отклонена
- ✓ resource_outside_allowlist_is_denied — ресурс вне списка разрешённых отклонён, обработчик не вызван
- ✓ capability_effect_class_cannot_be_overridden_by_call_params — параметры вызова не подменяют зарегистрированный класс воздействия
- ✓ handler_exception_raises_tool_gateway_error — сбой обработчика поднимает `ToolGatewayError`
- ✓ tool_gateway_error_is_a_distinct_type — тип исключения различим

## 5. Состав доказательства

`automated_evidence: quality_suite`. Каждый запуск канонического набора юнит-тестов создаёт доказательство выполнения всех 9 тестов на текущем Git SHA. Результат успеха фиксируется в evidence записи с временем выполнения и версией платформы.

## 6. Реализованные компоненты

### Компонент: Шлюз инструментов

**Стабильный контракт**: `ToolGateway` (абстрактный класс)

- `async call(tool_call: ToolCall) → ToolResult`: авторизовать и выполнить один вызов инструмента

**Данные**: `ToolCall` (`action_id`, `capability_name`, `resource`, `params`, `confirmed`), `ToolResult` (`output`, `succeeded`, `error_message`), исключение `ToolGatewayError` (инструмент недоступен или упал)

**Эталонная реализация**: `ToolGatewayImpl` — регистрирует список `Capability` (`name`, `effect_class`, `handler`, `allowed_resources`) и на каждом вызове: (1) проверяет существование возможности, (2) проверяет ресурс против `allowed_resources`, (3) передаёт `effect_class` возможности и параметры вызова в [`OwnerControl.authorize_sensitive_action`](../tasks/task_002_arc_002.md), (4) выполняет `handler` только при положительном решении.

## 7. Структура кода

```
src/tools/
├── __init__.py — публичный API
├── base.py — ToolGateway, ToolGatewayError, ToolCall, ToolResult
└── registry.py — Capability, ToolGatewayImpl, ToolHandler

operations/tests/product/
└── test_tool_gateway.py — юнит-тесты, часть канонического run_unittests.py (CI/CD)
```

## 8. Соответствие требованиям

| Требование | Статус | Примечание |
|---|---|---|
| [`SYS_020`](../../specifications/system_specification.md#sys_020): Чувствительные внешние действия | ✅ | Чувствительный класс требует подтверждения владельца с привязкой к точным параметрам; повтор не создаёт второй эффект |
| [`SYS_021`](../../specifications/system_specification.md#sys_021): Исполнение кода и преобразование данных | ➖ | Изолированное выполнение кода/риск разбора ([`SEC_CTL_009`](../../specifications/system_specification.md#sec_ctl_009)) требует рабочей области задачи ([`INF_CMP_004`](../../specifications/infrastructure_baseline.md#inf_cmp_004)), вне очереди [`m02`](../../milestones.md#m02) — эта TASK проверяет только техническую авторизацию вызова, не песочницу исполнения |
| [`SEC_CTL_007`](../../specifications/system_specification.md#sec_ctl_007): Техническая авторизация инструмента | ✅ | Проверяются возможность, ресурс и обязательный `effect_class`; обнаружение инструмента и параметры вызова не создают и не ослабляют авторизацию |
| [`SEC_CTL_008`](../../specifications/system_specification.md#sec_ctl_008): Контроль чувствительного внешнего действия | ✅ | Решение владельца привязано к точным параметрам; защита от дублей подтверждена тестом |

## 9. Доказательства

- **Исходный код**: [`src/tools/`](../../src/tools/) — стабильный контракт и эталонная реализация
- **Тесты**: 9 юнит-тестов в [`operations/tests/product/test_tool_gateway.py`](../../operations/tests/product/test_tool_gateway.py), часть обязательного gate `Quality skills`
- **Отсутствие регрессий**: Запуск `check.py --all` прошёл успешно

## 10. Готово когда

- ✅ 9 тестов пройдено
- ✅ Контракт `ToolGateway` определён и используется
- ✅ Авторизация чувствительного действия подтверждена через [`OwnerControl`](../tasks/task_002_arc_002.md) без дублирования его логики
- ✅ Защита от дублей подтверждена тестом

## 11. Что будет дальше

1. [`TASK_006`](../tasks/task_006_arc_007.md): Реализация [`ARC_CMP_007`](../../specifications/architecture_baseline.md#arc_cmp_007) (Состояние задач) — контрольные точки и возобновление после сбоя поверх цикла, использующего этот шлюз
2. Изолированное выполнение кода и рискованного разбора ([`SEC_CTL_009`](../../specifications/system_specification.md#sec_ctl_009)) остаётся отдельной работой, зависящей от рабочей области задачи ([`INF_CMP_004`](../../specifications/infrastructure_baseline.md#inf_cmp_004)), вне очереди [`m02`](../../milestones.md#m02)
3. Реальные интеграции инструментов (MCP-серверы, файловая система, внешние API) остаются отдельной работой: эта TASK строит контракт и точку авторизации, а не боевую проводку — как [`TASK_001`](../tasks/task_001_arc_001.md)–[`TASK_004`](../tasks/task_004_arc_004.md)

## 12. Примечания для разработчика

- `ToolGatewayImpl` — не заготовка конкретной интеграции: `Capability.handler` в тестах — простые функции, а не реальные обращения к файловой системе, сети или MCP-серверу.
- Решение "разрешено/отклонено" для чувствительного класса целиком делегировано [`OwnerControl.authorize_sensitive_action`](../tasks/task_002_arc_002.md) ([`TASK_002`](../tasks/task_002_arc_002.md)) — `ToolGatewayImpl` не хранит и не повторяет эту логику самостоятельно, чтобы не было двух независимых источников решения "разрешено ли чувствительное действие".

Действия владельца не требуются: тест полностью автоматизирован и не требует ручного вмешательства.
