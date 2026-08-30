---
id: audit_baseline_2026_08_30
type: audit_baseline
document_state: current
version: 1.0
updated: 2026-08-30
depends_on: []
---

# Аудит репозитория — 2026-08-30

Это точечный отчёт одного полного аудита. Разделы 3 и 4 содержат только новые находки этого запуска (`AUD-022`…`AUD-027`). Текущее состояние всех находок ведётся в [`audit_register.md`](audit_register.md).

## 1. Проверенная редакция

- Git SHA: `4ae3c992daa07a8989be642b8aee65273f619500`
- Ветка или тег: `main`
- Применённый prompt: [`repository_audit_system_prompt.md`](repository_audit_system_prompt.md) v3.7
- Режим: `FULL_REPOSITORY`
- Интервал: `2026-08-29T22:22:34Z` — `2026-08-30T06:14:32Z`
- Среда: Linux 6.18.35, x86_64, Python 3.12.13; точный snapshot из GitHub tree, 286 из 286 Git blobs проверены по SHA.

## 2. Итог

**Readiness: NOT READY.**

**Главный подтверждённый результат:** архитектурные границы реализации в целом ясны, 152 из 152 продуктовых тестов прошли, lock-файл согласован с девятью прямыми зависимостями и содержит SHA-256 для всех 54 пакетов. Большинство предложенных ADR теперь имеют машинную связь с незавершённой TASK.

