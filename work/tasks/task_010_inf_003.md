---
id: TASK_010
type: task
title: Реализация INF_CMP_003
component: INF_CMP_003
work_state: completed
version: 2.1
updated: 2026-09-02
next_actor: none
owner_action: none
depends_on:
  - TASK_009
allowed_paths:
  - work/tasks/task_010_inf_003.md
  - work/tests/test_016.md
  - src/secrets/__init__.py
  - src/secrets/base.py
  - src/secrets/env_provider.py
  - src/channels/telegram.py
  - operations/tests/product/test_secrets.py
traces_to:
  - m02
implements:
  - INF_CMP_003
tests:
  - TEST_016
---

# TASK_010 — Реализация INF_CMP_003

## 1. Зачем это делаем

Реализовать механизм защищённого хранения и выдачи секретов (API-ключи моделей, токены каналов, учётные данные внешних сервисов). Без выделенного хранилища секретов они неизбежно попадают в код, конфигурационные файлы или логи.

## 2. Результат

Механизм хранения и выдачи секретов на переменных окружения для [`m02`](../../milestones.md#m02). Потребитель запрашивает логическое имя через `SecretProvider`; TelegramChannel получает токен как `TELEGRAM_BOT_TOKEN`. Контракт не привязан к env-провайдеру.

## 3. Где мы сейчас

Спецификация [`INF_CMP_003`](../../specifications/infrastructure_baseline.md#inf_cmp_003) определяет [`INF_REQ_006`](../../specifications/infrastructure_baseline.md#inf_req_006). Выбран минимальный для [`m02`](../../milestones.md#m02) вариант: переменные окружения с заменяемым контрактом. Реальный поставщик модели должен получать ключ через этот же контракт. Зависимость от [`TASK_009`](task_009_inf_002.md) выполнена.

## 4. Что делать сейчас

### Агенту

Работа завершена. Следующая проектная задача — [`TASK_011`](task_011_inf_005.md).

## 5. План выполнения

- [x] Изучить требования к [`INF_CMP_003`](../../specifications/infrastructure_baseline.md#inf_cmp_003)
- [x] Дополнить allowed_paths реальными путями
- [x] Спроектировать реализацию
- [x] Реализовать компонент
- [x] Написать [`TEST_016`](../tests/test_016.md), связанный с TASK и требованиями компонента
- [x] Проверить покрытие путей в allowed_paths

## 6. Состав

В `src/secrets/` находится абстрактный контракт и реализация на переменных окружения. Доступ к секрету происходит по логическому имени; значения не пишутся в сообщения исключений или журналы. TelegramChannel может получить свой токен через этот контракт. Полный перечень путей поставки указан в `allowed_paths`.

## 7. Проверки и доказательства

`operations/tests/product/test_secrets.py` проверяет выдачу, ошибки и интеграцию Telegram; шесть целевых тестов пройдены. [`TEST_016`](../tests/test_016.md) связан с [`INF_REQ_006`](../../specifications/infrastructure_baseline.md#inf_req_006).

## 8. Готово когда

- [x] Шесть тестов `operations/tests/product/test_secrets.py` прошли;
- [x] Все пути поставки входят в `allowed_paths`;
- [x] [`TEST_016`](../tests/test_016.md) имеет актуальную спецификацию и автоматическое evidence;
- [x] Канонический CI успешен.

## 9. Что будет дальше

[`TASK_011`](task_011_inf_005.md) реализует Постоянное хранилище ([`INF_CMP_005`](../../specifications/infrastructure_baseline.md#inf_cmp_005)).

## 10. Что это даёт владельцу

Платформа получает заменяемый `SecretProvider`: секрет запрашивается по логическому имени из окружения, пустое или отсутствующее значение отвергается без вывода значения в ошибках, а TelegramChannel получает `TELEGRAM_BOT_TOKEN` через этот контракт.
