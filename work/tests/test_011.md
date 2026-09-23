---
id: TEST_011
type: test
title: "ARC_CMP_005 — Шлюз инструментов: техническая авторизация вызова"
spec_state: current
execution: automated
automated_evidence: quality_suite
version: 1.3
updated: 2026-09-23
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
- Повторный вызов с тем же полным descriptor и `confirmed=True` авторизуется и выполняется.
- Подмена субъекта, возможности, ресурса, параметров, секрета или сети отклоняется; подтверждение не переносится на другое действие.
- Третий вызов с тем же `action_id` после авторизации отклоняется как дубликат, в том числе после перезапуска ([`SEC_CTL_008`](../../specifications/system_specification.md#sec_ctl_008)).
- Аварийный выключатель проверяется до авторизации и непосредственно перед handler; включение в любом из этих окон не допускает внешний эффект ([`SEC_CTL_002`](../../specifications/system_specification.md#sec_ctl_002)).
- Неизвестная возможность и ресурс вне списка разрешённых для возможности отклоняются без вызова обработчика.
- Каждая возможность, включая класс `READ`, явно перечисляет разрешённые ресурсы: пустой список отклоняется при регистрации и не работает как неявное разрешение любого ресурса ([`SEC_CTL_003`](../../specifications/system_specification.md#sec_ctl_003), [`SEC_CTL_007`](../../specifications/system_specification.md#sec_ctl_007)).
- Повторное имя возможности отклоняется при сборке шлюза: одна привязка не может молча заменить проверенную политику и обработчик другой.
- Класс воздействия, заявленный в параметрах вызова, не может подменить зарегистрированный класс возможности — авторизация управляется только тем, что было зарегистрировано технической стороной, а не тем, что утверждает вызывающая сторона или обнаруженные метаданные инструмента ([`SEC_CTL_007`](../../specifications/system_specification.md#sec_ctl_007)).
- Сбой самого обработчика инструмента поднимает отдельное, отличимое от отказа авторизации исключение `ToolGatewayError`.

## 3. Автоматический запуск

Часть канонического прогона юнит-тестов, выполняется в `Quality skills` на каждом push/PR:

```bash
python3.12 operations/scripts/quality/run_unittests.py
```

Отдельный прогон только этого компонента:

```bash
python3.12 -m unittest operations.tests.product.test_tool_gateway -v
```

## 4. Критерий успеха

Проходят все 21 тест, включая сценарии:

- ✓ read_capability_authorized_immediately_without_confirmation — класс `READ` не требует подтверждения
- ✓ sensitive_capability_requires_confirmation_first — первый вызов чувствительной возможности отклонён, обработчик не вызван
- ✓ matching_confirmation_executes_once — подтверждённый повтор с тем же descriptor выполняется один раз
- ✓ confirmation substitution — другой resource или capability отклоняется
- ✓ kill-switch race — включение до подтверждения или после авторизации блокирует handler
- ✓ duplicate after restart — повторное использование `action_id` после перезапуска отклонено
- ✓ unknown_capability_returns_failed_result — неизвестная возможность отклонена
- ✓ resource_outside_allowlist_is_denied — ресурс вне списка разрешённых отклонён, обработчик не вызван
- ✓ read_capability_requires_explicit_resources — возможность `READ` без списка ресурсов отклонена при регистрации
- ✓ duplicate_capability_names_are_rejected — повторное имя возможности отклонено при сборке шлюза
- ✓ capability_effect_class_cannot_be_overridden_by_call_params — параметры вызова не подменяют зарегистрированный класс воздействия
- ✓ handler_exception_raises_tool_gateway_error — сбой обработчика поднимает `ToolGatewayError`
- ✓ tool_gateway_error_is_a_distinct_type — тип исключения различим

## 5. Состав доказательства

`automated_evidence: quality_suite`. Каждый запуск канонического набора юнит-тестов создаёт доказательство выполнения всех 21 теста на текущем Git SHA. Результат успеха фиксируется в evidence записи с временем выполнения и версией платформы.
