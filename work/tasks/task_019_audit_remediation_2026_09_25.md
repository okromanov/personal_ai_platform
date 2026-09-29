---
id: TASK_019
type: task
title: Исправление аудиторских замечаний 2026-09-25
component: AUDIT
delivery_role: component
work_state: planned
version: 1.1
updated: 2026-09-29
next_actor: agent
owner_action: none
depends_on:
  - TASK_018
allowed_paths:
  - operations/examples/sample_task_lifecycle.md
  - operations/hooks/pre_commit_hook.sh
  - operations/lifecycle/adr_lifecycle.md
  - operations/local_development_windows.md
  - operations/procedures/file_update_dependencies.md
  - operations/scripts/documents/check.py
  - operations/scripts/milestones/start.py
  - operations/scripts/quality/run_suite.py
  - operations/scripts/tasks/check_change_scope.py
  - operations/tests/product/test_channels.py
  - operations/tests/product/test_observability.py
  - operations/tests/product/test_operations_state.py
  - operations/tests/product/test_owner_control.py
  - operations/tests/product/test_persistent_task_state.py
  - operations/tests/product/test_tool_gateway.py
  - operations/tests/tooling/test_change_scope.py
  - operations/tests/tooling/test_check_owner_interface.py
  - src/observability/
  - src/operations/health.py
  - src/owner_control/control.py
  - src/task_state/**
  - adr/adr_009_secret_management_strategy.md
  - specifications/business_requirements.md
  - specifications/system_specification.md
  - specifications/threat_model.md
  - work/tasks/task_015_real_model_provider.md
  - work/tasks/task_018_runtime_task_events.md
  - work/tests/test_007.md
  - work/tests/test_021.md
traces_to:
  - m02
decides:
implements:
---

# TASK_019 — Исправление аудиторских замечаний 2026-09-25

## 1. Зачем это делаем

Закрыть все открытые аудиторские замечания baseline 2026-09-25 (AUD-049..AUD-067), которые можно устранить без новых продуктовых решений владельца, и зафиксировать решения владельца там, где они необходимы.

## 2. Результат

- Все maintenance-находки (AUD-049, AUD-050, AUD-053, AUD-055, AUD-056, AUD-057, AUD-059, AUD-064) устранены.
- Product-находки (AUD-051, AUD-061, AUD-062, AUD-063, AUD-065, AUD-066) устранены или переведены в `accepted_risk` с явным решением владельца.
- Находки, требующие решения владельца (AUD-052, AUD-054, AUD-060, AUD-067), зафиксированы в [`audit_register.md`](../audit/audit_register.md) с соответствующим состоянием.
- Локальный full gate и серверный CI проходят на точном SHA.

## 3. Где мы сейчас

Baseline 2026-09-25 содержит 18 открытых finding'ов. Maintenance-находки можно исправить напрямую; product-находки затрагивают код и authority-документы и требуют временной TASK с широкими `allowed_paths`.

## 4. Что делать сейчас

### Агенту

1. Исправить maintenance-находки.
2. Создать и выполнить product-исправления в рамках этой TASK.
3. Обновить [`work/audit/audit_register.md`](../audit/audit_register.md) и [`project_status.md`](../../project_status.md).
4. Запустить полный локальный gate, push, открыть PR и дождаться CI.

## 5. План выполнения

- [x] Добавить negative-path тесты для `check_owner_interface` и `validate_document_metadata` (AUD-049, AUD-050)
- [x] Привести [`file_update_dependencies.md`](../../operations/procedures/file_update_dependencies.md) к acceptance-модели (AUD-053)
- [x] Привести `work_state` [`TASK_018`](task_018_runtime_task_events.md) к факту (AUD-055)
- [x] Обновить число кандидатов [`ADR_007`](../../adr/adr_007_cloud_provider_selection.md) в [`ADR_009`](../../adr/adr_009_secret_management_strategy.md) (AUD-056)
- [x] Добавить [`ADR_005`](../../adr/adr_005_first_model_provider_selection.md) в `allowed_paths` [`TASK_015`](task_015_real_model_provider.md) (AUD-057)
- [x] Исправить мёртвые ссылки в [`sample_task_lifecycle.md`](../../operations/examples/sample_task_lifecycle.md) (AUD-059)
- [x] Обновить устаревшие статусные упоминания и счётчики тестов (AUD-064)
- [x] Платформенная проверка живости процесса в `control.py` (AUD-051)
- [x] Дедуплицировать [`SEC_CTL_018`](../../specifications/system_specification.md#sec_ctl_018) (AUD-061)
- [x] Удалить мёртвый API `has_executed`/`mark_executed` (AUD-062)
- [x] `health.py` не должен раскрывать `str(exc)` (AUD-063)
- [x] Закрыть дыры трассируемости (AUD-065)
- [x] Разорвать циклический импорт (AUD-066)
- [x] Зафиксировать состояние finding'ов в [`audit_register.md`](../audit/audit_register.md) (AUD-052, AUD-054, AUD-067 resolved; AUD-060 остаётся open до решения владельца/реализации [`TASK_016`](task_016_real_telegram.md))

## 6. Состав

Изменения затрагивают maintenance/operations, product-код, спецификации, карточки TASK/TEST, реестр аудита и производный [`project_status.md`](../../project_status.md).

## 7. Проверки и доказательства

Полный локальный gate (`operations/scripts/quality/run_suite.py full`) и серверный Project check на merge SHA.

## 8. Готово когда

- ✅ Все технические исправления AUD-049..AUD-067 выполнены или задокументированы в [`audit_register.md`](../audit/audit_register.md).
- ✅ AUD-049..AUD-059, AUD-061..AUD-067 — `resolved`; AUD-060 — `open` с review date 2026-10-25, требует решения владельца или реализации [`TASK_016`](task_016_real_telegram.md).
- ✅ Full gate зелёный локально и в CI.
- ✅ PR слит в `main`.

## 9. Что будет дальше

Проект возвращается к обычной очереди [`TASK_013`](task_013_inf_008.md) и следующих этапов.

## 10. Что это даёт владельцу

Аудиторские замечания не накапливаются, а их состояние и обоснование прозрачны в реестре.
