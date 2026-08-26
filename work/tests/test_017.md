---
id: TEST_017
type: test
title: "INF_CMP_005 — SQLite-постоянное состояние задачи"
spec_state: current
execution: automated
automated_evidence: quality_suite
version: 1.0
updated: 2026-08-26
accepts:
  - m02
traces_to:
  - TASK_011
verifies:
  - INF_REQ_008
  - INF_REQ_016
depends_on:
  - TEST_016
---

# TEST_017 — SQLite-постоянное состояние задачи

Автоматическая проверка. Действия владельца не требуются.

## 1. Назначение

Доказать, что [`INF_CMP_005`](../../specifications/infrastructure_baseline.md#inf_cmp_005) сохраняет каноническое состояние задачи в переносимой SQLite-базе и восстанавливает его новым экземпляром после перезапуска.

## 2. Что проверяется

`SQLiteTaskLifecycleStore` сохраняет нормализованное сообщение задачи, checkpoint, счётчик повторов, отмену и запись о выполненном действии. Все операции выполняются через неизменный контракт `TaskLifecycleStore`; физический путь к БД передаётся конфигурацией и не привязан к облачному поставщику.

Так выполняются [`INF_REQ_008`](../../specifications/infrastructure_baseline.md#inf_req_008) и [`INF_REQ_016`](../../specifications/infrastructure_baseline.md#inf_req_016).

## 3. Автоматический запуск

Канонический quality-suite запускает [`test_persistent_task_state.py`](../../operations/tests/product/test_persistent_task_state.py).

## 4. Критерий успеха

Тест создаёт SQLite-хранилище, записывает все виды состояния, затем открывает тот же файл новым экземпляром. Сообщение, checkpoint, retry/cancel и защита от повтора должны быть восстановлены.
