---
id: TEST_016
type: test
title: "INF_CMP_003 — секреты вне репозитория и выдача по логическому имени"
spec_state: current
execution: automated
automated_evidence: quality_suite
version: 1.0
updated: 2026-08-26
accepts:
  - m02
traces_to:
  - TASK_010
verifies:
  - INF_REQ_006
depends_on:
  - TEST_015
---

# TEST_016 — Секреты вне репозитория и выдача по логическому имени

Автоматическая проверка. Действия владельца не требуются.

## 1. Назначение

Доказать, что `INF_CMP_003` выдаёт секрет только по логическому имени, не допускает пустые значения и не раскрывает значение при ошибке.

## 2. Что проверяется

`src/secrets/env_provider.py` определяет заменяемый env-провайдер: он принимает допустимое логическое имя, возвращает только непустое значение среды и при отсутствии секрета не раскрывает его значение. [`TelegramChannel`](../../src/channels/telegram.py) получает токен через `SecretProvider`.

Так выполняется [`INF_REQ_006`](../../specifications/infrastructure_baseline.md#inf_req_006).

## 3. Автоматический запуск

Канонический quality-suite запускает `operations/tests/product/test_secrets.py`. Действия владельца не требуются.

## 4. Критерий успеха

Шесть тестов в `operations/tests/product/test_secrets.py` проходят: выдача, отсутствие и пустое значение секрета, проверка имени и интеграция с каналом Telegram.

## 5. Состав доказательства

- [`TASK_010`](../tasks/task_010_inf_003.md);
- [`INF_CMP_003`](../../specifications/infrastructure_baseline.md#inf_cmp_003);
- [`INF_REQ_006`](../../specifications/infrastructure_baseline.md#inf_req_006);
- `src/secrets/base.py`;
- `src/secrets/env_provider.py`;
- `operations/tests/product/test_secrets.py`.
