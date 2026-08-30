---
id: TASK_015
type: task
title: Реальный поставщик модели для ARC_CMP_004
component: ARC_CMP_004
delivery_role: terminal_outcome
work_state: planned
version: 1.4
updated: 2026-08-30
next_actor: agent
owner_action: none
depends_on:
  - TASK_014
allowed_paths:
  - work/tasks/task_015_real_model_provider.md
traces_to:
  - m02
decides:
  - ADR_005
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

1. Сравнить актуальных поставщиков на одной scorecard: качество, задержка, стоимость, доступность из выбранной сети, правила данных и обработка отказов; получить решение по [`ADR_005`](../../adr/adr_005_first_model_provider_selection.md)
2. Дополнить allowed_paths и реализовать адаптер выбранного provider
3. Зарегистрировать адаптер как явный non-stub профиль eval harness
4. Создать отдельные golden expectations для реального provider; stub-ожидания не переиспользовать как доказательство качества
5. Проверить timeout, budget и отказ provider
6. Создать TEST и evidence реального вызова на полном commit SHA без раскрытия секрета

## 5. План выполнения

- [ ] Сравнить варианты и принять [`ADR_005`](../../adr/adr_005_first_model_provider_selection.md)
- [ ] Дополнить allowed_paths реальными путями
- [ ] Подключить одного реального provider
- [ ] Зарегистрировать явный non-stub eval-профиль и отдельные golden expectations
- [ ] Проверить timeout, budget и ошибки
- [ ] Написать TEST, связанный с TASK и требованиями компонента

## 6. Состав

До принятия [`ADR_005`](../../adr/adr_005_first_model_provider_selection.md) пути реализации не предрешаются. В TASK обязательно войдут адаптер, конфигурация без секретов и TEST.

## 7. Проверки и доказательства

Проверяется реальный ответ, нормализация ошибки и отсутствие секретов в выводе. Eval запускается с явно выбранным non-stub профилем и полным 40-символьным commit SHA. Успешный stub-тест не является доказательством качества реального provider.

## 8. Готово когда

- ✅ [`ADR_005`](../../adr/adr_005_first_model_provider_selection.md) принят владельцем
- ✅ Реальный provider отвечает через ModelGateway
- ✅ Реальный provider зарегистрирован как явный non-stub eval-профиль с отдельными golden expectations
- ✅ Timeout, budget и отказ проверены
- ✅ Eval evidence привязано к полному commit SHA
- ✅ Секреты не попадают в репозиторий и логи

## 9. Что будет дальше

[`TASK_016`](task_016_real_telegram.md) подключит реальный Telegram Bot API к защищённому контуру.

## 10. Что это даёт владельцу

Помощник может получать настоящий ответ выбранной модели, а не ответ-заглушку.
