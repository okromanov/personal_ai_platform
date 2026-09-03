---
id: TEST_008
type: test
title: "ARC_CMP_002 — Контроль владельца: личность, аварийный выключатель, чувствительные действия"
spec_state: current
execution: automated
automated_evidence: quality_suite
version: 1.4
updated: 2026-09-04
accepts:
  - m02
traces_to:
  - TASK_002
  - SYS_002
  - SYS_020
  - SEC_CTL_001
  - SEC_CTL_002
  - SEC_CTL_008
  - SEC_CTL_020
depends_on: []
---

# TEST_008 — Контроль владельца: личность, аварийный выключатель, чувствительные действия

Автоматическая проверка. Действия владельца не требуются.

## 1. Назначение

Доказать, что компонент [`ARC_CMP_002`](../../specifications/architecture_baseline.md#arc_cmp_002) (Контроль владельца) отклоняет чужую личность, останавливает операции по независимому аварийному выключателю и не допускает чувствительное внешнее действие без явного решения владельца, привязанного к его точным параметрам.

## 2. Что проверяется

Реализация стабильного контракта `OwnerControl` (`src/owner_control/base.py`) и реализации `OwnerControlGate` (`src/owner_control/control.py`) с файловым аварийным выключателем (`src/owner_control/emergency_switch.py`):

- Признанный владелец проходит проверку личности, любой другой субъект отклоняется ([`SEC_CTL_001`](../../specifications/system_specification.md#sec_ctl_001), [`SYS_002`](../../specifications/system_specification.md#sys_002)).
- Состояние аварийного выключателя записывается атомарно, переживает перезапуск и блокирует операции; повреждённый, частичный или семантически неверный state приводит к safe stop ([`SEC_CTL_002`](../../specifications/system_specification.md#sec_ctl_002)).
- Действия классов `write_external`, `destructive`, `admin` требуют подтверждения того же неизменяемого `ActionDescriptor`: субъект, возможность, ресурс, класс, канонические параметры, секреты, сеть, ограничения и ссылка на учётные данные ([`SEC_CTL_008`](../../specifications/system_specification.md#sec_ctl_008), [`SYS_020`](../../specifications/system_specification.md#sys_020)).
- Ожидающие подтверждения и авторизованные идентификаторы сохраняются между перезапусками; повторное использование отклоняется как дубликат ([`SEC_CTL_008`](../../specifications/system_specification.md#sec_ctl_008)).
- Административный путь проверяется тем же контрактом `verify_identity`, без отдельного более слабого правила для `admin`-класса действий ([`SEC_CTL_020`](../../specifications/system_specification.md#sec_ctl_020)).

## 3. Автоматический запуск

Часть канонического прогона юнит-тестов, выполняется в `Quality skills` на каждом push/PR:

```bash
python3.12 operations/scripts/quality/run_unittests.py
```

Отдельный прогон только этого компонента:

```bash
python3.12 -m unittest operations.tests.product.test_owner_control -v
```

## 4. Критерий успеха

Все 27 тестов проходят, включая сценарии:

- ✓ identity — признанный владелец принят, любой другой субъект и пустая личность отклонены
- ✓ emergency_switch — по умолчанию не активен, включение блокирует, выключение снимает блокировку
- ✓ emergency_switch_survives_restart — новый экземпляр компонента с тем же каталогом состояния видит ранее установленное состояние
- ✓ sensitive_action — `READ` авторизуется сразу; `WRITE_EXTERNAL`/`DESTRUCTIVE`/`ADMIN` без подтверждения отклоняются
- ✓ sensitive_action_confirmation — подтверждение связано с полным descriptor; подмена ресурса или возможности отклоняется
- ✓ sensitive_action_dedup — повторное использование того же `action_id` после авторизации и перезапуска отклоняется
- ✓ fail_closed_state — повреждённое состояние выключателя, action ledger или lock блокирует продолжение

## 5. Состав доказательства

`automated_evidence: quality_suite`. Каждый запуск канонического набора юнит-тестов создаёт доказательство выполнения всех 27 тестов на текущем Git SHA. Результат успеха фиксируется в evidence записи с временем выполнения и версией платформы.
