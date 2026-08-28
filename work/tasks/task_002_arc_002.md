---
id: TASK_002
type: task
title: Реализация ARC_CMP_002
component: ARC_CMP_002
work_state: completed
version: 1.7
updated: 2026-08-28
next_actor: none
owner_action: none
depends_on:
  - TASK_001
allowed_paths:
  - work/tasks/task_002_arc_002.md
  - src/owner_control/
  - src/owner_control/__init__.py
  - src/owner_control/base.py
  - src/owner_control/emergency_switch.py
  - src/owner_control/control.py
  - operations/tests/product/test_owner_control.py
  - work/tests/test_008.md
traces_to:
  - m02
implements:
  - ARC_CMP_002
tests:
  - TEST_008
---

# TASK_002 — Реализация ARC_CMP_002

## 1. Зачем это делаем

Реализовать контроль владельца: проверку личности до выполнения задачи, независимый аварийный выключатель, контроль чувствительного внешнего действия и защиту административной идентичности. Без этого компонента любой субъект может запустить задачу от имени владельца, а аварийная остановка зависела бы от состояния модели или сменной среды агента — то есть переставала бы быть независимой. Это единственный компонент, который другие компоненты (оркестрация, шлюз инструментов) обязаны спрашивать перед стартом и продолжением задачи и перед чувствительным внешним действием.

**Примечание о версии 1.2:** предыдущая редакция этой карточки ошибочно описывала «хранилище задач» (Task Storage) вместо контроля владельца, хотя `component`/`implements` уже указывали на [`ARC_CMP_002`](../../specifications/architecture_baseline.md#arc_cmp_002). [`ARC_CMP_002`](../../specifications/architecture_baseline.md#arc_cmp_002) в [`specifications/architecture_baseline.md`](../../specifications/architecture_baseline.md) — это «Контроль владельца», а не хранилище задач; хранение личности и жизненного цикла исполняемой задачи относится к [`ARC_CMP_007`](../../specifications/architecture_baseline.md#arc_cmp_007) ([`TASK_006`](task_006_arc_007.md)). Версия 1.3 приводит карточку в соответствие со спецификацией и [`TEST_007`](../tests/test_007.md)§11, который уже до этого правильно называл следующим шагом «Контроль владельца».

## 2. Результат

Стабильный контракт `OwnerControl` (`src/owner_control/base.py`) и рабочая реализация `OwnerControlGate` (`src/owner_control/control.py`):

- **Проверка личности** ([`SEC_CTL_001`](../../specifications/system_specification.md#sec_ctl_001)): субъект, не входящий в список владельца, отклоняется до вызова модели или инструмента; личность не выводится из текста сообщения.
- **Независимый аварийный выключатель** ([`SEC_CTL_002`](../../specifications/system_specification.md#sec_ctl_002)): состояние атомарно хранится в файле вне процесса модели и сменной среды агента, переживает перезапуск, а повреждённое или нечитаемое состояние приводит к безопасной остановке.
- **Контроль чувствительного внешнего действия** ([`SEC_CTL_008`](../../specifications/system_specification.md#sec_ctl_008)): действия классов `write_external`, `destructive`, `admin` требуют явного решения владельца, привязанного к неизменяемому полному описанию действия; ожидающие и уже авторизованные `action_id` сохраняются между перезапусками.
- **Защита административной идентичности** ([`SEC_CTL_020`](../../specifications/system_specification.md#sec_ctl_020)): административный путь проверяется тем же контрактом `verify_identity`, без отдельного более слабого правила для `admin`-класса действий; фактическая многофакторная аутентификация на GitHub/площадке — операционная практика вне кода этого компонента (см. §12 в [`TEST_008`](../tests/test_008.md)).

Реализация упрощена для [`m02`](../../milestones.md#m02): список владельца и аварийный выключатель используют локальный файл вместо внешнего секрет-хранилища; полноценный административный командный интерфейс ([`SYS_006`](../../specifications/system_specification.md#sys_006)) появится при сквозной интеграции подэтапа 5 [`m02`](../../milestones.md#m02), а не в этой TASK.

## 3. Где мы сейчас

Спецификация и реализация [`ARC_CMP_002`](../../specifications/architecture_baseline.md#arc_cmp_002) завершены и покрыты [`TEST_008`](../tests/test_008.md), включая отрицательные сценарии повреждения состояния, подмены ресурса и повторного исполнения после перезапуска. Запись критичного JSON-состояния синхронизирует сначала файл, затем замену directory entry на POSIX; ошибка любого durability barrier не маскируется как успешная запись. На Windows используется доступная платформе семантика `os.replace`, поскольку переносимого directory-fsync API в Python нет.

## 4. Что делать сейчас

### Агенту

Работа завершена, следующего действия по этой TASK нет.

## 5. План выполнения

- [x] Изучить требования к [`ARC_CMP_002`](../../specifications/architecture_baseline.md#arc_cmp_002)
- [x] Дополнить allowed_paths реальными путями
- [x] Спроектировать реализацию
- [x] Реализовать компонент
- [x] Написать TEST, связанный с TASK и требованиями компонента
- [x] Проверить покрытие путей в allowed_paths

## 6. Состав

[`src/owner_control/`](../../src/owner_control/) — стабильный контракт `OwnerControl` ([`base.py`](../../src/owner_control/base.py)), файловый аварийный выключатель ([`emergency_switch.py`](../../src/owner_control/emergency_switch.py)) и реализация `OwnerControlGate` ([`control.py`](../../src/owner_control/control.py)). [`work/tests/test_008.md`](../tests/test_008.md) — описание проверок компонента. [`operations/tests/product/test_owner_control.py`](../../operations/tests/product/test_owner_control.py) — юнит-тесты, проверяющие компонент.

## 7. Проверки и доказательства

Автоматическая проверка подтверждает, что все изменённые пути входят в `allowed_paths`. Требования компонента проверяет [`TEST_008`](../tests/test_008.md): юнит-тесты [`operations/tests/product/test_owner_control.py`](../../operations/tests/product/test_owner_control.py), часть обязательного gate `Quality skills`.

## 8. Готово когда

- ✅ Все шаги плана выполнены
- ✅ Локальные проверки успешны ([`operations/tests/product/test_owner_control.py`](../../operations/tests/product/test_owner_control.py): 27/27 тестов прошли, часть CI gate)
- ✅ Pre-commit валидация успешна
- ✅ CI успешен
- ✅ Код review (смысловая проверка) пройден

## 9. Что будет дальше

[`TASK_003`](task_003_arc_003.md) реализует Оркестрацию и `RuntimePort` ([`ARC_CMP_003`](../../specifications/architecture_baseline.md#arc_cmp_003)), которая обязана вызывать `OwnerControl.verify_identity` и `OwnerControl.check_emergency_stop` на каждом шаге обычного цикла задачи ([`ARC_FLOW_001`](../../specifications/architecture_baseline.md#arc_flow_001)), прежде чем передать управление модели или инструменту.

## 10. Что это даёт владельцу

Чужое сообщение не превращается в выполняемую задачу от имени владельца, а команда на остановку срабатывает даже если модель или среда агента недоступны или ведут себя непредсказуемо. Чувствительное действие (например, необратимое или направленное вовне) не выполняется автоматически без явного решения, привязанного к его точным параметрам, и не может быть случайно выполнено дважды.
