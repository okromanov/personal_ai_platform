---
id: audit_register
type: audit_register
document_state: current
version: 2.6
updated: 2026-09-02
depends_on: []
---

# Реестр результатов аудита

## 1. Назначение

Это единственный реестр стабильных идентификаторов `AUD-NNN`, текущих состояний исправлений и формально принятых рисков. Новый аудит сопоставляет причину с существующим ID до создания следующего номера. Состояние `accepted_risk` допустимо только после явного решения владельца; отсутствие такого решения оставляет finding открытой.

Полные карточки хранятся отдельно от изменяемого состояния: в неизменяемых точечных отчётах `work/audit/audit_baseline_YYYY_MM_DD.md`, а семь legacy-карточек, появившихся между аудитами, — в [`audit_card_archive_2026_09_02.md`](audit_card_archive_2026_09_02.md). Первая ссылка в колонке Evidence ведёт к канонической карточке. Реестр больше не хранит тела карточек и не растёт вместе с их полным текстом; канонический gate проверяет биекцию «строка ↔ архивная карточка».

## 2. Допустимые состояния

- `open` — исправление не выполнено;
- `remediated_pending_verification` — изменение реализовано, но обязательная проверка на точном SHA ещё не подтверждена;
- `resolved` — исправление и его обязательная проверка подтверждены;
- `accepted_risk` — риск принят владельцем с ответственным и датой пересмотра.

## 3. Реестр

