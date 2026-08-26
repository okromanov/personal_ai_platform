---
id: TASK_016
type: task
title: Реальный Telegram Bot API для ARC_CMP_001
component: ARC_CMP_001
delivery_role: component
work_state: planned
version: 1.0
updated: 2026-08-26
next_actor: agent
owner_action: none
depends_on:
  - TASK_015
allowed_paths:
  - work/tasks/task_016_real_telegram.md
traces_to:
  - m02
implements:
  - ARC_CMP_001
---

# TASK_016 — Реальный Telegram Bot API для ARC_CMP_001

## 1. Зачем это делаем

Очередь внутри `TelegramChannel` не является Telegram. Эта TASK заменяет эмуляцию на Bot API и сохраняет единый жизненный цикл задачи.

## 2. Результат

Реальный Telegram webhook или polling принимает сообщение владельца, передаёт его в `Channel` и возвращает ответ; токен получается только через `SecretProvider`. При обязательном VPN-профиле канал не стартует без здорового туннеля.

## 3. Где мы сейчас

[`TASK_001`](task_001_arc_001.md) поставила контракт и queue-эмуляцию без подключения к Telegram Bot API.

## 4. Что делать сейчас

### Агенту

1. Выбрать webhook или polling в границах принятой среды
2. Дополнить allowed_paths и реализовать Bot API
3. Связать Telegram-путь с NetworkPolicy и SecretProvider
4. Создать TEST реального канала и отрицательных сценариев

## 5. План выполнения

- [ ] Выбрать интеграционный режим Telegram
- [ ] Дополнить allowed_paths реальными путями
- [ ] Реализовать Bot API без эмуляции
- [ ] Проверить allowlist, Kill Switch и VPN fail-closed
- [ ] Создать TEST и evidence

## 6. Состав

Пути Bot API, конфигурации сети и TEST фиксируются после выбора режима. Токен и значения VPN не включаются в репозиторий.

## 7. Проверки и доказательства

Проверяется внешний Telegram-канал, а также отсутствие вызова модели для чужого user_id, активного Kill Switch и потерянного обязательного туннеля.

## 8. Готово когда

- ✅ Владелец может отправить сообщение реальному боту
- ✅ Bot API не использует секрет из кода или лога
- ✅ Отрицательные сценарии не вызывают модель
- ✅ TEST и evidence актуальны для точного SHA

## 9. Что будет дальше

[`TASK_017`](task_017_m02_live_e2e.md) независимо докажет полный живой сценарий [`m02`](../../milestones.md#m02).

## 10. Что это даёт владельцу

Можно написать помощнику в Telegram вместо работы с внутренней тестовой очередью.
