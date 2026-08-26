---
id: TASK_015
type: task
title: Реальный поставщик модели для ARC_CMP_004
component: ARC_CMP_004
delivery_role: component
work_state: planned
version: 1.0
updated: 2026-08-26
next_actor: agent
owner_action: none
depends_on:
  - TASK_014
allowed_paths:
  - work/tasks/task_015_real_model_provider.md
traces_to:
  - m02
implements:
  - ARC_CMP_004
---

# TASK_015 — Реальный поставщик модели для ARC_CMP_004

## 1. Зачем это делаем

`StubModelGateway` проверяет контракт, но не даёт владельцу ответ модели. Для результата [`m02`](../../milestones.md#m02) нужен один реальный поставщик с ограничениями времени, бюджета и понятным отказом.

## 2. Результат

[`ADR_005`](../../adr/adr_005_first_model_provider_selection.md) принят; выбранный provider вызывается через `ModelGateway`, использует `SecretProvider`, отдаёт нормализованный ответ и не обходит OwnerControl.

## 3. Где мы сейчас

[`TASK_004`](task_004_arc_004.md) поставила контракт и переходный stub. Поставщик не выбран и сетевой вызов модели отсутствует.

## 4. Что делать сейчас

### Агенту

1. Сравнить актуальных поставщиков и получить решение по [`ADR_005`](../../adr/adr_005_first_model_provider_selection.md)
2. Дополнить allowed_paths и реализовать адаптер выбранного provider
3. Проверить timeout, budget и отказ provider
4. Создать TEST с evidence реального вызова без раскрытия секрета

## 5. План выполнения

- [ ] Сравнить варианты и принять [`ADR_005`](../../adr/adr_005_first_model_provider_selection.md)
- [ ] Дополнить allowed_paths реальными путями
- [ ] Подключить одного реального provider
- [ ] Проверить timeout, budget и ошибки
- [ ] Создать TEST и evidence точного SHA

## 6. Состав

До принятия [`ADR_005`](../../adr/adr_005_first_model_provider_selection.md) пути реализации не предрешаются. В TASK обязательно войдут адаптер, конфигурация без секретов и TEST.

## 7. Проверки и доказательства

Проверяется реальный ответ, нормализация ошибки и отсутствие секретов в выводе. Успешный stub-тест не является доказательством.

## 8. Готово когда

- ✅ [`ADR_005`](../../adr/adr_005_first_model_provider_selection.md) принят владельцем
- ✅ Реальный provider отвечает через ModelGateway
- ✅ Timeout, budget и отказ проверены
- ✅ Секреты не попадают в репозиторий и логи

## 9. Что будет дальше

[`TASK_016`](task_016_real_telegram.md) подключит реальный Telegram Bot API к защищённому контуру.

## 10. Что это даёт владельцу

Помощник может получать настоящий ответ выбранной модели, а не ответ-заглушку.