| ID | Severity | State | First seen | Review date | Owner | Evidence | Resolution |
|---|---|---|---|---|---|---|---|
| AUD-001 | high | remediated_pending_verification | 2026-08-27 | 2026-09-02 | repository_owner | [Карточка](audit_baseline_2026_08_28.md#aud-001), [`.github/workflows/project_check.yml`](../../.github/workflows/project_check.yml) | Удалён отдельный write-capable workflow; health evidence остаётся SHA-bound Actions artifact. |
| AUD-002 | medium | remediated_pending_verification | 2026-08-27 | 2026-09-02 | repository_owner | [Карточка](audit_baseline_2026_08_28.md#aud-002), [`pre_commit_hook.sh`](../../operations/hooks/pre_commit_hook.sh), [`test_quality_integration.py`](../../operations/tests/test_quality_integration.py) | Регенерация стала blocking; post-mutation fast gate и negative test исключают fail-open. |
| AUD-003 | medium | remediated_pending_verification | 2026-08-27 | 2026-09-02 | repository_owner | [Карточка](audit_baseline_2026_08_28.md#aud-003), [`dockerfile`](../../dockerfile), [`project_check.yml`](../../.github/workflows/project_check.yml) | Base image закреплён digest; CI выполняет build/run/health и создаёт SBOM. |
| AUD-004 | medium | remediated_pending_verification | 2026-08-27 | 2026-09-02 | repository_owner | [Карточка](audit_baseline_2026_08_28.md#aud-004), [`state_io.py`](../../src/owner_control/state_io.py), [`test_owner_control.py`](../../operations/tests/product/test_owner_control.py) | После replace выполняется POSIX directory fsync; отказ durability barrier распространяется вызывающему коду. |
| AUD-005 | low | remediated_pending_verification | 2026-08-27 | 2026-09-02 | repository_owner | [Карточка](audit_baseline_2026_08_28.md#aud-005), [`run_suite.py`](../../operations/scripts/quality/run_suite.py), [`test_quality_runner.py`](../../operations/tests/tooling/test_quality_runner.py) | Каждый шаг gate ограничен 300 секундами и выдаёт локализованную ошибку timeout. |
| AUD-006 | low | remediated_pending_verification | 2026-08-27 | 2026-09-02 | repository_owner | [Карточка](audit_baseline_2026_08_28.md#aud-006), [Раздел 3](#3-реестр), [`run_suite.py`](../../operations/scripts/quality/run_suite.py) | Реестр создан; gate проверяет ID, состояния, owner и review date. |
| AUD-007 | critical | open | 2026-08-29 | 2026-09-05 | repository_owner | [Карточка](audit_baseline_2026_08_29.md#aud-007), [`project_check.yml`](../../.github/workflows/project_check.yml), [`task_012_inf_007.md`](../tasks/task_012_inf_007.md) | Владелец 2026-08-30 решил пока не восстанавливать Actions. Это не принятие риска: finding остаётся `open`, проект — `NOT READY`, серверное evidence отсутствует до первого реального зелёного прогона. |
| AUD-008 | high | remediated_pending_verification | 2026-08-29 | 2026-09-05 | repository_owner | [Карточка](audit_baseline_2026_08_29.md#aud-008), [`template_contracts.py`](../../operations/scripts/documents/template_contracts.py), [`human_status.py`](../../operations/scripts/status/human_status.py), [`m01_final_report.md`](../acceptance/m01_final_report.md) | Оба mypy-типа исправлены (`mypy` чист); [`m01_final_report.md`](../acceptance/m01_final_report.md) перегенерирован через `render_final_report()`, путь совпадает с генератором. |
| AUD-009 | high | remediated_pending_verification | 2026-08-29 | 2026-09-05 | repository_owner | [Карточка](audit_baseline_2026_08_29.md#aud-009), [`m01.json`](../acceptance/m01.json), [`adr_001_language_and_runtime.md`](../../adr/adr_001_language_and_runtime.md)–[`adr_004_task_events_and_logging.md`](../../adr/adr_004_task_events_and_logging.md) | [`ADR_001`](../../adr/adr_001_language_and_runtime.md)–[`ADR_004`](../../adr/adr_004_task_events_and_logging.md) реально переведены в `accepted` (единственные с `traces_to: m01`); [`m01.json`](../acceptance/m01.json) исправлен на эти 4 с прозрачной корректирующей записью; новая проверка [`check_acceptance_adr_transitions`](../../operations/scripts/documents/check.py) в `check.py` предотвращает рецидив. |
| AUD-010 | medium | remediated_pending_verification | 2026-08-29 | 2026-09-12 | repository_owner | [Карточка](audit_baseline_2026_08_29.md#aud-010), [`human_status.py`](../../operations/scripts/status/human_status.py), [`project_status.md`](../../project_status.md) | Добавлена строка «Состояние gate/CI» (громко показывает открытые critical-находки) и явная пометка terminal-outcome задач в таблице покрытия. |
| AUD-011 | medium | remediated_pending_verification | 2026-08-29 | 2026-09-12 | repository_owner | [Карточка](audit_baseline_2026_08_29.md#aud-011), [`document_frontmatter_standard.md`](../../operations/policy/document_frontmatter_standard.md), [`change_process.md`](../../operations/change_process.md) | Документ помечен `document_state: superseded` со ссылкой на [`change_process.md`](../../operations/change_process.md) §8; уникальное содержимое (порядок полей) перенесено туда. |
| AUD-012 | medium | remediated_pending_verification | 2026-08-29 | 2026-09-12 | repository_owner | [Карточка](audit_baseline_2026_08_29.md#aud-012), [`change_process.md`](../../operations/change_process.md), [`check.py`](../../operations/scripts/documents/check.py) | `delivery_role` задокументирован в [`change_process.md`](../../operations/change_process.md) §8.1; новая проверка `check_terminal_outcome_delivery_role` в `check.py` нашла и исправила несогласованность — [`TASK_014`](../tasks/task_014_real_runtime.md)–[`TASK_016`](../tasks/task_016_real_telegram.md) были `component`, хотя должны были быть `terminal_outcome`. |
| AUD-013 | medium | remediated_pending_verification | 2026-08-29 | 2026-09-12 | repository_owner | [Карточка](audit_baseline_2026_08_29.md#aud-013), [`control.py`](../../src/owner_control/control.py), [`recover_lock.py`](../../operations/scripts/owner_control/recover_lock.py) | Блокировка теперь пишет PID и timestamp держателя в `holder.json`; добавлена явная (не автоматическая) команда восстановления, отказывающая при живом PID держателя, плюс runbook [`recover_stale_sensitive_action_lock.md`](../../operations/procedures/recover_stale_sensitive_action_lock.md). |
| AUD-014 | medium | remediated_pending_verification | 2026-08-29 | 2026-09-12 | repository_owner | [Карточка](audit_baseline_2026_08_29.md#aud-014), [`procedure_map.md`](../../operations/procedure_map.md) | Все 6 документов добавлены в таблицу §2 с назначением, входными условиями и результатом. |
| AUD-015 | medium | remediated_pending_verification | 2026-08-29 | 2026-09-12 | repository_owner | [Карточка](audit_baseline_2026_08_29.md#aud-015), [`check.py`](../../operations/scripts/documents/check.py) | Исключения сужены до `ValueError`/`OSError` (реально ожидаемых от коллекторов) с логированием в stderr; любое другое исключение теперь распространяется, а не поглощается. |
| AUD-016 | low | remediated_pending_verification | 2026-08-29 | 2026-09-19 | repository_owner | [Карточка](audit_baseline_2026_08_29.md#aud-016), [`telegram.py`](../../src/channels/telegram.py), [`test_channels.py`](../../operations/tests/product/test_channels.py) | Добавлен тест таймаута `receive()` (мгновенный fake timeout, без реального ожидания 30с); покрытие подтверждает, что путь больше не мёртвый. |
| AUD-017 | low | remediated_pending_verification | 2026-08-29 | 2026-09-19 | repository_owner | [Карточка](audit_baseline_2026_08_29.md#aud-017), [`test_quality_integration.py`](../../operations/tests/test_quality_integration.py), [`run_unittests.py`](../../operations/scripts/quality/run_unittests.py) | Тест теперь шимит все имена интерпретаторов, которые пробует `find_python()` (не только `python3.12`); `run_unittests.py` даёт `unexpectedSuccesses` отдельный exit code 3 и сообщение. |
| AUD-018 | low | remediated_pending_verification | 2026-08-29 | 2026-09-19 | repository_owner | [Карточка](audit_baseline_2026_08_29.md#aud-018), [`test_007.md`](../tests/test_007.md), [`quality_registry.json`](../../operations/quality_registry.json), `.gitignore` | [`TEST_007`](../tests/test_007.md) приведён к единому числу (17, с учётом нового теста AUD-016); в [`quality_registry.json`](../../operations/quality_registry.json) добавлено пояснение фазирования; устаревший блок `generated/` удалён из `.gitignore`. |
| AUD-019 | low | remediated_pending_verification | 2026-08-29 | 2026-09-19 | repository_owner | [Карточка](audit_baseline_2026_08_29.md#aud-019), [`sqlite_store.py`](../../src/task_state/sqlite_store.py), [`test_persistent_task_state.py`](../../operations/tests/product/test_persistent_task_state.py) | Добавлены тесты по образцу `test_owner_control.py`: невалидный/не-dict JSON и неизвестный `state`, записанные напрямую в SQLite, подтверждают `TaskLifecycleError`. |
| AUD-020 | medium | remediated_pending_verification | 2026-08-29 | 2026-09-05 | repository_owner | [Карточка](audit_baseline_2026_08_29.md#aud-020), [`repository_audit_system_prompt.md`](../../operations/repository_audit_system_prompt.md) §7.5, [`run_eval_suite.py`](../../operations/scripts/eval/run_eval_suite.py) | §7.5 требует eval/regression-набор; текущий `stub` profile доказывает только plumbing. Реальный profile должен быть явно зарегистрирован в [`TASK_015`](../tasks/task_015_real_model_provider.md), привязан к полному SHA и иметь отдельные expectations. |
| AUD-021 | high | remediated_pending_verification | 2026-08-29 | 2026-09-05 | repository_owner | [Карточка](audit_card_archive_2026_09_02.md#aud-021), [`adr_task_coverage.py`](../../operations/scripts/traceability/adr_task_coverage.py), [`TASK_013`](../tasks/task_013_inf_008.md)–[`TASK_015`](../tasks/task_015_real_model_provider.md) | Введено `TASK.decides`, active proposed ADR назначены незавершённым TASK, планирование и аудит требуют обратного прохода ADR → TASK; отрицательные tests блокируют потерю и дублирование владельца решения. Планируемый (`planned`) milestone деференциально откладывает назначение TASK до декомпозиции — владелец подтвердил 2026-08-30, см. AUD-025. |
| AUD-022 | high | remediated_pending_verification | 2026-08-30 | 2026-09-06 | repository_owner | [Карточка](audit_baseline_2026_08_30.md#aud-022), [`project_status.md`](../../project_status.md), [`audit_register.md`](#3-реестр), [`AGENTS.md`](../../AGENTS.md), [`project_check.yml`](../../.github/workflows/project_check.yml), [`test_checker_negative_paths.py`](../../operations/tests/test_checker_negative_paths.py) | Ссылки и owner-status исправлены, CI triggers согласованы, formatter drift и Mypy-регрессия нового section-contract test устранены; ожидается серверная проверка. |
| AUD-023 | high | remediated_pending_verification | 2026-08-30 | 2026-09-06 | repository_owner | [Карточка](audit_baseline_2026_08_30.md#aud-023), [`.gitignore`](../../.gitignore), [`.dockerignore`](../../.dockerignore), [`test_security_extended.py`](../../operations/tests/test_security_extended.py) | Root secret dirs закреплены, `src/secrets` видим Git, Docker context исключает `.env`/keys/credentials; добавлены negative policy tests. |
| AUD-024 | high | remediated_pending_verification | 2026-08-30 | 2026-09-06 | repository_owner | [Карточка](audit_baseline_2026_08_30.md#aud-024), [`ADR_003`](../../adr/adr_003_model_provider_interface.md), [`TASK_014`](../tasks/task_014_real_runtime.md), [`TASK_018`](../tasks/task_018_runtime_task_events.md), [`ADR_004`](../../adr/adr_004_task_events_and_logging.md), [`task_events.py`](../../src/observability/task_events.py), [`TEST_019`](../tests/test_019.md) | Реализованы отдельный `runtime_task_id` и коррелированные state/model/tool/policy/checkpoint/retry/error events; schema запрещает свободный текст, negative tests проверяют sentinel и разделение исполнений. |
| AUD-025 | medium | remediated_pending_verification | 2026-08-30 | 2026-09-13 | repository_owner | [Карточка](audit_baseline_2026_08_30.md#aud-025), [`adr_lifecycle.md`](../../operations/lifecycle/adr_lifecycle.md), [`change_process.md`](../../operations/change_process.md), [`adr_task_coverage.py`](../../operations/scripts/traceability/adr_task_coverage.py), [`task_template.md`](../../operations/templates/task_template.md), [`milestone_template.md`](../../operations/templates/milestone_template.md) | Процедуры и checker разделяют create/compare/accept и удаляют PR-approval shortcut. Владелец 2026-08-30 явно вернул planned-milestone исключение (TASK для далёкого `planned` milestone откладывается до декомпозиции) — единственная отменённая деталь этого fix, см. карточку. |
| AUD-026 | medium | remediated_pending_verification | 2026-08-30 | 2026-09-13 | repository_owner | [Карточка](audit_baseline_2026_08_30.md#aud-026), [`TASK_013`](../tasks/task_013_inf_008.md), [`paths_validation.py`](../../operations/scripts/quality/paths_validation.py) | Служебные пути удалены из активной TASK; новая проверка запрещает governance/audit paths в незавершённых product TASK. |
| AUD-027 | medium | remediated_pending_verification | 2026-08-30 | 2026-09-13 | repository_owner | [Карточка](audit_baseline_2026_08_30.md#aud-027), [`run_eval_suite.py`](../../operations/scripts/eval/run_eval_suite.py), [`test_eval_suite.py`](../../operations/tests/tooling/test_eval_suite.py) | CLI получил явные profiles и SHA-требование для non-stub; degraded non-stub profile проверенно завершает canonical entrypoint с кодом 1. |
| AUD-028 | medium | remediated_pending_verification | 2026-08-30 | 2026-09-13 | repository_owner | [Карточка](audit_card_archive_2026_09_02.md#aud-028), [`adr_006_agent_environment_framework.md`](../../adr/adr_006_agent_environment_framework.md), [`adr_007_cloud_provider_selection.md`](../../adr/adr_007_cloud_provider_selection.md), [`adr_lifecycle.md`](../../operations/lifecycle/adr_lifecycle.md) | Найдено при сведении параллельной ветки с `main`: два конкурирующих агента независимо переписали [`ADR_006`](../../adr/adr_006_agent_environment_framework.md) (CrewAI vs Hermes Agent) и [`ADR_007`](../../adr/adr_007_cloud_provider_selection.md) (двухсценарная структура была свёрнута в один сценарий). Владелец 2026-08-30 явно разрешил оба конфликта: [`ADR_006`](../../adr/adr_006_agent_environment_framework.md) объединён в четыре кандидата (LangGraph, CrewAI, Hermes Agent, собственная реализация); [`ADR_007`](../../adr/adr_007_cloud_provider_selection.md) вернулся к двум сценариям (A: Hetzner/DigitalOcean вне России; B: Selectel в бэклоге до проверки A). |
| AUD-029 | medium | remediated_pending_verification | 2026-08-30 | 2026-09-13 | repository_owner | [Карточка](audit_card_archive_2026_09_02.md#aud-029), [`ADR_004`](../../adr/adr_004_task_events_and_logging.md), [`TASK_018`](../tasks/task_018_runtime_task_events.md), [`AUD-024`](#aud-024) | Дубликат ID со случайно тем же номером из параллельной ветки — переномерован при слиянии. Сама находка (принятый [`ADR_004`](../../adr/adr_004_task_events_and_logging.md) не реализован в коде) уже отслеживается [`AUD-024`](#aud-024) и получила план исправления через [`TASK_018`](../tasks/task_018_runtime_task_events.md); отдельного действия не требуется. |
| AUD-030 | low | remediated_pending_verification | 2026-08-30 | 2026-09-20 | repository_owner | [Карточка](audit_card_archive_2026_09_02.md#aud-030), [`adr_003_model_provider_interface.md`](../../adr/adr_003_model_provider_interface.md), [`src/models/base.py`](../../src/models/base.py) | Дубликат ID со случайно тем же номером из параллельной ветки — переномерован при слиянии. Сама находка (расхождение имени `ModelProvider`/`ModelGateway` между ADR и кодом) уже устранена независимо: [`ADR_003`](../../adr/adr_003_model_provider_interface.md) переименован на `ModelGateway`, совпадает с кодом. |
| AUD-031 | medium | remediated_pending_verification | 2026-09-01 | 2026-09-08 | repository_owner | [Карточка](audit_card_archive_2026_09_02.md#aud-031), [`run_unittests.py`](../../operations/scripts/quality/run_unittests.py), [`test_quality_integration.py`](../../operations/tests/test_quality_integration.py) | Агент без согласования владельца ослабил политику «любой skip = провал» персональным исключением для одной причины skip, вместо того чтобы устранить сам skip. Откачено; настоящая причина (`os.chmod()` не выставляет POSIX exec-бит на Windows) исправлена в самом тесте. |
| AUD-032 | medium | remediated_pending_verification | 2026-09-01 | 2026-09-08 | repository_owner | [Карточка](audit_card_archive_2026_09_02.md#aud-032), [`test_concurrency.py`](../../operations/tests/test_concurrency.py), [`project.py`](../../operations/scripts/common/project.py) | Агент без согласования владельца заглушил `PermissionError` в тесте вместо того чтобы чинить продуктовый код. Откачено; `read_text()` теперь сам переживает эту гонку через bounded retry, симметрично уже принятому `_replace_with_retry`. |
| AUD-033 | medium | remediated_pending_verification | 2026-09-01 | 2026-09-08 | repository_owner | [Карточка](audit_card_archive_2026_09_02.md#aud-033), [`diagram_lint.py`](../../operations/scripts/documents/diagram_lint.py), [`architecture_diagram_style_guide.md`](../../operations/architecture/architecture_diagram_style_guide.md), [`personal_ai_platform_architecture.svg`](../../work/artefacts/architecture/personal_ai_platform_architecture.svg) | Агент без согласования владельца расширил формат `data-spec-id`, чтобы один узел мог заявлять несколько ID через пробел, вместо того чтобы разнести их по отдельным элементам. Откачено; линтер снова требует ровно один ID на элемент, схема переработана на `<tspan>`-теги. |
| AUD-034 | high | remediated_pending_verification | 2026-09-02 | 2026-09-09 | repository_owner | [Карточка](audit_baseline_2026_09_02.md#aud-034), [`diagram_lint.py`](../../operations/scripts/documents/diagram_lint.py), [`test_diagram_lint.py`](../../operations/tests/tooling/test_diagram_lint.py) | SVG разбирается через прямую pinned-зависимость `defusedxml`; hostile entity test подтверждает отказ без раскрытия содержимого, Bandit B314 устранён. |
| AUD-035 | medium | remediated_pending_verification | 2026-09-02 | 2026-09-16 | repository_owner | [Карточка](audit_baseline_2026_09_02.md#aud-035), [`project_check.yml`](../../.github/workflows/project_check.yml), [`.gitleaksignore`](../../.gitleaksignore), [`test_quality_integration.py`](../../operations/tests/test_quality_integration.py) | CI после полного unshallow запускает и `gitleaks dir`, и `gitleaks git`, сохраняет раздельные evidence; четыре проверенных учебных примера разрешены только точными fingerprints. |
| AUD-036 | medium | remediated_pending_verification | 2026-09-02 | 2026-09-16 | repository_owner | [Карточка](audit_baseline_2026_09_02.md#aud-036), [`human_status.py`](../../operations/scripts/status/human_status.py), [`project_status.md`](../../project_status.md) | Статус критических findings отделён от фактического Project check; без SHA-bound evidence dashboard явно сообщает, что проверка текущей редакции не подтверждена. |
| AUD-037 | low | remediated_pending_verification | 2026-09-02 | 2026-09-23 | repository_owner | [Карточка](audit_baseline_2026_09_02.md#aud-037), [`run_suite.py`](../../operations/scripts/quality/run_suite.py), [`test_quality_runner.py`](../../operations/tests/tooling/test_quality_runner.py) | Любой просроченный `review_date` незакрытой строки теперь блокирует gate; фиксированная дата в negative/edge tests делает проверку детерминированной. |
| AUD-038 | low | remediated_pending_verification | 2026-09-02 | 2026-09-23 | repository_owner | [Карточка](audit_baseline_2026_09_02.md#aud-038), [Индекс совместимости](#4-индекс-совместимости), [`audit_card_archive_2026_09_02.md`](audit_card_archive_2026_09_02.md), [`check.py`](../../operations/scripts/documents/check.py), [`test_checker_negative_paths.py`](../../operations/tests/test_checker_negative_paths.py) | В реестре оставлены состояния и компактный индекс; полные карточки находятся в датированных отчётах/архиве, checker блокирует missing, duplicate, orphan и неизвестные поля. |
| AUD-039 | medium | remediated_pending_verification | 2026-09-02 | 2026-09-16 | repository_owner | [Карточка](audit_baseline_2026_09_02.md#aud-039), [`task_016_real_telegram.md`](../tasks/task_016_real_telegram.md), [`TEST_020`](../tests/test_020.md), [`test_security_extended.py`](../../operations/tests/test_security_extended.py) | План требует secret token на каждом webhook update либо исходящий polling без ingress; linked TEST фиксирует отрицательный spoofed-owner-id сценарий. |
| AUD-040 | low | remediated_pending_verification | 2026-09-02 | 2026-09-23 | repository_owner | [Карточка](audit_baseline_2026_09_02.md#aud-040), [`pyproject.toml`](../../pyproject.toml), [`license_policy.md`](../../operations/policy/license_policy.md) | Подтверждён текущий private-режим репозитория; политика явно сохраняет all-rights-reserved без LICENSE и требует LICENSE, dependency review и security channel до публичного распространения. |
## 4. Индекс совместимости

Старые якорные ссылки сохранены; каждая строка перенаправляет к полной архивной карточке.

<a id="aud-001"></a>[AUD-001](audit_baseline_2026_08_28.md#aud-001)

<a id="aud-002"></a>[AUD-002](audit_baseline_2026_08_28.md#aud-002)

<a id="aud-003"></a>[AUD-003](audit_baseline_2026_08_28.md#aud-003)

<a id="aud-004"></a>[AUD-004](audit_baseline_2026_08_28.md#aud-004)

<a id="aud-005"></a>[AUD-005](audit_baseline_2026_08_28.md#aud-005)

<a id="aud-006"></a>[AUD-006](audit_baseline_2026_08_28.md#aud-006)

<a id="aud-007"></a>[AUD-007](audit_baseline_2026_08_29.md#aud-007)

<a id="aud-008"></a>[AUD-008](audit_baseline_2026_08_29.md#aud-008)

<a id="aud-009"></a>[AUD-009](audit_baseline_2026_08_29.md#aud-009)

<a id="aud-010"></a>[AUD-010](audit_baseline_2026_08_29.md#aud-010)

<a id="aud-011"></a>[AUD-011](audit_baseline_2026_08_29.md#aud-011)

<a id="aud-012"></a>[AUD-012](audit_baseline_2026_08_29.md#aud-012)

<a id="aud-013"></a>[AUD-013](audit_baseline_2026_08_29.md#aud-013)

<a id="aud-014"></a>[AUD-014](audit_baseline_2026_08_29.md#aud-014)

<a id="aud-015"></a>[AUD-015](audit_baseline_2026_08_29.md#aud-015)

<a id="aud-016"></a>[AUD-016](audit_baseline_2026_08_29.md#aud-016)

<a id="aud-017"></a>[AUD-017](audit_baseline_2026_08_29.md#aud-017)

<a id="aud-018"></a>[AUD-018](audit_baseline_2026_08_29.md#aud-018)

<a id="aud-019"></a>[AUD-019](audit_baseline_2026_08_29.md#aud-019)

<a id="aud-020"></a>[AUD-020](audit_baseline_2026_08_29.md#aud-020)

<a id="aud-021"></a>[AUD-021](audit_card_archive_2026_09_02.md#aud-021)

<a id="aud-022"></a>[AUD-022](audit_baseline_2026_08_30.md#aud-022)

<a id="aud-023"></a>[AUD-023](audit_baseline_2026_08_30.md#aud-023)

<a id="aud-024"></a>[AUD-024](audit_baseline_2026_08_30.md#aud-024)

<a id="aud-025"></a>[AUD-025](audit_baseline_2026_08_30.md#aud-025)

<a id="aud-026"></a>[AUD-026](audit_baseline_2026_08_30.md#aud-026)

<a id="aud-027"></a>[AUD-027](audit_baseline_2026_08_30.md#aud-027)

<a id="aud-028"></a>[AUD-028](audit_card_archive_2026_09_02.md#aud-028)

<a id="aud-029"></a>[AUD-029](audit_card_archive_2026_09_02.md#aud-029)

<a id="aud-030"></a>[AUD-030](audit_card_archive_2026_09_02.md#aud-030)

<a id="aud-031"></a>[AUD-031](audit_card_archive_2026_09_02.md#aud-031)

<a id="aud-032"></a>[AUD-032](audit_card_archive_2026_09_02.md#aud-032)

<a id="aud-033"></a>[AUD-033](audit_card_archive_2026_09_02.md#aud-033)

<a id="aud-034"></a>[AUD-034](audit_baseline_2026_09_02.md#aud-034)

<a id="aud-035"></a>[AUD-035](audit_baseline_2026_09_02.md#aud-035)

<a id="aud-036"></a>[AUD-036](audit_baseline_2026_09_02.md#aud-036)

<a id="aud-037"></a>[AUD-037](audit_baseline_2026_09_02.md#aud-037)

<a id="aud-038"></a>[AUD-038](audit_baseline_2026_09_02.md#aud-038)

<a id="aud-039"></a>[AUD-039](audit_baseline_2026_09_02.md#aud-039)

<a id="aud-040"></a>[AUD-040](audit_baseline_2026_09_02.md#aud-040)

## 5. Правило обновления

После зелёного `Project check` на точном SHA записи исправленных findings переводятся в `resolved` отдельным служебным PR. Для `accepted_risk` обязательно сохраняются явное решение владельца, ответственный, срок пересмотра и компенсирующий контроль. Удаление строк запрещено: закрытая finding остаётся историей реестра, а не удаляется.

