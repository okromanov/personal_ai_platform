---
id: audit_register
type: audit_register
document_state: current
version: 1.7
updated: 2026-08-30
depends_on: []
---

# Реестр результатов аудита

## 1. Назначение

Это единственный реестр стабильных идентификаторов `AUD-NNN`, состояния исправлений и формально принятых рисков. Новый аудит сопоставляет причину с существующим ID до создания следующего номера. Состояние `accepted_risk` допустимо только после явного решения владельца; отсутствие такого решения оставляет finding открытой.

Каждый запуск аудита отдельно публикует точечный отчёт `work/audit/audit_baseline_YYYY_MM_DD.md`, содержащий **только новые находки этого запуска** вместе с полным контекстом, доказательствами и разбором по столпам (см., например, [`audit_baseline_2026_08_29.md`](audit_baseline_2026_08_29.md)). Этот файл не создаётся заново при каждом аудите: это единственный источник, который читают канонический gate ([`run_suite.py`](../../operations/scripts/quality/run_suite.py)) и owner dashboard ([`human_status.py`](../../operations/scripts/status/human_status.py)) для текущего состояния всех находок. После публикации точечного отчёта его находки переносятся сюда; состояние существующих строк обновляется здесь же по мере исправления.

## 2. Допустимые состояния

- `open` — исправление не выполнено;
- `remediated_pending_verification` — изменение реализовано, но обязательная проверка на точном SHA ещё не подтверждена;
- `resolved` — исправление и его обязательная проверка подтверждены;
- `accepted_risk` — риск принят владельцем с ответственным и датой пересмотра.

## 3. Реестр

