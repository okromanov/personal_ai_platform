---
id: TASK_013
type: task
title: Реализация INF_CMP_008
component: INF_CMP_008
work_state: in-progress
version: 2.6
updated: 2026-09-01
next_actor: agent
owner_action: none
owner_followups:
  - "[open] Выполнить четыре инструкции развёртывания (Hetzner, DigitalOcean, Selectel, OVHcloud) и прислать заполненные evidence-блоки (раздел 11 каждой) — агент не может сам зарегистрировать аккаунты, подключиться по SSH или создать Telegram-бота. Инструкция для OVHcloud — черновая (dummy), не проверена практически ни разу, в отличие от остальных трёх."
depends_on:
  - TASK_012
allowed_paths:
  - work/tasks/task_013_inf_008.md
  - adr/adr_005_first_model_provider_selection.md
  - adr/adr_006_agent_environment_framework.md
  - adr/adr_007_cloud_provider_selection.md
  - adr/adr_009_secret_management_strategy.md
traces_to:
  - m02
decides:
  - ADR_007
  - ADR_009
implements:
  - INF_CMP_008
---

# TASK_013 — Реализация INF_CMP_008

## 1. Зачем это делаем

Обеспечить идентифицируемое развёртывание, контрольную проверку и управляемый переход между версиями. Без этого компонента нельзя достоверно ответить, какая версия кода развёрнута, откатить неудачное развёртывание или гарантировать, что переход между версиями не потерял данные из постоянного хранилища ([`TASK_011`](task_011_inf_005.md)).

## 2. Результат

Выбранная площадка размещения, зафиксированная в [`ADR_007`](../../adr/adr_007_cloud_provider_selection.md), согласованная с ней стратегия runtime-секретов из [`ADR_009`](../../adr/adr_009_secret_management_strategy.md) и механизм развёртывания с явной привязкой к версии (Git SHA или тег), контрольной проверкой после развёртывания и управляемым откатом. Замыкает цепочку инфраструктурных компонентов: среда ([`TASK_008`](task_008_inf_001.md)) → сеть ([`TASK_009`](task_009_inf_002.md)) → секреты ([`TASK_010`](task_010_inf_003.md)) → хранилище ([`TASK_011`](task_011_inf_005.md)) → наблюдаемость ([`TASK_012`](task_012_inf_007.md)) → развёртывание (эта TASK).

## 3. Где мы сейчас

