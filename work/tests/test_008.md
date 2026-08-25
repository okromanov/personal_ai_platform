---
id: TEST_008
type: test
title: "ARC_CMP_002 — Контроль владельца: личность, аварийный выключатель, чувствительные действия"
spec_state: current
execution: automated
automated_evidence: quality_suite
version: 1.3
updated: 2026-08-25
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
python3 operations/scripts/quality/run_unittests.py
```

Отдельный прогон только этого компонента:

```bash
python3 -m unittest operations.tests.product.test_owner_control -v
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

## 6. Реализованные компоненты

### Компонент: Контроль владельца

**Стабильный контракт**: `OwnerControl` (абстрактный класс)

- `verify_identity(subject_id: str) → None`: отклонить субъект, не являющийся владельцем (`IdentityRejected`)
- `check_emergency_stop() → None`: отклонить продолжение при активном выключателе (`EmergencyStopActive`)
- `authorize_sensitive_action(action_id, action_descriptor, *, confirmed) → AuthorizationDecision`: авторизовать или отклонить точное действие

**Данные**: `ActionDescriptor`, `AuthorizationDecision`, `ActionClass` (`read`, `write_external`, `destructive`, `admin`)

**Реализация**: `OwnerControlGate`

- Один сконфигурированный владелец (`owner_subject_id`)
- `EmergencySwitch` — файловое хранилище состояния (`<state_dir>/emergency_switch.json`), не зависит от процесса модели или сменной среды агента
- Двухфазный протокол чувствительного действия: запрос регистрирует полный immutable descriptor, подтверждение обязано совпасть с ним
- Durable-защита от дублей: pending и authorized action IDs атомарно сохраняются в `<state_dir>/owner_control_actions.json`

## 7. Структура кода

```
src/owner_control/
├── __init__.py — публичный API
├── base.py — OwnerControl, исключения, ActionClass, AuthorizationDecision
├── emergency_switch.py — EmergencySwitch (файловое состояние)
├── state_io.py — атомарная fail-closed JSON persistence
└── control.py — OwnerControlGate реализация

operations/tests/product/
└── test_owner_control.py — юнит-тесты, часть канонического run_unittests.py (CI/CD)
```

## 8. Соответствие требованиям

| Требование | Статус | Примечание |
|---|---|---|
| [`SYS_002`](../../specifications/system_specification.md#sys_002): Идентичность и контекст полномочий | ✅ | `verify_identity` реализован и покрыт тестами |
| [`SYS_020`](../../specifications/system_specification.md#sys_020): Чувствительные внешние действия | ✅ | Двухфазная авторизация с привязкой к параметрам |
| [`SEC_CTL_001`](../../specifications/system_specification.md#sec_ctl_001): Проверка личности до выполнения задачи | ✅ | Личность не выводится из текста, только из параметра `subject_id` |
| [`SEC_CTL_002`](../../specifications/system_specification.md#sec_ctl_002): Независимый аварийный выключатель | ✅ | Файловое состояние переживает создание нового экземпляра |
| [`SEC_CTL_008`](../../specifications/system_specification.md#sec_ctl_008): Контроль чувствительного внешнего действия | ✅ | Подтверждение привязано к параметрам, дубли отклоняются |
| [`SEC_CTL_020`](../../specifications/system_specification.md#sec_ctl_020): Защита административной идентичности | 🔄 | Код не создаёт отдельного слабого пути для `admin`; реальная MFA на GitHub/площадке — операционная практика вне кода этого компонента |

## 9. Доказательства

- **Исходный код**: [`src/owner_control/`](../../src/owner_control/) — стабильный контракт и файловая реализация
- **Тесты**: 27 юнит-тестов в [`operations/tests/product/test_owner_control.py`](../../operations/tests/product/test_owner_control.py), часть обязательного gate `Quality skills`
- **Отсутствие регрессий**: Запуск `check.py --all` прошёл успешно

## 10. Готово когда

- ✅ 27 тестов пройдено
- ✅ Контракт `OwnerControl` определён и используется
- ✅ `OwnerControlGate` реализован с файловым аварийным выключателем
- ✅ Чувствительные действия авторизуются только по точным параметрам, с защитой от дублей
- ✅ Структура готова для интеграции в [`ARC_CMP_003`](../../specifications/architecture_baseline.md#arc_cmp_003) (Оркестрация)

## 11. Что будет дальше

1. [`TASK_003`](../tasks/task_003_arc_003.md): Реализация [`ARC_CMP_003`](../../specifications/architecture_baseline.md#arc_cmp_003) (Оркестрация и `RuntimePort`) — вызывает `verify_identity` и `check_emergency_stop` на каждом шаге обычного цикла задачи
2. [`TASK_004`](../tasks/task_004_arc_004.md): Реализация [`ARC_CMP_004`](../../specifications/architecture_baseline.md#arc_cmp_004) (Шлюз моделей)
3. [`TASK_005`](../tasks/task_005_arc_005.md): Реализация [`ARC_CMP_005`](../../specifications/architecture_baseline.md#arc_cmp_005) (Шлюз инструментов) — станет основным вызывающим `authorize_sensitive_action` перед внешним действием инструмента
4. Затем интеграция: Telegram → Каналы → Контроль владельца → Оркестрация → Модель

## 12. Примечания для разработчика

- Список владельца и состояние выключателя упрощены для [`m02`](../../milestones.md#m02): локальный файл вместо внешнего секрет-хранилища; production потребует секрет-хранилище и, возможно, несколько уполномоченных идентичностей.
- Полноценный ограниченный административный командный интерфейс ([`SYS_006`](../../specifications/system_specification.md#sys_006)) не входит в эту TASK — появится при сквозной интеграции подэтапа 5 [`m02`](../../milestones.md#m02); этот компонент предоставляет только проверку, которую тот путь обязан вызывать.
- Реальная многофакторная защита административной идентичности ([`SEC_CTL_020`](../../specifications/system_specification.md#sec_ctl_020)) на GitHub/площадке размещения — операционная практика, не код; этот компонент гарантирует лишь отсутствие отдельного более слабого программного пути для административных действий.
- Файловый action ledger рассчитан на текущий одиночный runtime [`m02`](../../milestones.md#m02). Атомарный directory lock блокирует параллельную или неопределённую запись fail-closed; при переходе к распределённому исполнению ledger должен быть перенесён в транзакционное хранилище состояния ([`TASK_006`](../tasks/task_006_arc_007.md), [`ARC_CMP_007`](../../specifications/architecture_baseline.md#arc_cmp_007)).

Действия владельца не требуются: тест полностью автоматизирован и не требует ручного вмешательства.