| ID | Severity | State | First seen | Review date | Owner | Evidence | Resolution |
|---|---|---|---|---|---|---|---|
| AUD-001 | high | remediated_pending_verification | 2026-08-27 | 2026-09-02 | repository_owner | [`.github/workflows/project_check.yml`](../../.github/workflows/project_check.yml) | Удалён отдельный write-capable workflow; health evidence остаётся SHA-bound Actions artifact. |
| AUD-002 | medium | remediated_pending_verification | 2026-08-27 | 2026-09-02 | repository_owner | [`pre_commit_hook.sh`](../../operations/hooks/pre_commit_hook.sh), [`test_quality_integration.py`](../../operations/tests/test_quality_integration.py) | Регенерация стала blocking; post-mutation fast gate и negative test исключают fail-open. |
| AUD-003 | medium | remediated_pending_verification | 2026-08-27 | 2026-09-02 | repository_owner | [`dockerfile`](../../dockerfile), [`project_check.yml`](../../.github/workflows/project_check.yml) | Base image закреплён digest; CI выполняет build/run/health и создаёт SBOM. |
| AUD-004 | medium | remediated_pending_verification | 2026-08-27 | 2026-09-02 | repository_owner | [`state_io.py`](../../src/owner_control/state_io.py), [`test_owner_control.py`](../../operations/tests/product/test_owner_control.py) | После replace выполняется POSIX directory fsync; отказ durability barrier распространяется вызывающему коду. |
| AUD-005 | low | remediated_pending_verification | 2026-08-27 | 2026-09-02 | repository_owner | [`run_suite.py`](../../operations/scripts/quality/run_suite.py), [`test_quality_runner.py`](../../operations/tests/tooling/test_quality_runner.py) | Каждый шаг gate ограничен 300 секундами и выдаёт локализованную ошибку timeout. |
| AUD-006 | low | remediated_pending_verification | 2026-08-27 | 2026-09-02 | repository_owner | [Раздел 3](#3-реестр), [`run_suite.py`](../../operations/scripts/quality/run_suite.py) | Реестр создан; gate проверяет ID, состояния, owner и review date. |
| AUD-007 | critical | open | 2026-08-29 | 2026-09-05 | repository_owner | [`project_check.yml`](../../.github/workflows/project_check.yml), [`task_012_inf_007.md`](../tasks/task_012_inf_007.md) | Владелец 2026-08-30 решил пока не восстанавливать Actions. Это не принятие риска: finding остаётся `open`, проект — `NOT READY`, серверное evidence отсутствует до первого реального зелёного прогона. |
| AUD-008 | high | remediated_pending_verification | 2026-08-29 | 2026-09-05 | repository_owner | [`template_contracts.py`](../../operations/scripts/documents/template_contracts.py), [`human_status.py`](../../operations/scripts/status/human_status.py), [`m01_final_report.md`](../acceptance/m01_final_report.md) | Оба mypy-типа исправлены (`mypy` чист); [`m01_final_report.md`](../acceptance/m01_final_report.md) перегенерирован через `render_final_report()`, путь совпадает с генератором. |
| AUD-009 | high | remediated_pending_verification | 2026-08-29 | 2026-09-05 | repository_owner | [`m01.json`](../acceptance/m01.json), [`adr_001_language_and_runtime.md`](../../adr/adr_001_language_and_runtime.md)–[`adr_004_task_events_and_logging.md`](../../adr/adr_004_task_events_and_logging.md) | [`ADR_001`](../../adr/adr_001_language_and_runtime.md)–[`ADR_004`](../../adr/adr_004_task_events_and_logging.md) реально переведены в `accepted` (единственные с `traces_to: m01`); [`m01.json`](../acceptance/m01.json) исправлен на эти 4 с прозрачной корректирующей записью; новая проверка [`check_acceptance_adr_transitions`](../../operations/scripts/documents/check.py) в `check.py` предотвращает рецидив. |
| AUD-010 | medium | remediated_pending_verification | 2026-08-29 | 2026-09-12 | repository_owner | [`human_status.py`](../../operations/scripts/status/human_status.py), [`project_status.md`](../../project_status.md) | Добавлена строка «Состояние gate/CI» (громко показывает открытые critical-находки) и явная пометка terminal-outcome задач в таблице покрытия. |
| AUD-011 | medium | remediated_pending_verification | 2026-08-29 | 2026-09-12 | repository_owner | [`document_frontmatter_standard.md`](../../operations/document_frontmatter_standard.md), [`change_process.md`](../../operations/change_process.md) | Документ помечен `document_state: superseded` со ссылкой на [`change_process.md`](../../operations/change_process.md) §8; уникальное содержимое (порядок полей) перенесено туда. |
| AUD-012 | medium | remediated_pending_verification | 2026-08-29 | 2026-09-12 | repository_owner | [`change_process.md`](../../operations/change_process.md), [`check.py`](../../operations/scripts/documents/check.py) | `delivery_role` задокументирован в [`change_process.md`](../../operations/change_process.md) §8.1; новая проверка `check_terminal_outcome_delivery_role` в `check.py` нашла и исправила несогласованность — [`TASK_014`](../tasks/task_014_real_runtime.md)–[`TASK_016`](../tasks/task_016_real_telegram.md) были `component`, хотя должны были быть `terminal_outcome`. |
| AUD-013 | medium | remediated_pending_verification | 2026-08-29 | 2026-09-12 | repository_owner | [`control.py`](../../src/owner_control/control.py), [`recover_lock.py`](../../operations/scripts/owner_control/recover_lock.py) | Блокировка теперь пишет PID и timestamp держателя в `holder.json`; добавлена явная (не автоматическая) команда восстановления, отказывающая при живом PID держателя, плюс runbook [`recover_stale_sensitive_action_lock.md`](../../operations/procedures/recover_stale_sensitive_action_lock.md). |
| AUD-014 | medium | remediated_pending_verification | 2026-08-29 | 2026-09-12 | repository_owner | [`procedure_map.md`](../../operations/procedure_map.md) | Все 6 документов добавлены в таблицу §2 с назначением, входными условиями и результатом. |
| AUD-015 | medium | remediated_pending_verification | 2026-08-29 | 2026-09-12 | repository_owner | [`check.py`](../../operations/scripts/documents/check.py) | Исключения сужены до `ValueError`/`OSError` (реально ожидаемых от коллекторов) с логированием в stderr; любое другое исключение теперь распространяется, а не поглощается. |
| AUD-016 | low | remediated_pending_verification | 2026-08-29 | 2026-09-19 | repository_owner | [`telegram.py`](../../src/channels/telegram.py), [`test_channels.py`](../../operations/tests/product/test_channels.py) | Добавлен тест таймаута `receive()` (мгновенный fake timeout, без реального ожидания 30с); покрытие подтверждает, что путь больше не мёртвый. |
| AUD-017 | low | remediated_pending_verification | 2026-08-29 | 2026-09-19 | repository_owner | [`test_quality_integration.py`](../../operations/tests/test_quality_integration.py), [`run_unittests.py`](../../operations/scripts/quality/run_unittests.py) | Тест теперь шимит все имена интерпретаторов, которые пробует `find_python()` (не только `python3.12`); `run_unittests.py` даёт `unexpectedSuccesses` отдельный exit code 3 и сообщение. |
| AUD-018 | low | remediated_pending_verification | 2026-08-29 | 2026-09-19 | repository_owner | [`test_007.md`](../tests/test_007.md), [`quality_registry.json`](../../operations/quality_registry.json), `.gitignore` | [`TEST_007`](../tests/test_007.md) приведён к единому числу (17, с учётом нового теста AUD-016); в [`quality_registry.json`](../../operations/quality_registry.json) добавлено пояснение фазирования; устаревший блок `generated/` удалён из `.gitignore`. |
| AUD-019 | low | remediated_pending_verification | 2026-08-29 | 2026-09-19 | repository_owner | [`sqlite_store.py`](../../src/task_state/sqlite_store.py), [`test_persistent_task_state.py`](../../operations/tests/product/test_persistent_task_state.py) | Добавлены тесты по образцу `test_owner_control.py`: невалидный/не-dict JSON и неизвестный `state`, записанные напрямую в SQLite, подтверждают `TaskLifecycleError`. |
| AUD-020 | medium | remediated_pending_verification | 2026-08-29 | 2026-09-05 | repository_owner | [`repository_audit_system_prompt.md`](repository_audit_system_prompt.md) §7.5, [`run_eval_suite.py`](../../operations/scripts/eval/run_eval_suite.py) | §7.5 требует eval/regression-набор; текущий `stub` profile доказывает только plumbing. Реальный profile должен быть явно зарегистрирован в [`TASK_015`](../tasks/task_015_real_model_provider.md), привязан к полному SHA и иметь отдельные expectations. |
| AUD-021 | high | remediated_pending_verification | 2026-08-29 | 2026-09-05 | repository_owner | [`adr_task_coverage.py`](../../operations/scripts/traceability/adr_task_coverage.py), [`TASK_013`](../tasks/task_013_inf_008.md)–[`TASK_019`](../tasks/task_019_m04_data_storage.md) | Введено `TASK.decides`; каждый proposed ADR любого milestone назначен одной незавершённой TASK, включая [`ADR_008`](../../adr/adr_008_data_storage_schema.md) → [`TASK_019`](../tasks/task_019_m04_data_storage.md); negative tests блокируют потерю и дублирование владельца. |
| AUD-022 | high | remediated_pending_verification | 2026-08-30 | 2026-09-06 | repository_owner | [`project_status.md`](../../project_status.md), [`audit_register.md`](#3-реестр), [`AGENTS.md`](../../AGENTS.md), [`project_check.yml`](../../.github/workflows/project_check.yml), [`test_checker_negative_paths.py`](../../operations/tests/test_checker_negative_paths.py) | Ссылки и owner-status исправлены, CI triggers согласованы, formatter drift и Mypy-регрессия нового section-contract test устранены; ожидается серверная проверка. |
| AUD-023 | high | remediated_pending_verification | 2026-08-30 | 2026-09-06 | repository_owner | [`.gitignore`](../../.gitignore), [`.dockerignore`](../../.dockerignore), [`test_security_extended.py`](../../operations/tests/test_security_extended.py) | Root secret dirs закреплены, `src/secrets` видим Git, Docker context исключает `.env`/keys/credentials; добавлены negative policy tests. |
| AUD-024 | high | open | 2026-08-30 | 2026-09-06 | repository_owner | [`ADR_003`](../../adr/adr_003_model_provider_interface.md), [`TASK_014`](../tasks/task_014_real_runtime.md), [`TASK_018`](../tasks/task_018_runtime_task_events.md), [`TASK_019`](../tasks/task_019_m04_data_storage.md) | Контракт `ModelGateway` и candidate sets согласованы, [`ADR_008`](../../adr/adr_008_data_storage_schema.md) получил owner TASK. Остаётся `open` до реализации событий [`ADR_004`](../../adr/adr_004_task_events_and_logging.md) в [`TASK_018`](../tasks/task_018_runtime_task_events.md). |
| AUD-025 | medium | remediated_pending_verification | 2026-08-30 | 2026-09-13 | repository_owner | [`adr_lifecycle.md`](../../operations/adr_lifecycle.md), [`change_process.md`](../../operations/change_process.md), [`adr_task_coverage.py`](../../operations/scripts/traceability/adr_task_coverage.py), [`task_template.md`](../../operations/templates/task_template.md), [`milestone_template.md`](../../operations/templates/milestone_template.md) | Процедуры, checker и защищённые шаблоны согласованы: каждый proposed ADR любого milestone немедленно получает одну незавершённую TASK-владельца; ожидается полный gate и серверная проверка. |
| AUD-026 | medium | remediated_pending_verification | 2026-08-30 | 2026-09-13 | repository_owner | [`TASK_013`](../tasks/task_013_inf_008.md), [`paths_validation.py`](../../operations/scripts/quality/paths_validation.py) | Служебные пути удалены из активной TASK; новая проверка запрещает governance/audit paths в незавершённых product TASK. |
| AUD-027 | medium | remediated_pending_verification | 2026-08-30 | 2026-09-13 | repository_owner | [`run_eval_suite.py`](../../operations/scripts/eval/run_eval_suite.py), [`test_eval_suite.py`](../../operations/tests/tooling/test_eval_suite.py) | CLI получил явные profiles и SHA-требование для non-stub; degraded non-stub profile проверенно завершает canonical entrypoint с кодом 1. |

## 4. Карточки findings

<a id="aud-001"></a>
### AUD-001 — workflow мог напрямую изменять основную ветку

- **Наблюдение:** отдельный workflow публикации health report имел право `contents: write`, создавал коммит и выполнял прямой push. Результат служебной проверки мог изменять репозиторий в обход обычного PR и проверки точного SHA.
- **Риск:** компрометация workflow или ошибка генератора позволяла записать непроверенное содержимое в основную ветку; автоматическая запись также могла запускать каскад CI и смешивать доказательство проверки с состоянием проверяемого кода.
- **Ожидаемое состояние:** CI работает с минимальными правами, не изменяет репозиторий и сохраняет отчёты как неизменяемые artifacts, привязанные к проверяемому SHA.
- **Исправление:** write-capable workflow удалён. Канонический [`Project check`](../../.github/workflows/project_check.yml) формирует runtime health evidence и загружает его как artifact без записи в Git.
- **Критерий закрытия:** зелёный `Project check` на точном SHA подтверждает создание и загрузку health artifact; в активных workflows отсутствуют прямой push и необоснованное `contents: write`.

<a id="aud-002"></a>
### AUD-002 — pre-commit допускал fail-open при регенерации

- **Наблюдение:** ошибки вспомогательной регенерации подавлялись, поэтому hook мог завершиться успешно после неуспешного обновления производных файлов. После мутации не выполнялась повторная быстрая проверка итогового состояния.
- **Риск:** в коммит могли попадать устаревшие или частично обновлённые `generated/*` и статусные документы, хотя локальный контроль показывал успех.
- **Ожидаемое состояние:** любой обязательный генератор является blocking; после изменений hook проверяет уже окончательное состояние репозитория.
- **Исправление:** [`pre_commit_hook.sh`](../../operations/hooks/pre_commit_hook.sh) и связанный скрипт регенерации теперь распространяют ненулевой код возврата и повторяют fast suite после мутаций. [`test_quality_integration.py`](../../operations/tests/test_quality_integration.py) содержит negative test отказа генератора.
- **Критерий закрытия:** negative test подтверждает ненулевое завершение hook при ошибке генератора, а повторный запуск на стабильном дереве не создаёт drift.

<a id="aud-003"></a>
### AUD-003 — контейнерная поставка была недостаточно воспроизводимой и проверяемой

- **Наблюдение:** базовый Docker image не был закреплён неизменяемым digest, а CI не подтверждал полный цикл build/run/health и не формировал перечень программных компонентов поставки.
- **Риск:** один и тот же Git SHA мог собираться на различной базе; ошибки контейнерного запуска и изменения транзитивного состава обнаруживались бы только при развёртывании, а анализ уязвимостей и лицензий не имел полного входа.
- **Ожидаемое состояние:** база закреплена полным OCI digest; точный исходный SHA проходит реальную контейнерную сборку и health-check; для образа сохраняются digest и SBOM.
- **Исправление:** [`dockerfile`](../../dockerfile) использует digest-pinned Python base. [`Project check`](../../.github/workflows/project_check.yml) собирает и запускает image, сверяет health и `APP_VERSION`, фиксирует digests и создаёт SPDX JSON SBOM.
- **Критерий закрытия:** зелёный `Project check` на точном SHA содержит успешные Docker build/run/health шаги и загруженный SBOM вместе с digest evidence.

<a id="aud-004"></a>
### AUD-004 — атомарная запись состояния не гарантировала POSIX durability

- **Наблюдение:** запись JSON синхронизировала временный файл и выполняла atomic replace, но не синхронизировала родительский каталог после замены имени.
- **Риск:** после внезапного отключения питания или сбоя ОС вызов мог быть сообщён как успешный, хотя directory entry ещё не был устойчиво сохранён. Это особенно существенно для owner-control и emergency state.
- **Ожидаемое состояние:** на POSIX успешный результат возвращается только после последовательности file fsync → replace → directory fsync; отказ последнего барьера не скрывается. На Windows явно документируется отсутствие переносимого аналога directory fsync.
- **Исправление:** [`state_io.py`](../../src/owner_control/state_io.py) синхронизирует родительский каталог после `os.replace` на POSIX. [`test_owner_control.py`](../../operations/tests/product/test_owner_control.py) проверяет порядок операций и распространение ошибки.
- **Критерий закрытия:** Linux- и Windows-проверки проходят на точном SHA; POSIX-тест подтверждает порядок durability barriers и controlled failure при ошибке directory fsync.

<a id="aud-005"></a>
### AUD-005 — шаги quality gate могли зависать без контролируемого завершения

- **Наблюдение:** runner запускал внешние проверки без общего ограничения времени на отдельный шаг.
- **Риск:** зависший тест или инструмент мог удерживать локальный hook либо CI до внешнего принудительного завершения, не указывая владельцу конкретный зависший этап и не сохраняя полезную диагностику.
- **Ожидаемое состояние:** каждый шаг имеет явный конечный timeout, локализованное сообщение об ошибке и сохраняемое доступное output evidence.
- **Исправление:** [`run_suite.py`](../../operations/scripts/quality/run_suite.py) ограничивает шаг 300 секундами по умолчанию, обрабатывает `TimeoutExpired`, записывает доступный вывод и завершает gate контролируемой ошибкой с именем шага. Поведение проверяет [`test_quality_runner.py`](../../operations/tests/tooling/test_quality_runner.py).
- **Критерий закрытия:** автоматический тест с коротким timeout завершается предсказуемо, называет зависший шаг и не оставляет runner в состоянии бесконечного ожидания.

<a id="aud-006"></a>
### AUD-006 — отсутствовал долговечный реестр результатов аудита

- **Наблюдение:** findings и состояние их устранения жили в тексте конкретного аудита или PR без единого стабильного реестра идентификаторов, владельцев и сроков пересмотра.
- **Риск:** повторные аудиты могли дублировать одну причину под разными формулировками; незакрытые риски терялись после слияния PR, а статус исправления нельзя было однозначно проверить автоматически.
- **Ожидаемое состояние:** каждый finding имеет стабильный ID, severity, lifecycle state, дату обнаружения, владельца, дату пересмотра, evidence, решение и подробную карточку причины и закрытия.
- **Исправление:** создан этот реестр; [`run_suite.py`](../../operations/scripts/quality/run_suite.py) блокирует отсутствие записей, некорректные или повторные ID и открытые состояния без owner/review date.
- **Критерий закрытия:** gate успешно валидирует реестр; все реализованные исправления подтверждены зелёным `Project check` на точном SHA и затем переведены в `resolved` отдельным служебным PR.

<a id="aud-007"></a>
### AUD-007 — CI не диспетчеризует джобы 4 дня подряд; ~30 мёрджей ушли без проверки gate

- **Severity/Confidence/Evidence state:** critical / high / CONFIRMED
- **Файл:** [`.github/workflows/project_check.yml`](../../.github/workflows/project_check.yml); история запусков GitHub Actions (API); [`task_012_inf_007.md`](../tasks/task_012_inf_007.md) §8
- **Ожидаемый контракт:** AGENTS.md §3 — «Слияние или принятие этапа запрещено, пока общий gate не подтверждён для точного SHA»; `Project check` обязан выполняться на каждый push/PR.
- **Наблюдаемое поведение:** запросил историю запусков `project_check.yml` на `main` через GitHub API. Последний реально отработавший (~2 минуты, зелёный) запуск — 2026-08-25 06:38 UTC (run #253, коммит `c6422e6`). Каждый запуск начиная с 2026-08-25 07:36 UTC и до текущего HEAD (2026-08-29 12:26, run #614) завершается неудачей за 2–13 секунд, без логов (404 при попытке скачать), оба джоба (`ubuntu-latest` и `windows-latest`) — то есть раннер вообще не назначался, а не упал на реальном шаге. Причина самораскрыта в [`task_012_inf_007.md`](../tasks/task_012_inf_007.md) §8: «серверный GitHub Actions gate ожидает восстановления квоты после 1 сентября 2026 года; успешный CI не заявляется».
- **Воздействие и достижимость:** технической защиты правила «merge только после зелёного gate» не существует (самораскрыто в [`SEC_CTL_018`](../../specifications/system_specification.md#sec_ctl_018) — read-only автоматизация может только постфактум проверить, что push пришёл из смёрженного PR). За ~4 дня в `main` попало ~30 мёрджей, включая весь цикл `codex/audit-*`, без единой реальной проверки. Все 6 записей реестра `AUD-001…006` физически не могут быть подтверждены зелёным CI, пока это не исправлено.
- **Как воспроизвести:** запросить `GET /repos/okromanov/personal_ai_platform/actions/workflows/project_check.yml/runs?branch=main` — все записи после 2026-08-25 07:36 UTC имеют `conclusion: failure` и длительность в секундах.
- **Рекомендованное исправление:** дождаться восстановления квоты (после 2026-09-01) и получить хотя бы один реальный прогон на актуальном SHA; рассмотреть сокращение триггера CI (сейчас — каждый push в каждую ветку), чтобы не исчерпывать квоту повторно.
- **Как проверить исправление:** `actions_list`/`actions_get` показывают `conclusion: success` с реалистичной длительностью (~1-2 минуты) и непустыми логами на точном SHA.
- **Частично исправлено (2026-08-29):** вторая часть рекомендации выполнена — [`project_check.yml`](../../.github/workflows/project_check.yml) больше не триггерится на `push` в произвольную ветку (только `main`); `pull_request` по-прежнему покрывает каждый push в открытый PR. Первая часть (дождаться восстановления квоты) вне нашей власти — остаётся `open`.
- **Решение владельца (2026-08-30):** Actions пока не восстанавливать. Это не перевод в `accepted_risk`: finding остаётся `critical/open`, серверное evidence отсутствует, readiness остаётся `NOT READY`.

<a id="aud-008"></a>
### AUD-008 — Канонический gate реально красный на HEAD по двум независимым причинам

- **Severity/Confidence/Evidence state:** high / high / CONFIRMED
- **Файл:** [`template_contracts.py:208`](../../operations/scripts/documents/template_contracts.py), [`human_status.py:125`](../../operations/scripts/status/human_status.py), [`test_quality_integration.py:150`](../../operations/tests/test_quality_integration.py), [`m01_final_report.md:31,51`](../acceptance/m01_final_report.md)
- **Ожидаемый контракт:** `run_suite.py full` обязан завершаться с exit 0 на коммитах, допущенных к слиянию ([`quality_baseline.json`](../../operations/quality_baseline.json): `mypy_error_budget: 0`, без per-file исключений).
- **Наблюдаемое поведение:** запуск `run_suite.py full` в изолированной среде (worktree на точном HEAD SHA + venv с hash-verified pinned зависимостями) даёт два независимых провала: (а) `Mypy regression: 2 errors exceeds baseline budget 0` — `template_contracts.py:208` ("object" has no attribute "__iter__") и `human_status.py:125` (несовместимый тип tuple при `list.append`), оба трассируются через `git blame` к коммитам `dc4ee8b`/`f44cb1a` (последний мёрдж, PR #65/#63); (б) независимо подтверждено вторым прогоном: `test_final_report_matches_current_repository_state` падает, потому что `update_completion_report.py` был переписан в том же коммите `dc4ee8b`, но [`m01_final_report.md`](../acceptance/m01_final_report.md) не был полностью перегенерирован — файл всё ещё ссылается на `work/m01.json`, тогда как фактический путь (и то, что теперь вычисляет генератор) — [`work/acceptance/m01.json`](../acceptance/m01.json).
- **Воздействие и достижимость:** оба дефекта введены самим последним мёрджем и блокируют gate независимо друг от друга — исправление только mypy не сделает `run_suite.py full` зелёным.
- **Как воспроизвести:** `git worktree add /tmp/w 218eb61f5b6461c65d7250ba23ac8c5dae066013 && cd /tmp/w && python3.12 -m venv .venv && .venv/bin/pip install --require-hashes -r operations/quality/requirements_dev.txt && .venv/bin/python operations/scripts/quality/run_suite.py full`.
- **Рекомендованное исправление:** добавить типовые аннотации/приведения в `template_contracts.py`/`human_status.py`; перегенерировать [`m01_final_report.md`](../acceptance/m01_final_report.md) через `render_final_report()` и закоммитить результат байт-в-байт (кроме поля `updated:`).
- **Как проверить исправление:** `run_suite.py full` доходит до конца без ошибок на mypy/Unit tests шагах на новом SHA.
- **Исправлено (2026-08-29):** `assert_registered_output()` сузило тип `outputs` через `isinstance`; `_audit_status()` строит tuple явно через `match.group(1..3)` вместо `match.groups()`. `mypy` чист на обоих файлах. [`m01_final_report.md`](../acceptance/m01_final_report.md) перегенерирован — путь [`work/acceptance/m01.json`](../acceptance/m01.json) совпадает с генератором.
- **Повторная верификация (2026-08-30):** pinned Mypy выявил четыре нулевых-baseline ошибки в ADR-checker и тестовых `TaskItem` fixtures; типизация и обязательное `delivery_role` исправлены, Mypy снова проходит с нулём ошибок. Канонический тест также подтвердил drift [`m01_final_report.md`](../acceptance/m01_final_report.md); отчёт повторно пересобран зарегистрированным `update_completion_report.py m01`.

<a id="aud-009"></a>
### AUD-009 — Акт приёмки m01 заявляет недостоверный переход всех 9 ADR в accepted

- **Severity/Confidence/Evidence state:** high / high / CONFIRMED
- **Файл:** [`m01.json:27-63`](../acceptance/m01.json); коммит `a7831afbe2d3417ba71b1e68c0ee1254116151ca`; [`adr_001_language_and_runtime.md`](../../adr/adr_001_language_and_runtime.md) и остальные 8 ADR
- **Ожидаемый контракт:** акт приёмки милестона — канонический источник истины о завершении этапа ([`project_rules.md`](../../project_rules.md) §2); он не должен утверждать эффект, которого не было.
- **Наблюдаемое поведение:** [`m01.json`](../acceptance/m01.json) содержит массив `adr_transitions` из 9 записей, каждая `"state_change": "proposed → accepted"`. `git log -p --all -- adr/` не содержит ни одного вхождения строки `decision_state: accepted` за всю историю репозитория. `git show --stat a7831af` (коммит, чьё сообщение заявляет этот переход) не затрагивает ни одного файла под `adr/`. На SHA `218eb61` все 9 ADR остаются `decision_state: proposed`. Отдельно: [`ADR_005`](../../adr/adr_005_first_model_provider_selection.md)–[`ADR_009`](../../adr/adr_009_secret_management_strategy.md) указывают `traces_to` не на [`m01`](../../milestones.md#m01), а на [`m02`](../../milestones.md#m02)/[`m04`](../../milestones.md#m04)/[`m06`](../../milestones.md#m06) — переход для них не мог произойти в принципе по логике `apply.py`, независимо от того, что реально выполнялось.
- **Воздействие и достижимость:** не блокирует механически приёмку [`m01`](../../milestones.md#m01) (критерии [`milestones.md#m01`](../../milestones.md#m01) не требуют ADR-acceptance как gate), но высокоавторитетный evidence-документ содержит конкретное, опровержимое ложное утверждение — тот самый класс самообмана инструмента, который [`AGENTS.md`](../../AGENTS.md) §5.1 прямо запрещает для gate/evidence.
- **Как воспроизвести:** `git log -p --all -- adr/ | grep "decision_state: accepted"` (пусто); `git show --stat a7831afbe2d3417ba71b1e68c0ee1254116151ca` (нет пути `adr/`); `grep decision_state adr/adr_*.md` (все `proposed`).
- **Рекомендованное исправление:** решение владельца — либо реально выполнить переход [`ADR_001`](../../adr/adr_001_language_and_runtime.md)–[`ADR_004`](../../adr/adr_004_task_events_and_logging.md) (единственные, кто `traces_to: m01`) отдельным PR с честной evidence-записью, либо скорректировать нарратив [`m01.json`](../acceptance/m01.json)/[`adr_lifecycle.md`](../../operations/adr_lifecycle.md) корректирующей записью (без переписывания истории).
- **Как проверить исправление:** `grep decision_state adr/adr_00{1,2,3,4}_*.md` показывает `accepted`, либо [`m01.json`](../acceptance/m01.json) больше не содержит недостоверного `adr_transitions`.
- **Исправлено (2026-08-29), комплексно по решению владельца:** расследование показало, что запись НИКОГДА не создавалась через `apply.py` — её JSON-форма не совпадает со схемой скрипта (нет `schema_version`/`type`), подтверждая, что она создана вручную в обход контролируемого процесса. Выполнено: (1) [`ADR_001`](../../adr/adr_001_language_and_runtime.md)–[`ADR_004`](../../adr/adr_004_task_events_and_logging.md) реально переведены в `accepted` (`decision_state`, `updated: 2026-08-29`) — той же трансформацией, что выполнил бы `apply.py`; (2) [`m01.json`](../acceptance/m01.json) исправлен на `adr_transitions` из 4 (не 9) записей плюс явное поле `adr_transitions_correction`, документирующее расхождение и дату исправления; (3) [`milestones.md`](../../milestones.md) получил примечание в разделе [`m01`](../../milestones.md#m01); (4) добавлена новая проверка `check_acceptance_adr_transitions` в [`check.py`](../../operations/scripts/documents/check.py), сверяющая любую заявленную ADR-транзицию в `work/acceptance/*.json` с реальным `decision_state` на диске — это и есть «исправление скрипта»: не патч самой логики перехода (она была верна), а гарантия, что расхождение записи со скриптом больше не пройдёт незамеченным.

<a id="aud-010"></a>
### AUD-010 — Owner-facing статус не показывает состояние gate/CI и переоценивает близость к цели milestone

- **Severity/Confidence/Evidence state:** medium / high / CONFIRMED
- **Файл:** [`project_status.md`](../../project_status.md)
- **Наблюдаемое поведение:** владелец, читающий только [`project_status.md`](../../project_status.md), не может увидеть ни AUD-007 (CI не работает), ни AUD-008 (gate реально красный локально), ни то, что ADR, на которые опираются заявленные возможности, всё ещё `proposed` (AUD-009). Рамка «13/17 задач [`m02`](../../milestones.md#m02) выполнено» не даёт сигнала, что все 4 оставшиеся задачи ([`TASK_014`](../tasks/task_014_real_runtime.md)–[`TASK_017`](../tasks/task_017_m02_live_e2e.md)) несут ~100% внешнего, пользовательского риска milestone (все три внешних адаптера — Telegram Bot API, agent runtime, model provider — остаются эхо-заглушками).
- **Рекомендованное исправление:** добавить в генератор статуса поле состояния gate/CI (или явную пометку «последняя проверка недоступна»); добавить визуальное отличие component vs terminal-outcome задач в таблице (используя уже существующее поле `delivery_role`, см. AUD-012).
- **Как проверить исправление:** обновлённый [`project_status.md`](../../project_status.md) содержит статус последнего известного прогона gate и визуально выделяет оставшиеся terminal-outcome задачи.
- **Исправлено (2026-08-29):** `_audit_status()` добавляет вычисляемую строку «Состояние gate/CI», громко показывающую число незакрытых critical-находок (сейчас 1 — [`AUD-007`](#aud-007)); `_technical_coverage()` дописывает «— закрывает результат этапа» к состоянию terminal-outcome задач.

<a id="aud-011"></a>
### AUD-011 — Конкурирующий, осиротевший документ о стандарте frontmatter

- **Severity/Confidence/Evidence state:** medium / high / CONFIRMED
- **Файл:** [`operations/document_frontmatter_standard.md`](../../operations/document_frontmatter_standard.md)
- **Наблюдаемое поведение:** документ объявляет себя «единственным источником истины» для YAML frontmatter, конфликтуя с реально применяемым и enforced [`change_process.md`](../../operations/change_process.md) §8. Ноль входящих ссылок из любого authority-файла или [`procedure_map.md`](../../operations/procedure_map.md). Правило порядка полей (§5) не соблюдается реальными ADR-файлами и не проверяется `metadata.py`/`check.py`. Пропускает живые поля (`delivery_role`, `blocker`, `owner_followups`).
- **Рекомендованное исправление:** слить уникальный контент (правило порядка полей, если оно того стоит) в [`change_process.md`](../../operations/change_process.md) §8, либо пометить `document_state: superseded`; убрать самозаявление «единственный источник истины». Требует явного согласования владельца (AGENTS.md §5 — не менять соглашения об именовании самостоятельно).
- **Как проверить исправление:** остаётся ровно один документ, claiming ownership фронтматтер-контракта; `grep "единственный источник истины"` возвращает только актуальных владельцев этого статуса.
- **Исправлено (2026-08-29):** [`document_frontmatter_standard.md`](../../operations/document_frontmatter_standard.md) помечен `document_state: superseded` с явной ссылкой на [`change_process.md`](../../operations/change_process.md) §8; самозаявление «единственный источник истины» снято. Правило порядка полей перенесено в [`change_process.md`](../../operations/change_process.md) §8.2 как явно не проверяемая автоматически рекомендация.

<a id="aud-012"></a>
### AUD-012 — `delivery_role` не документирован ни в одном frontmatter-контракте

- **Severity/Confidence/Evidence state:** medium / high / CONFIRMED
- **Файл:** [`operations/templates/task_template.md`](../../operations/templates/task_template.md), [`work/tasks/task_014_real_runtime.md`](../tasks/task_014_real_runtime.md)…[`task_017_m02_live_e2e.md`](../tasks/task_017_m02_live_e2e.md), [`change_process.md`](../../operations/change_process.md) §8.1
- **Наблюдаемое поведение:** поле `delivery_role` (`component`/`terminal_outcome`) — структурно важно (различает stub-TASK от закрывающих milestone, [`change_process.md`](../../operations/change_process.md) §7.1), присутствует в 4 из 17 карточек TASK и в 2 генераторах, но отсутствует в обоих документах, претендующих на перечисление TASK-контракта, и не валидируется `check.py` — ни один запуск не проверяет, что terminal-outcome задача из очереди milestone действительно так помечена.
- **Рекомендованное исправление:** добавить `delivery_role` в таблицу полей TASK в [`change_process.md`](../../operations/change_process.md) §8.1; добавить проверку в `check.py`, что каждая задача из терминальной очереди milestone имеет `delivery_role: terminal_outcome`.
- **Как проверить исправление:** новая проверка `check.py` падает на синтетической TASK с несоответствующим/отсутствующим `delivery_role` в терминальной очереди.
- **Исправлено (2026-08-29):** `delivery_role` задокументирован в [`change_process.md`](../../operations/change_process.md) §8.1; добавлена `check_terminal_outcome_delivery_role` в [`check.py`](../../operations/scripts/documents/check.py). Запуск этой проверки нашёл реальное расхождение с прозой [`milestones.md`](../../milestones.md#m02): [`TASK_014`](../tasks/task_014_real_runtime.md)–[`TASK_016`](../tasks/task_016_real_telegram.md) были `delivery_role: component`, хотя milestones.md явно называет все четыре ([`TASK_014`](../tasks/task_014_real_runtime.md)–[`TASK_017`](../tasks/task_017_m02_live_e2e.md)) незаменяемыми — только [`TASK_017`](../tasks/task_017_m02_live_e2e.md) был помечен верно. Исправлено на `terminal_outcome` для всех четырёх.

<a id="aud-013"></a>
### AUD-013 — Блокировка sensitive-action не имеет timeout и recovery-процедуры

- **Severity/Confidence/Evidence state:** medium / high / CONFIRMED
- **Файл:** [`src/owner_control/control.py:86-103`](../../src/owner_control/control.py) (`_exclusive_state`)
- **Наблюдаемое поведение:** `os.mkdir`-блокировка вокруг `authorize_sensitive_action` не имеет timeout, retry или проверки «протухания» (PID/возраст держателя). Нигде в репозитории ([`change_process.md`](../../operations/change_process.md), [`state_machines.md`](../../operations/state_machines.md), `operations/procedures/`) не описано, что именно означает «recovery is required» операционно. Крах процесса между `os.mkdir` и `os.rmdir` (реалистичный сценарий — OOM-kill, принудительная остановка контейнера) навсегда блокирует все последующие чувствительные действия владельца, пока кто-то вручную не удалит `owner_control_actions.lock` — без единой инструкции в репозитории, что это правильное исправление.
- **Воздействие и достижимость:** напрямую достижимо любым крахом процесса во время удержания блокировки; поскольку [`ARC_CMP_002`](../../specifications/architecture_baseline.md#arc_cmp_002) — единая точка авторизации для всех чувствительных действий платформы, это правдоподобный полный self-lockout владельца. Fail-closed здесь — правильный default, но полное отсутствие runbook превращает спроектированное свойство безопасности в незадокументированную ловушку.
- **Рекомендованное исправление:** записывать PID и timestamp держателя блокировки в директорию блокировки; добавить явную (одобренную владельцем, не автоматическую) команду восстановления, которая проверяет, что держатель действительно мёртв, прежде чем очищать блокировку — либо, как минимум, добавить операционный runbook с точным описанием, что проверить и что удалить.
- **Как проверить исправление:** новый тест симулирует крах (создаёт директорию блокировки, не вызывая `authorize_sensitive_action` до завершения) и подтверждает, что документированная процедура восстанавливает нормальную работу без обхода identity/emergency-проверок.
- **Исправлено (2026-08-29):** `_exclusive_state()` пишет `holder.json` (pid, `acquired_at` UTC) в директорию блокировки при захвате и удаляет его при снятии. Добавлена `recover_stale_sensitive_action_lock()` — не вызывается автоматически, требует точную confirmation-фразу и отказывает, если записанный PID держателя ещё жив (`os.kill(pid, 0)`); тонкий CLI [`recover_lock.py`](../../operations/scripts/owner_control/recover_lock.py) и runbook [`recover_stale_sensitive_action_lock.md`](../../operations/procedures/recover_stale_sensitive_action_lock.md) с инструкцией, как подтвердить смерть держателя вне процесса восстановления.

<a id="aud-014"></a>
### AUD-014 — Шесть операционных документов недостижимы из карты процедур

- **Severity/Confidence/Evidence state:** medium / high / CONFIRMED
- **Файл:** [`operations/adr_lifecycle.md`](../../operations/adr_lifecycle.md), [`state_machines.md`](../../operations/state_machines.md), [`threat_review_triggers.md`](../../operations/threat_review_triggers.md), [`license_policy.md`](../../operations/license_policy.md), [`procedures/file_update_dependencies.md`](../../operations/procedures/file_update_dependencies.md), [`examples/sample_task_lifecycle.md`](../../operations/examples/sample_task_lifecycle.md)
- **Наблюдаемое поведение:** [`AGENTS.md`](../../AGENTS.md) называет [`procedure_map.md`](../../operations/procedure_map.md) «детальным деревом решений для каждой ситуации», но этот файл ведёт лишь к 3 из ~9+ реальных процедурных документов. Ни один из перечисленных 6 файлов не имеет входящей ссылки ни из одного authority-файла, [`procedure_map.md`](../../operations/procedure_map.md) или друг из друга. Содержимое всех шести прочитано полностью и признано реальным, не дублирующим — дефект чисто навигационный, не дублирование и не мёртвый код.
- **Рекомендованное исправление:** добавить по одной строке в таблицу [`procedure_map.md`](../../operations/procedure_map.md) (или в список утилит [`AGENTS.md`](../../AGENTS.md) §6) на каждый из 6 файлов, называя ситуацию, которую он описывает.
- **Как проверить исправление:** `grep -c "adr_lifecycle\|state_machines\|threat_review_triggers\|license_policy\|file_update_dependencies\|sample_task_lifecycle" operations/procedure_map.md` возвращает ≥6.
- **Исправлено (2026-08-29):** все 6 файлов добавлены в таблицу §2 [`procedure_map.md`](../../operations/procedure_map.md) с назначением, входными условиями и результатом (по образцу существующих строк).

<a id="aud-015"></a>
### AUD-015 — Канонический traceability-checker глотает исключения из собственных коллекторов

- **Severity/Confidence/Evidence state:** medium / medium / SUSPECTED
- **Файл:** [`operations/scripts/documents/check.py:269-279, 856-872`](../../operations/scripts/documents/check.py) (`_known_reference_ids`, `check_test_specs`)
- **Наблюдаемое поведение:** оба места откатываются к пустому множеству/словарю при ЛЮБОМ исключении из `collect_traceable_elements`/`collect_milestones`/`load_quality_registry`, вместо того чтобы явно провалить проверку. На текущем SHA `check.py --all --json` проходит чисто (22/22) — ветка не была замечена сработавшей вживую, поэтому статус понижен до `SUSPECTED`, а не `CONFIRMED`.
- **Воздействие:** если будущее изменение документа/реестра внесёт реальный баг парсера в эти коллекторы, checker молча недосчитает известные ID (более безопасное направление ошибки — больше ложных «unknown reference», а не меньше), но это увеличит стоимость отладки и риск «исправления не того».
- **Рекомендованное исправление:** сузить типы перехватываемых исключений до реально ожидаемых, и/или логировать проглоченное исключение в `runtime/check_summary.json`, даже если общая проверка всё равно проходит.
- **Как проверить исправление:** новый тест подаёт заведомо некорректный вход в `collect_traceable_elements`/`collect_milestones`, достижимый из `check_test_specs`/`_known_reference_ids`, и подтверждает, что сбой становится видимым, а не тихо поглощается.
- **Исправлено (2026-08-29):** оба места сужены до `except (ValueError, OSError)` с логированием проглоченного исключения в stderr; любое другое исключение (`AttributeError`, `TypeError` и т.п.) теперь распространяется. Новые тесты подтверждают оба поведения (fallback на ожидаемых ошибках, propagation на неожиданных).

<a id="aud-016"></a>
### AUD-016 — Timeout-путь TelegramChannel.receive() недостижим и не тестирован

- **Severity/Confidence/Evidence state:** low / high / CONFIRMED
- **Файл:** [`src/channels/telegram.py:65-68`](../../src/channels/telegram.py)
- **Наблюдаемое поведение:** единственный документированный error-path канала (`Channel.receive()` → `ChannelError` при 30-секундном timeout) не вызывается ни одним текущим кодом (`Orchestrator` вызывает только `.send()`) и не покрыт ни одним из 16 тестов `test_channels.py`. Измеренное покрытие подтверждает: строки 67-68 явно отмечены как missing. Это ровно тот контракт, который понадобится [`TASK_016`](../tasks/task_016_real_telegram.md) (реальный Telegram Bot API).
- **Рекомендованное исправление:** добавить тест, сокращающий timeout (параметр или monkey-patch `asyncio.wait_for`), подтверждающий `ChannelError` при пустой очереди без ожидания реальных 30 секунд.
- **Как проверить исправление:** новый тест проходит; `coverage report` показывает `telegram.py` на 100% (или явно документирует остаток `# pragma: no cover` с причиной).
- **Исправлено (2026-08-29):** новый тест подменяет `asyncio.wait_for` на мгновенный timeout (без реального ожидания 30с) и подтверждает точное сообщение `ChannelError`. Покрытие подтверждает: строки таймаута больше не missing.

<a id="aud-017"></a>
### AUD-017 — Хрупкость теста регенерации к версии Python + xpass не выделяется отдельно

- **Severity/Confidence/Evidence state:** low / high / CONFIRMED
- **Файл:** [`operations/tests/test_quality_integration.py:119-148`](../../operations/tests/test_quality_integration.py); [`pre_commit_regenerate_dashboards.sh:16-26`](../../operations/hooks/pre_commit_regenerate_dashboards.sh); [`run_unittests.py:24-30`](../../operations/scripts/quality/run_unittests.py)
- **Наблюдаемое поведение:** (а) `find_python()` в хуке предпочитает новейший доступный интерпретатор (`python3.14`→…→`python3.12`) через `command -v`, который резолвится по реальному PATH, а не только по тестовому шиму — на любой машине с уже установленным `python3.13`/`3.14` тест ложно падает на несвязанном assertion; (б) "no skips" gate в `run_unittests.py` проверяет только `result.skipped`, не выделяя `result.unexpectedSuccesses` отдельным сообщением — пока безопасно (`wasSuccessful()` всё равно поймает xpass), но нет ни одного `expectedFailure`-теста, чтобы это проверить, и сообщение об ошибке было бы неотличимо от обычного провала.
- **Рекомендованное исправление:** (а) шимить все имена интерпретаторов, которые пробует цикл, либо передавать явный override; (б) отдельно проверять и называть `result.unexpectedSuccesses`.
- **Как проверить исправление:** тест (а) проходит и на машине с несколькими версиями Python; синтетический `expectedFailure`-тест для (б) даёт отдельное, узнаваемое сообщение.
- **Исправлено (2026-08-29):** (а) тест теперь шимит все 5 имён, которые пробует `find_python()` (не только `python3.12`) — воспроизведено и подтверждено на этой машине (уже установлен `python3.13`, который раньше побеждал шим); (б) `run_unittests.py` даёт `unexpectedSuccesses` отдельный exit code 3 и печатает список; новый синтетический `expectedFailure`-тест подтверждает оба поведения.

<a id="aud-018"></a>
### AUD-018 — Мелкая гигиена evidence-документов

- **Severity/Confidence/Evidence state:** low / high / CONFIRMED
- **Файл:** [`work/tests/test_007.md:59,72,132`](../tests/test_007.md); [`operations/quality_registry.json`](../../operations/quality_registry.json); `.gitignore`
- **Наблюдаемое поведение:** [`TEST_007`](../tests/test_007.md) в разных разделах называет разное число тестов для одного файла (§4: 16, §5/§10: 8) — реальное число (посчитано напрямую) — 16; [`quality_registry.json`](../../operations/quality_registry.json) перечисляет `m02_security_tests`/`m02_e2e_tests`/`m02_infrastructure_tests` в `evidence_catalog`, но не в `m02_development.required_evidence`, без пояснения, преднамеренно ли это фазирование; `.gitignore` всё ещё описывает конвенцию «versioned generated markdown stays in git» для директории `generated/`, полностью удалённой коммитом `dc4ee8b`.
- **Рекомендованное исправление:** привести [`TEST_007`](../tests/test_007.md) к единому числу (16); владелец/мейнтейнер поясняет намерение по `required_evidence`; убрать устаревший комментарий и связанные с ним ignore-паттерны из `.gitignore` при следующем изменении файла.
- **Как проверить исправление:** все три раздела [`TEST_007`](../tests/test_007.md) согласованы; `.gitignore` не упоминает `generated/`, если директория не появится вновь как tracked.
- **Исправлено (2026-08-29):** [`TEST_007`](../tests/test_007.md) приведён к единому числу — 17 (16 исходных + 1 новый тест из [`AUD-016`](#aud-016)); [`quality_registry.json`](../../operations/quality_registry.json) получил пояснение фазирования в `note`; устаревший блок `generated/` удалён из `.gitignore`.

<a id="aud-019"></a>
### AUD-019 — Пути обработки повреждённых данных в SQLite-хранилище задач не тестируются

- **Severity/Confidence/Evidence state:** low / medium / SUSPECTED
- **Файл:** [`src/task_state/sqlite_store.py:81-82,84,137-138`](../../src/task_state/sqlite_store.py) (`_decode`, `load_task`)
- **Наблюдаемое поведение:** измеренное покрытие подтверждает, что эти строки (обработка `JSONDecodeError`, не-dict значений, неизвестного `state`) никогда не исполняются; `test_persistent_task_state.py` содержит только 3 теста, ни один не пишет напрямую повреждённый `metadata_json`/`checkpoint_data_json` в SQLite-файл. Контрастирует с гораздо более строгой проверкой того же класса риска (JSON-в-хранилище, повреждение) в `owner_control`.
- **Рекомендованное исправление:** добавить тесты по образцу `test_owner_control.py` — напрямую записать невалидный JSON/не-dict/неизвестный `state` в строку SQLite и подтвердить, что `TaskLifecycleError` поднимается.
- **Как проверить исправление:** новые тесты проходят; строки из отчёта покрытия перестают быть missing.
- **Исправлено (2026-08-29):** 5 новых тестов пишут напрямую в SQLite (невалидный JSON, не-dict JSON, неизвестный `state` для `task_messages`; невалидный и не-dict `checkpoint_data_json` для `task_states`) и подтверждают `TaskLifecycleError`.

<a id="aud-020"></a>
### AUD-020 — Фреймворк аудита не проверяет наличие eval/regression-набора для качества выхода модели

- **Severity/Confidence/Evidence state:** medium / high / CONFIRMED
- **Файл:** [`repository_audit_system_prompt.md`](repository_audit_system_prompt.md) (весь документ, включая §7.5 «Тестирование»); репозиторий целиком
- **Ожидаемый контракт:** для продукта, чья основная ценность — поведение LLM-агента, полный аудит качества (пилар 7.5) должен включать проверку наличия и актуальности eval-набора (golden-задачи, регрессия ответов, LLM-judge или эквивалент), отдельно от обычных unit/coverage-тестов.
- **Наблюдаемое поведение:** исчерпывающий поиск (`grep -in "eval"`) по [`repository_audit_system_prompt.md`](repository_audit_system_prompt.md) целиком не дал ни одного совпадения — ни в §6 (канонические проверки), ни в §7.5 (тестирование), ни где-либо ещё. Поиск по всему репозиторию терминов eval/evals/evaluation-suite/prompt-regression/llm-judge также не дал ни одного реального совпадения (только ложные срабатывания по подстроке, например `evaluate_coverage`). На проверенном SHA это не является дефектом реализации: `ModelGateway`/`RuntimePort` остаются эхо-заглушками ([`TASK_015`](../tasks/task_015_real_model_provider.md) не выполнена), поэтому оценивать пока нечего — но сам факт, что фреймворк аудита прошёл 7 столпов и не поднял этот вопрос, означает, что пробел останется незамеченным и после появления реального провайдера, если фреймворк не обновить заранее.
- **Воздействие и достижимость:** сегодня — нулевое (нет модели, нечего оценивать). Как только [`TASK_015`](../tasks/task_015_real_model_provider.md) заменит эхо-заглушку реальным провайдером, у репозитория не будет ни одного канонического механизма отследить регрессию качества ответов между изменениями промптов/логики — только структурные unit-тесты, которые эту категорию рисков в принципе не покрывают.
- **Как воспроизвести:** `grep -in "eval" work/audit/repository_audit_system_prompt.md` (пусто); `grep -rin "evaluation-suite\|llm-judge\|prompt-regression" --include=*.py --include=*.md .` (пусто, кроме подстрочных ложных срабатываний).
- **Рекомендованное исправление:** владелец решает — либо (а) добавить в §7.5 фреймворка явный пункт «наличие и актуальность eval/regression-набора для LLM-выхода, если репозиторий содержит реальный model provider», либо (б) явно задокументировать это как осознанно отложенное до [`TASK_015`](../tasks/task_015_real_model_provider.md) решение (не пробел, а фаза). Само внедрение eval-набора — отдельная задача, вне рамок текущего аудита.
- **Как проверить исправление:** обновлённый [`repository_audit_system_prompt.md`](repository_audit_system_prompt.md) §7.5 явно упоминает eval/regression-проверку (или явное фазирование до [`TASK_015`](../tasks/task_015_real_model_provider.md) задокументировано в этом же разделе).
- **Исправление (2026-08-29):** [`repository_audit_system_prompt.md`](repository_audit_system_prompt.md) §7.5 требует проверки eval/regression-набора; добавлены пять golden-задач и исполняемый harness. Текущий `stub` profile доказывает только request/response plumbing и не является model-quality evidence.
- **Уточнение (2026-08-30):** [`run_eval_suite.py`](../../operations/scripts/eval/run_eval_suite.py) получил явный выбор profile. Любой non-stub profile должен быть зарегистрирован [`TASK_015`](../tasks/task_015_real_model_provider.md) и запускаться с полным Git SHA; stub-specific expectations заменяются отдельным реальным набором. Канонический entrypoint проверенно падает на деградировавшем non-stub provider.
- **Критерий закрытия:** зелёный `Project check` на точном SHA подтверждает `python3 -m operations.scripts.eval.run_eval_suite` и связанные unit-тесты; переход в `resolved` — как и для остальных findings этого запуска, недостижим, пока не разрешён [`AUD-007`](#aud-007).

<a id="aud-021"></a>
### AUD-021 — Proposed ADR активного этапа не имели машинного владельца решения

- **Severity/Confidence/Evidence state:** high / high / CONFIRMED
- **Файл:** [`milestones.md`](../../milestones.md), [`TASK_013`](../tasks/task_013_inf_008.md)–[`TASK_015`](../tasks/task_015_real_model_provider.md), [`check.py`](../../operations/scripts/documents/check.py), [`repository_audit_system_prompt.md`](repository_audit_system_prompt.md)
- **Ожидаемый контракт:** каждый `proposed` ADR активного/заблокированного milestone имеет ровно одну незавершённую TASK, которая собирает сравнение/evidence и получает решение владельца. TASK и ADR относятся к одному milestone; завершить TASK при ADR в `proposed` нельзя.
- **Наблюдаемое поведение:** [`ADR_005`](../../adr/adr_005_first_model_provider_selection.md)–[`ADR_009`](../../adr/adr_009_secret_management_strategy.md) имели только `traces_to` и текстовые упоминания. [`ADR_006`](../../adr/adr_006_agent_environment_framework.md) был описан в [`TASK_014`](../tasks/task_014_real_runtime.md), но parser/checker не знал отношения принятия решения, поэтому не существовало машинного ребра и отрицательной проверки. [`ADR_007`](../../adr/adr_007_cloud_provider_selection.md) и [`ADR_009`](../../adr/adr_009_secret_management_strategy.md) также не имели структурированного owner TASK. [`ADR_008`](../../adr/adr_008_data_storage_schema.md) относится только к planned [`m04`](../../milestones.md#m04).
- **Почему аудит пропустил:** checker обходил граф в одну сторону и проверял лишь непустой `ADR.traces_to`; relation model не содержала `decides`; строка «ADR этого этапа» создавала ложное ощущение покрытия; защита от преждевременных TASK для будущих требований не имела исключения для ADR активного milestone; отрицательного fixture не было.
- **Риск:** TASK или milestone можно было завершить, оставив решение `proposed`, без владельца, evidence и явного решения владельца; структура при этом оставалась «зелёной».
- **Исправление:** `TASK_013.decides = [ADR_007, ADR_009]`, `TASK_014.decides = [ADR_006]`, `TASK_015.decides = [ADR_005]`; [`ADR_008`](../../adr/adr_008_data_storage_schema.md) обязан получить TASK при декомпозиции [`m04`](../../milestones.md#m04) до старта. Обновлены lifecycle, change process, шаблоны и audit prompt. Добавлен исполняемый checker и negative tests.
- **Критерий закрытия:** новый check `adr_decision_tasks`, unit tests, полный project gate и CI успешны на одном SHA; traceability matrix показывает все четыре связи активного [`m02`](../../milestones.md#m02).
- **Дополнено (2026-08-30):** правило распространено на planned milestones; [`ADR_008`](../../adr/adr_008_data_storage_schema.md) назначен [`TASK_019`](../tasks/task_019_m04_data_storage.md), а negative fixture запрещает proposed ADR будущего этапа без TASK.

<a id="aud-022"></a>
### AUD-022 — Канонический gate красный, а owner-facing статус и описание CI устарели

- **Severity/Confidence/Evidence state:** high / high / CONFIRMED
- **Файл:** [`project_status.md`](../../project_status.md), [`audit_register.md`](#3-реестр), [`AGENTS.md`](../../AGENTS.md), [`project_check.yml`](../../.github/workflows/project_check.yml)
- **Наблюдение:** documentation audit нашёл 10 некликабельных ADR/TASK/milestone references в этом реестре. Генератор добавляет [`ADR_009`](../../adr/adr_009_secret_management_strategy.md) в текущие шаги и меняет число findings с 20 на 21. [`AGENTS.md`](../../AGENTS.md) обещает push-проверку каждой ветки, а workflow запускает `push` только на `main`. После установки pinned development tools полный gate дополнительно обнаружил formatter drift в семи Python-файлах и несовместимость относительного `--output`, который сам `run_suite.py` передаёт health generator. После синхронизации с PR #76 Mypy также обнаружил инвариантный `list` в новом section-contract test.
- **Риск:** основной экран владельца скрывает решение и одну high-находку; основной branch не удовлетворяет собственному gate.
- **Исправление:** исправить ссылки, перегенерировать статус и согласовать описание triggers.
- **Критерий закрытия:** полный suite и pre-commit зелёные; повторная генерация не создаёт diff.
- **Исправлено (2026-08-30):** ссылки приведены к политике, [`project_status.md`](../../project_status.md) перегенерирован, описание triggers в [`AGENTS.md`](../../AGENTS.md) согласовано с workflow, formatter drift устранён каноническим Ruff formatter. Health generator нормализует относительные runtime paths относительно корня репозитория; regression test воспроизводит точную CLI-команду canonical suite. Section-contract test принимает ковариантный `Sequence`, поэтому Mypy сохраняет нулевой baseline. Ожидается серверная верификация.

<a id="aud-023"></a>
### AUD-023 — Ignore-правила скрывают source-файлы и допускают секреты в Docker image

- **Severity/Confidence/Evidence state:** high / high / CONFIRMED
- **Файл:** [`.gitignore`](../../.gitignore), [`.dockerignore`](../../.dockerignore), [`dockerfile`](../../dockerfile)
- **Наблюдение:** unanchored `secrets/` игнорирует `src/secrets/`; текущие модули видны только потому, что tracked. Docker context не исключает `.env*`, ключи и secret-пути, а image копирует `src/`.
- **Риск:** новый source-модуль может исчезнуть из Git, а локальный credential — попасть в image.
- **Исправление:** привязать data-secret patterns к корню, разрешить source package, зеркально исключить секретные patterns в `.dockerignore` и добавить sentinel test.
- **Критерий закрытия:** новый source-файл виден Git; sentinel отсутствует в build context, слоях и image.
- **Исправлено (2026-08-30):** root secret directories закреплены в [`.gitignore`](../../.gitignore), `src/secrets` остаётся видимым Git, чувствительные patterns добавлены в [`.dockerignore`](../../.dockerignore), negative policy tests проходят. Фактическая проверка слоёв image остаётся недоступна без Docker.

<a id="aud-024"></a>
### AUD-024 — ADR-трассировка структурно зелёная, но семантически неполная

- **Severity/Confidence/Evidence state:** high / high / CONFIRMED
- **Файл:** [`ADR_003`](../../adr/adr_003_model_provider_interface.md), [`ADR_004`](../../adr/adr_004_task_events_and_logging.md), [`ADR_006`](../../adr/adr_006_agent_environment_framework.md), [`ADR_007`](../../adr/adr_007_cloud_provider_selection.md), [`ADR_008`](../../adr/adr_008_data_storage_schema.md)
- **Наблюдение:** для событий [`ADR_004`](../../adr/adr_004_task_events_and_logging.md) нет `runtime_task_id` и тестов; [`TASK_014`](../tasks/task_014_real_runtime.md) не сравнивает требуемый [`ADR_006`](../../adr/adr_006_agent_environment_framework.md) LangGraph; [`TASK_013`](../tasks/task_013_inf_008.md) не фиксирует оба прототипа [`ADR_007`](../../adr/adr_007_cloud_provider_selection.md); [`ADR_008`](../../adr/adr_008_data_storage_schema.md) не имеет TASK-владельца; accepted contract [`ADR_003`](../../adr/adr_003_model_provider_interface.md) называется иначе, чем код.
- **Причина пропуска предыдущим аудитом:** автоматическая проверка подтверждала только структурное ребро `TASK.decides`, общий milestone и состояния, но не сопоставляла содержание ADR с TASK, кодом и тестами. Planned-milestone exception исключал [`ADR_008`](../../adr/adr_008_data_storage_schema.md) из обязательной проверки, а ручной обратный проход не был завершён как отдельная матрица candidate sets, verification checklist и контрактных имён.
- **Риск:** TASK можно завершить без verification checklist assigned ADR, а accepted ADR может заявлять отсутствующее поведение.
- **Исправление:** получить решения владельца и синхронизировать ADR, TASK, код и поведенческое evidence; назначить владельцев всей незавершённой ADR-работы.
- **Критерий закрытия:** candidate sets, contract names и evidence mapping совпадают; у каждого proposed ADR ровно одна незавершённая TASK.
- **Частично исправлено (2026-08-30):** каноническое имя `ModelGateway` согласовано; [`TASK_014`](../tasks/task_014_real_runtime.md) сравнивает LangGraph, Hermes Agent и native loop; [`TASK_013`](../tasks/task_013_inf_008.md) сравнивает Hetzner и DigitalOcean; [`ADR_008`](../../adr/adr_008_data_storage_schema.md) назначен [`TASK_019`](../tasks/task_019_m04_data_storage.md). Finding остаётся `open`, пока [`TASK_018`](../tasks/task_018_runtime_task_events.md) не реализует и не проверит события [`ADR_004`](../../adr/adr_004_task_events_and_logging.md).

<a id="aud-025"></a>
### AUD-025 — ADR lifecycle противоречит сам себе и каноническому change process

- **Severity/Confidence/Evidence state:** medium / high / CONFIRMED
- **Файл:** [`adr_lifecycle.md`](../../operations/adr_lifecycle.md), [`change_process.md`](../../operations/change_process.md)
- **Наблюдение:** lifecycle одновременно требует сравнить альтернативы до создания ADR и поручает сравнение TASK-владельцу после создания. Подробная процедура требует решения владельца, таблица переходов считает достаточным PR approval. Planned-milestone exception оставляет proposed ADR без TASK.
- **Риск:** ADR можно создать слишком поздно либо принять без решения владельца.
- **Исправление:** оставить одно правило создания/сравнения/acceptance, удалить PR shortcut и исключение для ADR без TASK.
- **Критерий закрытия:** negative fixtures блокируют acceptance без owner decision и proposed ADR без единственного незавершённого owner TASK.
- **Исправлено (2026-08-30):** lifecycle и change process разделяют создание proposed ADR, сравнение TASK, явное решение владельца и доставку через PR; переход по одному PR approval удалён. Checker, negative tests и защищённые [`task_template.md`](../../operations/templates/task_template.md) и [`milestone_template.md`](../../operations/templates/milestone_template.md) требуют единственного незавершённого owner TASK для каждого proposed ADR любого milestone. Изменение шаблонов выполнено по явному разрешению владельца в отдельной ветке; finding ожидает полный gate и серверную проверку.

<a id="aud-026"></a>
### AUD-026 — Служебные изменения ретроактивно включены в продуктовую TASK

- **Severity/Confidence/Evidence state:** medium / high / CONFIRMED
- **Файл:** [`TASK_013`](../tasks/task_013_inf_008.md), [`AGENTS.md`](../../AGENTS.md)
- **Наблюдение:** карточка прямо говорит, что [`milestones.md`](../../milestones.md) и этот audit register добавлены в `allowed_paths`, потому что это была единственная активная TASK, хотя изменения не относятся к её компоненту.
- **Риск:** `allowed_paths` перестаёт быть честной границей поставки и превращается в ретроактивное разрешение.
- **Исправление:** убрать несвязанные paths/пояснение и применять service-change route; добавить проверку несвязанных расширений scope.
- **Критерий закрытия:** scope fixture отделяет service change от product TASK и отклоняет несвязанное расширение карточки.
- **Исправлено (2026-08-30):** служебные пути и объяснение удалены из [`TASK_013`](../tasks/task_013_inf_008.md); `paths_validation.py` отклоняет governance/audit paths в `allowed_paths` любой незавершённой product TASK и сохраняет исторические completed-карточки.

<a id="aud-027"></a>
### AUD-027 — Eval CLI всегда выбирает stub, несмотря на обещание real-provider evidence

- **Severity/Confidence/Evidence state:** medium / high / CONFIRMED
- **Файл:** [`run_eval_suite.py`](../../operations/scripts/eval/run_eval_suite.py), [`AUD-020`](#aud-020)
- **Наблюдение:** канонический `main()` всегда вызывает `_default_gateway()` и создаёт `StubModelGateway`. Карточка [`AUD-020`](#aud-020) обещает работу с реальным provider после [`TASK_015`](../tasks/task_015_real_model_provider.md) без изменения runner, но factory/configuration path отсутствует.
- **Риск:** eval останется зелёным на echo-ответах после подключения реальной модели.
- **Исправление:** исправить обещание; в [`TASK_015`](../tasks/task_015_real_model_provider.md) добавить явный provider selection/injection и разделить stub/real profiles.
- **Критерий закрытия:** canonical entrypoint с деградировавшим non-stub provider возвращает 1 и фиксирует provider/profile и точный SHA.
- **Исправлено (2026-08-30):** CLI поддерживает явные profiles, non-stub требует полный SHA, неизвестный profile отклоняется, а injected degraded profile возвращает exit code 1. Текущий default остаётся честно обозначенным `stub`.

## 5. Правило обновления

После зелёного `Project check` на точном SHA записи исправленных findings переводятся в `resolved` отдельным служебным PR. Для `accepted_risk` обязательно сохраняются явное решение владельца, ответственный, срок пересмотра и компенсирующий контроль. Удаление строк запрещено: закрытая finding остаётся историей реестра, а не удаляется.
