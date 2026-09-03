---
id: TEST_007
type: test
title: "ARC_CMP_001 — Каналы: нормализация входа для Telegram"
spec_state: current
execution: automated
automated_evidence: quality_suite
version: 2.1
updated: 2026-09-03
accepts:
  - m02
traces_to:
  - TASK_001
  - SYS_001
  - SYS_005
  - SYS_006
  - SYS_007
depends_on: []
---

# TEST_ARC_CMP_001_IMPLEMENTATION — Каналы: нормализация входа для Telegram

## 1. Назначение

Доказать, что компонент [`ARC_CMP_001`](../../specifications/architecture_baseline.md#arc_cmp_001) (Каналы) правильно нормализует пользовательский ввод для Telegram и других поддерживаемых интерфейсов в формат `TaskMessage` согласно требованиям [`SYS_001`](../../specifications/system_specification.md#sys_001).

## 2. Что проверяется

Реализация стабильного контракта канала `Channel` и конкретной реализации для Telegram (`TelegramChannel`):

- Нормализация входных сообщений в `TaskMessage` с уникальным идентификатором задачи
- Отслеживание наблюдаемого состояния: pending → running → completed/failed/cancelled
- Отправка ответов обратно через тот же канал
- Отсутствие владения бизнес-логикой, памятью или полномочиями

Требования:

- **[`SYS_001`](../../specifications/system_specification.md#sys_001)**: Единый жизненный цикл задачи в основном канале (Telegram)
- **[`SYS_005`](../../specifications/system_specification.md#sys_005)**: Веб-интерфейс как общий клиент (базовая подготовка)
- **[`SYS_006`](../../specifications/system_specification.md#sys_006)**: Командный интерфейс (подготовка)
- **[`SYS_007`](../../specifications/system_specification.md#sys_007)**: Голосовой канал (подготовка архитектуры)

## 3. Автоматический запуск

Часть канонического прогона юнит-тестов, выполняется в `Quality skills` на каждом push/PR:

```bash
python3.12 operations/scripts/quality/run_unittests.py
```

Отдельный прогон только этого компонента:

```bash
python3.12 -m unittest operations.tests.product.test_channels -v
```

## 4. Критерий успеха

Все 17 тестов проходят, включая сценарии:

- ✓ telegram_channel_init — инициализация с токеном
- ✓ receive_without_token — отказ без токена
- ✓ inject_and_receive_message — приём и нормализация сообщения
- ✓ send_response — отправка ответа через канал
- ✓ task_message_state_transitions — смена состояний задачи
- ✓ send_status — отправка статуса задачи
- ✓ multiple_messages — обработка нескольких сообщений
- ✓ channel_reset — очистка состояния канала
- ✓ receive_timeout — таймаут ожидания сообщения возвращает `ChannelError`

## 5. Состав доказательства

`automated_evidence: quality_suite`. Каждый запуск верификационного скрипта создаёт доказательство выполнения всех 17 модульных тестов на текущем Git SHA. Результат успеха фиксируется в evidence записи с временем выполнения и версией платформы.