**Главный риск:** существующая критическая находка [`AUD-007`](audit_register.md#aud-007) остаётся открытой — GitHub Actions для точного SHA завершился без назначенного runner и без исполнявшихся шагов. Одновременно `main` не проходит собственный локальный gate: найдены 10 ошибок ссылок и drift производного [`project_status.md`](../../project_status.md).

**ADR и трассировка:** [`ADR_006`](../../adr/adr_006_agent_environment_framework.md) не принят и формально закреплён за [`TASK_014`](../tasks/task_014_real_runtime.md), но набор сравниваемых вариантов в этих документах различается. [`ADR_008`](../../adr/adr_008_data_storage_schema.md) не имеет TASK-владельца: действующая процедура разрешает отсрочку для будущего planned milestone, что противоречит прямому правилу владельца о TASK для каждого непринятого ADR.

**Ограничения:** Docker, полный pinned static/security toolchain, vulnerability database, SBOM/license inventory и full-history secret scan были недоступны. Эти проверки имеют состояние `UNAVAILABLE`, а не успешный результат.

**Семь столпов, кратко:**

- контракт и документация — `CONFIRMED`: структура сильная, но gate красный и нормативные документы расходятся;
- реализация против спецификации — `CONFIRMED/PARTIAL`: продуктовые тесты зелёные, но контракт событий [`ADR_004`](../../adr/adr_004_task_events_and_logging.md) не реализован;
- качество кода — `PARTIAL`: compile/AST проверки прошли, полный pinned toolchain недоступен;
- гигиена и безопасность — `CONFIRMED/PARTIAL`: fail-closed controls присутствуют, но ignore/build-context создаёт путь попадания локального секрета в image;
- тестирование — `PARTIAL`: 529 тестов обнаружено, одна реальная ошибка и четыре запрещённых skip;
- трассируемость — `CONFIRMED/PARTIAL`: ID-граф в основном проходит, семантическое соответствие ADR/TASK не обеспечено;
- supply chain — `PARTIAL`: зависимости и hashes согласованы, vulnerability/SBOM/license evidence недоступно.

## 3. Реестр

| ID | Severity | State | First seen | Review date | Owner | Evidence | Resolution |
|---|---|---|---|---|---|---|---|
| AUD-022 | high | open | 2026-08-30 | 2026-09-06 | repository_owner | [`project_status.md`](../../project_status.md), [`audit_register.md`](audit_register.md), [`AGENTS.md`](../../AGENTS.md), [`project_check.yml`](../../.github/workflows/project_check.yml) | Канонический gate красный: 10 ошибок ссылок, drift owner-status и расхождение описания CI triggers. |
| AUD-023 | high | open | 2026-08-30 | 2026-09-06 | repository_owner | [`.gitignore`](../../.gitignore), [`.dockerignore`](../../.dockerignore), [`dockerfile`](../../dockerfile) | Unanchored `secrets/` скрывает новый код `src/secrets`, а Docker context не исключает локальные `.env`/key/secret-файлы. |
| AUD-024 | high | open | 2026-08-30 | 2026-09-06 | repository_owner | [`ADR_003`](../../adr/adr_003_model_provider_interface.md), [`ADR_004`](../../adr/adr_004_task_events_and_logging.md), [`ADR_006`](../../adr/adr_006_agent_environment_framework.md), [`ADR_007`](../../adr/adr_007_cloud_provider_selection.md), [`ADR_008`](../../adr/adr_008_data_storage_schema.md) | Структурно зелёная ADR-матрица семантически не соответствует TASK, коду и прямому правилу владельца. |
| AUD-025 | medium | open | 2026-08-30 | 2026-09-13 | repository_owner | [`adr_lifecycle.md`](../../operations/adr_lifecycle.md), [`change_process.md`](../../operations/change_process.md) | Условия создания и принятия ADR противоречат друг другу; PR approval ошибочно выглядит достаточным для acceptance. |
| AUD-026 | medium | open | 2026-08-30 | 2026-09-13 | repository_owner | [`TASK_013`](../tasks/task_013_inf_008.md), [`AGENTS.md`](../../AGENTS.md) | В product TASK ретроактивно включены несвязанные governance/audit paths, что ослабляет смысл `allowed_paths`. |
| AUD-027 | medium | open | 2026-08-30 | 2026-09-13 | repository_owner | [`run_eval_suite.py`](../../operations/scripts/eval/run_eval_suite.py), [`audit_register.md`](audit_register.md#aud-020) | Реестр обещает real-provider eval без изменения runner, но канонический CLI всегда создаёт StubModelGateway. |

## 4. Карточки findings

<a id="aud-022"></a>
### AUD-022 — Канонический gate красный, а owner-facing статус и описание CI устарели

- **Severity/Confidence/Evidence state:** high / high / CONFIRMED
- **Baseline:** pre-existing на проверенном SHA.
- **Ожидаемое состояние:** `run_suite.py full` завершается успешно; повторная генерация не меняет tracked-файлы; [`AGENTS.md`](../../AGENTS.md) точно описывает triggers workflow.
- **Наблюдение:** documentation audit нашёл 10 голых ссылок на ADR/TASK/milestone в [`audit_register.md`](audit_register.md). Генератор добавляет [`ADR_009`](../../adr/adr_009_secret_management_strategy.md) в шаги текущей задачи и меняет счётчики аудита с 20 на 21. Тест `test_project_status_is_detailed_without_artificial_percentages` падает. [`AGENTS.md`](../../AGENTS.md) говорит о push-проверке каждой ветки, тогда как workflow запускает `push` только для `main`.
- **Риск:** основной экран владельца скрывает решение и одну high-находку; `main` не удовлетворяет собственному merge gate.
- **Исправление:** починить ссылки, перегенерировать статус и согласовать текст CI с фактическими triggers.
- **Проверка:** полный suite и pre-commit проходят; повторная генерация не создаёт diff.

<a id="aud-023"></a>
### AUD-023 — Ignore-правила скрывают source-файлы и допускают локальные секреты в Docker image

- **Severity/Confidence/Evidence state:** high / high / CONFIRMED
- **Baseline:** pre-existing на проверенном SHA.
- **Ожидаемое состояние:** новые source-модули видны Git; всё, что игнорируется как секрет, исключено из Docker build context.
- **Наблюдение:** правило `secrets/` в [`.gitignore`](../../.gitignore) не привязано к корню и поэтому игнорирует `src/secrets/`. Текущие файлы видны только потому, что уже tracked; новый модуль будет скрыт. [`.dockerignore`](../../.dockerignore) не исключает `.env*`, ключи и secret-пути, а [`dockerfile`](../../dockerfile) выполняет `COPY src ./src`.
- **Риск:** локальная реализация может отличаться от CI, а gitignored credential внутри `src/` может попасть в image.
- **Исправление:** привязать data-secret patterns к нужным корневым путям, явно разрешить source package, зеркально исключить секретные patterns из Docker context и добавить negative test с sentinel.
- **Проверка:** новый source-файл отображается в `git status`; sentinel отсутствует в build context, слоях и image.

<a id="aud-024"></a>
### AUD-024 — Структурная ADR-трассировка не подтверждает соответствие решений содержанию TASK и реализации

- **Severity/Confidence/Evidence state:** high / high / CONFIRMED
- **Baseline:** pre-existing на проверенном SHA.
- **Наблюдение:** принятый [`ADR_004`](../../adr/adr_004_task_events_and_logging.md) требует коррелированных событий `runtime_task_id`, но такой контракт отсутствует в коде и тестах. [`ADR_006`](../../adr/adr_006_agent_environment_framework.md) требует LangGraph-прототип, а [`TASK_014`](../tasks/task_014_real_runtime.md) сравнивает Hermes Agent, Claude Agent SDK и native loop. [`ADR_007`](../../adr/adr_007_cloud_provider_selection.md) требует два сценария и два воспроизводимых прототипа, чего явно нет в [`TASK_013`](../tasks/task_013_inf_008.md). [`ADR_008`](../../adr/adr_008_data_storage_schema.md) не имеет TASK-владельца. [`ADR_003`](../../adr/adr_003_model_provider_interface.md) называет контракт `ModelProvider`, код — `ModelGateway`.
- **Почему это пропустил предыдущий аудит:** зелёный structural checker проверял только наличие ребра `TASK.decides`, общий milestone и допустимые состояния; он не сопоставлял candidate sets, verification checklist и имена контрактов с TASK, кодом и тестами. Кроме того, checker и prompt разрешали не назначать TASK для proposed ADR planned milestone, поэтому [`ADR_008`](../../adr/adr_008_data_storage_schema.md) выпадал из обязательного покрытия. Предыдущий запуск не довёл предусмотренный ручной обратный проход по содержанию каждого ADR до такой матрицы и ошибочно принял зелёную структурную проверку за достаточное evidence.
- **Риск:** TASK можно завершить, не выполнив verification checklist назначенного ADR; accepted ADR может заявлять отсутствующее поведение.
- **Исправление:** сначала получить решения владельца по спорным вариантам; затем синхронизировать ADR/TASK/контракты, назначить владельца [`ADR_008`](../../adr/adr_008_data_storage_schema.md) и работу по событиям [`ADR_004`](../../adr/adr_004_task_events_and_logging.md).
- **Проверка:** у каждого verification-пункта ADR есть ровно один TASK owner и поведенческое evidence; candidate sets и имена контрактов совпадают.

<a id="aud-025"></a>
### AUD-025 — ADR lifecycle содержит противоречивые правила создания и принятия

- **Severity/Confidence/Evidence state:** medium / high / CONFIRMED
- **Baseline:** pre-existing на проверенном SHA.
- **Наблюдение:** [`adr_lifecycle.md`](../../operations/adr_lifecycle.md) в условиях создания говорит, что альтернативы уже сравнены, но позднее назначает сравнение TASK-владельцу. Подробная процедура требует явного решения владельца и evidence, а таблица переходов допускает `proposed → accepted` по факту PR approval. Дополнительно planned-milestone exception оставляет [`ADR_008`](../../adr/adr_008_data_storage_schema.md) без TASK, вопреки прямому решению владельца.
- **Риск:** агент может создать ADR слишком поздно или принять его без явного решения владельца.
- **Исправление:** оставить одно каноническое правило: ADR создаётся до сравнения, TASK собирает evidence, acceptance требует явного решения владельца; PR только доставляет зафиксированное решение. Удалить исключение для proposed ADR без TASK.
- **Проверка:** negative fixtures отклоняют acceptance только по PR и любой proposed ADR без единственной незавершённой TASK.

<a id="aud-026"></a>
### AUD-026 — Несвязанные служебные изменения включены в scope продуктовой TASK

- **Severity/Confidence/Evidence state:** medium / high / CONFIRMED
- **Baseline:** pre-existing на проверенном SHA.
- **Наблюдение:** [`TASK_013`](../tasks/task_013_inf_008.md) прямо сообщает, что [`milestones.md`](../../milestones.md) и [`audit_register.md`](audit_register.md) добавлены в `allowed_paths`, потому что это была единственная активная TASK, хотя изменения не относятся к поставке её компонента. [`AGENTS.md`](../../AGENTS.md) требует для служебных изменений не создавать и не загрязнять product TASK.
- **Риск:** `allowed_paths` становится ретроактивной меткой разрешения и перестаёт доказывать реальную область поставки.
- **Исправление:** убрать несвязанные пути и пояснение из TASK; проводить прямые owner-requested governance/audit изменения как service change; добавить проверку расширений, недостижимых от `component`/`decides`.
- **Проверка:** scope fixture отличает service change от product delivery и отклоняет несвязанное расширение карточки.

<a id="aud-027"></a>
### AUD-027 — Eval harness может остаться зелёным на stub после подключения реального провайдера

- **Severity/Confidence/Evidence state:** medium / high / CONFIRMED
- **Baseline:** pre-existing на проверенном SHA.
- **Наблюдение:** `main()` в [`run_eval_suite.py`](../../operations/scripts/eval/run_eval_suite.py) всегда вызывает `_default_gateway()`, который создаёт `StubModelGateway`. Карточка [`AUD-020`](audit_register.md#aud-020) утверждает, что после [`TASK_015`](../tasks/task_015_real_model_provider.md) runner начнёт измерять реальный provider без изменений, но CLI не имеет provider factory или конфигурации выбора.
- **Риск:** каноническая команда останется зелёной на echo-ответах и создаст ложное evidence качества реальной модели.
- **Исправление:** исправить утверждение реестра; в [`TASK_015`](../tasks/task_015_real_model_provider.md) добавить явный выбор/injection provider и раздельные stub/real profiles.
- **Проверка:** canonical entrypoint с намеренно деградировавшим non-stub provider завершается с кодом 1 и записывает provider/profile и точный SHA.