[`TASK_012`](task_012_inf_007.md) завершена, поэтому эта TASK стала текущей. Сейчас сравниваются Hetzner и DigitalOcean (сценарий A) для [`ADR_007`](../../adr/adr_007_cloud_provider_selection.md), Selectel оценивается отдельно как резервный сценарий B, и совместимая стратегия управления runtime-секретами для [`ADR_009`](../../adr/adr_009_secret_management_strategy.md). Оба ADR остаются `proposed`: окончательное решение по сценарию A будет принято после единой scorecard, проверки доступной владельцу оплаты и практического deployment победителя; сценарий B остаётся в бэклоге до завершения сценария A и создания резервной копии. После решения будут зафиксированы требования к воспроизводимому развёртыванию, health-check и откату по [`INF_REQ_010`](../../specifications/infrastructure_baseline.md#inf_req_010), [`INF_REQ_011`](../../specifications/infrastructure_baseline.md#inf_req_011) и [`INF_REQ_014`](../../specifications/infrastructure_baseline.md#inf_req_014).

## 4. Что делать сейчас

### Агенту

1. На одной scorecard сравнить Hetzner и DigitalOcean (сценарий A), отдельно оценить Selectel (сценарий B), вместе с совместимыми способами хранения runtime-секретов; представить владельцу рекомендации для [`ADR_007`](../../adr/adr_007_cloud_provider_selection.md) и [`ADR_009`](../../adr/adr_009_secret_management_strategy.md)
2. После решения владельца зафиксировать выбранные варианты и обоснование в обоих ADR
3. Дополнить `allowed_paths` фактическими путями реализации
4. Реализовать идентифицируемое развёртывание, контрольную проверку и откат
5. Написать TEST с реальным evidence и проверить развёрнутый контур

## 5. План выполнения

- [ ] Сравнить Hetzner/DigitalOcean (сценарий A) и оценить Selectel (сценарий B) вместе с runtime-secret вариантами; подготовить решения [`ADR_007`](../../adr/adr_007_cloud_provider_selection.md) и [`ADR_009`](../../adr/adr_009_secret_management_strategy.md)
- [ ] Получить решение владельца и обновить оба ADR
- [ ] Дополнить allowed_paths реальными путями
- [ ] Реализовать развёртывание, контрольную проверку и откат
- [ ] Написать TEST, связанный с TASK и требованиями компонента
- [ ] Проверить развёрнутый контур и покрытие путей

## 6. Состав

**В начале работы агент** определит фактические файлы реализации (предположительно в каталоге `infrastructure/deploy/` или конфигурации существующего CI), добавит их в `allowed_paths` и создаст связанную карточку TEST.

По прямому запросу владельца, не относящемуся к реализации [`INF_CMP_008`](../../specifications/infrastructure_baseline.md#inf_cmp_008): в [`milestones.md`](../../milestones.md) добавлена строка «ADR этого этапа» для каждого `mXX` и убран необязательный текст из раздела «Готовность этапа [`m01`](../../milestones.md#m01)»; в [`work/audit/audit_register.md`](../audit/audit_register.md) убрана вспомогательная запись, ссылавшаяся на этот текст. Оба файла теперь покрыты `MAINTENANCE_PATH_PATTERNS` в `check_change_scope.py` (governance/audit-трейл, не продуктовая поставка) — в `allowed_paths` этой TASK не добавлялись.

Полный прогон проверки также обнаружил в [`work/audit/audit_register.md`](../audit/audit_register.md) две некликабельные ссылки на [`ADR_009`](../../adr/adr_009_secret_management_strategy.md) (одна — испорченная вложенными скобками от автоматического линкера, добавлена отдельным изменением) — исправлены; не относится к реализации [`INF_CMP_008`](../../specifications/infrastructure_baseline.md#inf_cmp_008).

По прямому запросу владельца проведена сверка синхронизации всех ADR (принятых и `proposed`) с реализованным кодом; найденные расхождения зафиксированы карточками [`AUD-029`](../audit/audit_adhoc_cards.md#aud-029) и [`AUD-030`](../audit/audit_adhoc_cards.md#aud-030) в [`work/audit/audit_register.md`](../audit/audit_register.md) — не реализовано решение [`ADR_004`](../../adr/adr_004_task_events_and_logging.md) и разошлось имя контракта модели против `ModelGateway` в коде. При слиянии с `main` выяснилось, что обе находки уже независимо отслежены/устранены параллельной сессией ([`AUD-024`](../audit/audit_baseline_2026_08_30.md#aud-024), [`TASK_018`](task_018_runtime_task_events.md), переименование [`ADR_003`](../../adr/adr_003_model_provider_interface.md) на `ModelGateway`) — [`AUD-029`](../audit/audit_adhoc_cards.md#aud-029)/[`AUD-030`](../audit/audit_adhoc_cards.md#aud-030) переномерованы из-за коллизии ID и закрыты как дубликаты; не относится к реализации [`INF_CMP_008`](../../specifications/infrastructure_baseline.md#inf_cmp_008).

По прямому запросу владельца скорректирован процесс формирования ADR ([`operations/lifecycle/adr_lifecycle.md`](../../operations/lifecycle/adr_lifecycle.md) Фаза 0, [`AGENTS.md`](../../AGENTS.md) §5): список кандидатов ADR согласуется с владельцем через диалог до создания текста, а не выбирается агентом в одиночку. По итогам того же диалога (уточняющие вопросы владельцу) переписаны [`ADR_005`](../../adr/adr_005_first_model_provider_selection.md) (кандидаты расширены до Claude/GPT/Gemini/отечественных моделей вместо одного Claude) и [`ADR_006`](../../adr/adr_006_agent_environment_framework.md) (кандидаты — LangGraph/CrewAI/собственная реализация вместо одного LangGraph); [`ADR_009`](../../adr/adr_009_secret_management_strategy.md) переформулирован без слова «кандидат» для `.env` — это уже выбранный подход, а не вариант для сравнения, с SOPS+age как согласованным следующим шагом и Vault как отдельно отложенной опцией. [`ADR_008`](../../adr/adr_008_data_storage_schema.md) по решению владельца оставлен без изменений — пересмотр отложен до декомпозиции [`m04`](../../milestones.md#m04). Оба файла ([`ADR_005`](../../adr/adr_005_first_model_provider_selection.md), [`ADR_006`](../../adr/adr_006_agent_environment_framework.md)) добавлены в `allowed_paths`; не относится к реализации [`INF_CMP_008`](../../specifications/infrastructure_baseline.md#inf_cmp_008).

По прямому запросу владельца добавлен [`project_rules.md`](../../project_rules.md) Принцип 19: выбор технологии для ADR-кандидатов и решения при написании кода опираются на текущие лучшие практики отрасли для контекста задачи, а не на интуицию или аналогию с уже существующим в репозитории кодом. Со ссылкой на него дополнены [`operations/lifecycle/adr_lifecycle.md`](../../operations/lifecycle/adr_lifecycle.md) Фаза 0 и [`AGENTS.md`](../../AGENTS.md) §3. [`project_rules.md`](../../project_rules.md) покрыт `MAINTENANCE_PATH_PATTERNS` — в `allowed_paths` не добавлялся.

При слиянии этой ветки с `main` обнаружились два независимых, недоступных друг другу диалога с владельцем по [`ADR_006`](../../adr/adr_006_agent_environment_framework.md) и [`ADR_007`](../../adr/adr_007_cloud_provider_selection.md) — зафиксировано и разрешено владельцем как [`AUD-028`](../audit/audit_adhoc_cards.md#aud-028): [`ADR_006`](../../adr/adr_006_agent_environment_framework.md) объединён в четыре кандидата (LangGraph, CrewAI, Hermes Agent, собственная реализация), [`ADR_007`](../../adr/adr_007_cloud_provider_selection.md) вернулся к двухсценарной структуре. Одновременно владелец вернул деференциальное правило для `proposed` ADR `planned` milestone (см. [`AUD-025`](../audit/audit_baseline_2026_08_30.md#aud-025) — обновление 2026-08-30), отменив немедленное требование TASK для [`ADR_008`](../../adr/adr_008_data_storage_schema.md)/[`m04`](../../milestones.md#m04), введённое параллельной сессией; не относится к реализации [`INF_CMP_008`](../../specifications/infrastructure_baseline.md#inf_cmp_008).

**Ожидаемые файлы:**
- `infrastructure/deploy/` или расширение существующего CI workflow — механизм версионирования и развёртывания
- `work/tests/test_00X.md` — описание проверок

## 7. Проверки и доказательства

**Автоматические:**
1. Все файлы в `allowed_paths` (CI проверяет)
2. Развёртывание тестового окружения проходит с контрольной проверкой
3. Существующий CI (Windows + Ubuntu) продолжает проходить

**Ручные (code review):**
1. Каждое развёртывание однозначно связано с версией кода (SHA/тег)
2. Откат к предыдущей версии не требует ручного вмешательства в данные

## 8. Готово когда

- ✅ [`ADR_007`](../../adr/adr_007_cloud_provider_selection.md) и [`ADR_009`](../../adr/adr_009_secret_management_strategy.md) приняты или отклонены владельцем с зафиксированным обоснованием
- ✅ Все шаги плана выполнены
- ✅ Локальные проверки успешны
- ✅ CI успешен
- ✅ Код review завершен

## 9. Что будет дальше

[`TASK_014`](task_014_real_runtime.md) выбирает и подключает реальную среду агента к уже развёрнутому контуру. Она не может быть заменена существующим StubRuntime.

## 10. Что это даёт владельцу

Функционал появится после завершения этой TASK.

## Незакрытые действия владельца

Выполнить четыре инструкции развёртывания (Hetzner, DigitalOcean, Selectel, OVHcloud) и прислать заполненные evidence-блоки (раздел 11 каждой) — агент не может сам зарегистрировать аккаунты, подключиться по SSH или создать Telegram-бота. Инструкция для OVHcloud — черновая (dummy), не проверена практически ни разу, в отличие от остальных трёх.

Инструкции отправлены владельцу как PDF (не в репозитории), также сохранены в Google Drive (папка `personal_ai_platform`). Инструкция для OVHcloud — черновая (`v0.1 dummy`), не проверена практически ни разу, в отличие от Hetzner/DigitalOcean/Selectel: конкретные названия экранов OVHcloud Control Panel могут не совпасть с актуальным интерфейсом. Пока не пришли evidence-блоки по Hetzner и минимум одной альтернативе сценария A, [`ADR_007`](../../adr/adr_007_cloud_provider_selection.md) не может перейти из `proposed`: §6 ADR требует Hetzner и минимум одну альтернативу сценария A (DigitalOcean или OVHcloud), а также отдельно оценённый сценарий B (Selectel). Можно проходить инструкции по одной, в любом порядке, и присылать evidence по мере готовности — это не блокирует ничего кроме самого решения по [`ADR_007`](../../adr/adr_007_cloud_provider_selection.md).
