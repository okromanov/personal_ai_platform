---
id: TEST_020
type: test
title: "SEC_CTL_001 — Контракт подлинности Telegram update"
spec_state: current
execution: automated
automated_evidence: quality_suite
version: 1.0
updated: 2026-09-02
accepts:
  - m02
traces_to:
  - TASK_016
verifies:
  - SEC_CTL_001
depends_on:
  - TEST_019
---

# TEST_020 — Контракт подлинности Telegram update

Автоматическая проверка. Действия владельца не требуются.

## 1. Назначение

Не позволить будущей реализации [`TASK_016`](../tasks/task_016_real_telegram.md) доверять подделываемому идентификатору владельца без проверки происхождения Telegram update, требуемой [`SEC_CTL_001`](../../specifications/system_specification.md#sec_ctl_001).

## 2. Что проверяется

Пока реальный Telegram Bot API запланирован, executable contract test проверяет саму карточку поставки: webhook обязан проверять отдельный secret token на каждом update до `OwnerControl`; polling обязан оставаться исходящим и не открывать входной endpoint; отрицательный сценарий с поддельным update и правильным идентификатором владельца обязан завершиться до вызова модели. При реализации [`TASK_016`](../tasks/task_016_real_telegram.md) этот TEST расширяется проверкой реального адаптера, не меняя критерий безопасности.

## 3. Автоматический запуск

Канонический quality-suite запускает `TelegramTaskAuthenticityContractTest` из [`test_security_extended.py`](../../operations/tests/test_security_extended.py). Действий владельца нет.

## 4. Критерий успеха

Карточка одновременно содержит обязательный webhook secret token, безопасную polling-модель и отрицательный spoof-сценарий; удаление любого из этих требований проваливает тест.

## 5. Состав доказательства

`automated_evidence: quality_suite`: результат executable contract test входит в SHA-bound запись канонического серверного прогона. Это доказательство полноты плана безопасности, а не заявление о уже существующем реальном Telegram endpoint.
