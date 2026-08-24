---
id: TEST_007
type: test
title: "ARC_CMP_001 — Каналы: нормализация входа для Telegram"
spec_state: current
execution: automated
automated_evidence: quality_suite
version: 1.5
updated: 2026-08-23
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

Доказать, что компонент ARC_CMP_001 (Каналы) правильно нормализует пользовательский ввод для Telegram и других поддерживаемых интерфейсов в формат `TaskMessage` согласно требованиям SYS_001.

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
python3 operations/scripts/quality/run_unittests.py
```

Отдельный прогон только этого компонента:

```bash
python3 -m unittest operations.tests.product.test_channels -v
```

## 4. Критерий успеха

Все 16 тестов проходят, включая сценарии:

- ✓ telegram_channel_init — инициализация с токеном
- ✓ receive_without_token — отказ без токена
- ✓ inject_and_receive_message — приём и нормализация сообщения
- ✓ send_response — отправка ответа через канал
- ✓ task_message_state_transitions — смена состояний задачи
- ✓ send_status — отправка статуса задачи
- ✓ multiple_messages — обработка нескольких сообщений
- ✓ channel_reset — очистка состояния канала

## 5. Состав доказательства

`automated_evidence: quality_suite`. Каждый запуск верификационного скрипта создаёт доказательство выполнения всех 8 модульных тестов на текущем Git SHA. Результат успеха фиксируется в evidence записи с временем выполнения и версией платформы.

## 6. Реализованные компоненты

### Компонент: Каналы

**Стабильный контракт**: `Channel` (абстрактный класс)

- `async receive() → TaskMessage`: Получить нормализованное сообщение
- `async send(response: str, task_id: str)`: Отправить ответ
- `async send_status(status: TaskState, task_id: str)`: Отправить статус

**Данные**: `TaskMessage`

- `task_id`: Уникальный идентификатор выполнения (UUID)
- `channel_type`: Тип канала (telegram, web, cli, voice)
- `user_input`: Нормализованный текст ввода
- `state`: TaskState (pending, running, completed, failed, cancelled)
- `metadata`: Контекст (user_id, chat_id, timestamp и т.д.)
- `created_at`, `completed_at`, `error_message`: Метаданные жизненного цикла

**Реализация**: `TelegramChannel` для Telegram

- Поддерживает очередь сообщений (для тестирования и интеграции)
- Нормализует Telegram обновления в TaskMessage
- Хранит ответы для проверки
- Методы inject_message и reset для тестирования

## 7. Структура кода

```
src/
├── __init__.py
└── channels/
    ├── __init__.py — публичный API
    ├── base.py — Channel, TaskMessage, TaskState, ChannelError
    └── telegram.py — TelegramChannel реализация

operations/tests/product/
├── __init__.py
└── test_channels.py — юнит-тесты, часть канонического run_unittests.py (CI/CD)
```

## 8. Соответствие требованиям

| Требование | Статус | Примечание |
|---|---|---|
| [`SYS_001`](../../specifications/system_specification.md#sys_001): Жизненный цикл задачи | ✅ | Реализовано с TaskState и наблюдаемыми переходами |
| [`SYS_005`](../../specifications/system_specification.md#sys_005): Веб-интерфейс | 🔄 | Архитектура готова, реализация на m02.step5 |
| [`SYS_006`](../../specifications/system_specification.md#sys_006): Админский интерфейс | 🔄 | Архитектура готова, реализация на m02.step6 |
| [`SYS_007`](../../specifications/system_specification.md#sys_007): Голосовой канал | 🔄 | Архитектура готова, реализация на m03+ |

## 9. Доказательства

- **Исходный код**: `src/channels/*` — стабильный контракт и Telegram реализация
- **Тесты**: 16 юнит-тестов в `operations/tests/product/test_channels.py`, часть обязательного gate `Quality skills`
- **Отсутствие регрессий**: Запуск `check.py --all` прошел успешно

## 10. Готово когда

- ✅ 8 тестов пройдено
- ✅ Архитектура Channel определена и используется
- ✅ TelegramChannel реализован для базового сценария
- ✅ TaskMessage нормализует ввод с метаданными
- ✅ Наблюдаемое состояние отслеживается
- ✅ Структура готова для интеграции в [`ARC_CMP_003`](../../specifications/architecture_baseline.md#arc_cmp_003) (Оркестрация)

## 11. Что будет дальше

1. [`TASK_002`](../tasks/task_002_arc_002.md): Реализация [`ARC_CMP_002`](../../specifications/architecture_baseline.md#arc_cmp_002) (Контроль владельца)
2. [`TASK_003`](../tasks/task_003_arc_003.md): Реализация [`ARC_CMP_003`](../../specifications/architecture_baseline.md#arc_cmp_003) (Оркестрация и RuntimePort)
3. [`TASK_004`](../tasks/task_004_arc_004.md): Реализация [`ARC_CMP_004`](../../specifications/architecture_baseline.md#arc_cmp_004) (Шлюз моделей)
4. Затем интеграция: Telegram → Каналы → Контроль → Оркестрация → Модель

## 12. Примечания для разработчика

- Telegram интеграция упрощена для m02: используется очередь вместо реального Bot API
- Production реализация будет использовать `python-telegram-bot` и webhook/polling
- Контракт Channel стабилен и позволяет заменять реализацию без изменения остального кода
- Стабильность по [`SYS_003`](../../specifications/system_specification.md#sys_003): замена TelegramChannel на MockChannel или WebChannel не требует изменений выше уровня Channel

## 13. История версий

- **v1.0** (2026-08-22): Начальная реализация ARC_CMP_001 с поддержкой Telegram

Действия владельца не требуются: тест полностью автоматизирован и не требует ручного вмешательства.
