---
id: audit_register
type: audit_register
document_state: current
version: 1.2
updated: 2026-08-29
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
| AUD-007 | critical | open | 2026-08-29 | 2026-09-05 | repository_owner | [`project_check.yml`](../../.github/workflows/project_check.yml), [`task_012_inf_007.md`](../tasks/task_012_inf_007.md) | GitHub Actions не диспетчеризовал ни одного джоба Project check с 2026-08-25 06:38 UTC (~30+ мёрджей, включая HEAD); причина самораскрыта — квота Actions, ожидается после 2026-09-01. |
| AUD-008 | high | open | 2026-08-29 | 2026-09-05 | repository_owner | [`template_contracts.py`](../../operations/scripts/documents/template_contracts.py), [`human_status.py`](../../operations/scripts/status/human_status.py), [`m01_final_report.md`](../acceptance/m01_final_report.md) | `run_suite.py full` реально красный на HEAD: 2 новые mypy-ошибки при бюджете 0, плюс [`m01_final_report.md`](../acceptance/m01_final_report.md) разошёлся со своим генератором — обе причины введены последним мёрджем. |
| AUD-009 | high | open | 2026-08-29 | 2026-09-05 | repository_owner | [`m01.json`](../acceptance/m01.json), [`adr_001_language_and_runtime.md`](../../adr/adr_001_language_and_runtime.md) | Акт приёмки [`m01`](../../milestones.md#m01) заявляет переход всех 9 ADR `proposed → accepted`; ни один коммит за всю историю не устанавливал `decision_state: accepted`; все 9 ADR остаются `proposed`. |
| AUD-010 | medium | open | 2026-08-29 | 2026-09-12 | repository_owner | [`project_status.md`](../../project_status.md) | Owner-facing статус не показывает состояние gate/CI и ADR-статус; рамка «13/17 задач m02» переоценивает близость к достижимой цели milestone. |
| AUD-011 | medium | open | 2026-08-29 | 2026-09-12 | repository_owner | [`document_frontmatter_standard.md`](../../operations/document_frontmatter_standard.md) | Документ объявляет себя единственным источником истины для frontmatter, конфликтуя с реально применяемым [`change_process.md`](../../operations/change_process.md) §8; ноль входящих ссылок. |
| AUD-012 | medium | open | 2026-08-29 | 2026-09-12 | repository_owner | [`task_template.md`](../../operations/templates/task_template.md), [`change_process.md`](../../operations/change_process.md) | Поле `delivery_role` живое и структурно важное, но не описано ни в одном frontmatter-контракте и не валидируется `check.py`. |
| AUD-013 | medium | open | 2026-08-29 | 2026-09-12 | repository_owner | [`control.py`](../../src/owner_control/control.py) | Блокировка sensitive-action не имеет timeout/staleness-проверки и recovery-процедуры; крах процесса под блокировкой перманентно закрывает владельцу чувствительные действия. |
| AUD-014 | medium | open | 2026-08-29 | 2026-09-12 | repository_owner | [`procedure_map.md`](../../operations/procedure_map.md) | 6 содержательных документов `operations/*.md` недостижимы из «дерева решений для каждой ситуации» и не связаны ни одной входящей ссылкой. |
| AUD-015 | medium | open | 2026-08-29 | 2026-09-12 | repository_owner | [`check.py`](../../operations/scripts/documents/check.py) | Канонический traceability-checker глотает исключения из собственных коллекторов (`except Exception: pass`) — не воспроизведено вживую, но риск тихой деградации trust-anchor инструмента реален. |
| AUD-016 | low | open | 2026-08-29 | 2026-09-19 | repository_owner | [`telegram.py`](../../src/channels/telegram.py) | Единственный внешне-наблюдаемый error-path канала (timeout → `ChannelError`) недостижим ни из одного текущего вызывающего кода и не покрыт тестом. |
| AUD-017 | low | open | 2026-08-29 | 2026-09-19 | repository_owner | [`test_quality_integration.py`](../../operations/tests/test_quality_integration.py), [`run_unittests.py`](../../operations/scripts/quality/run_unittests.py) | Тест генератора хрупок к порядку установленных версий Python на PATH; gate «без skip» отдельно не выделяет unexpectedSuccesses (xpass). |
| AUD-018 | low | open | 2026-08-29 | 2026-09-19 | repository_owner | [`test_007.md`](../tests/test_007.md), [`quality_registry.json`](../../operations/quality_registry.json) | TEST_007 противоречит сам себе по числу тестов (16 vs 8); [`quality_registry.json`](../../operations/quality_registry.json) перечисляет 3 evidence-типа в каталоге, но не в `required_evidence` без объяснения; устаревший комментарий в `.gitignore`. |
| AUD-019 | low | open | 2026-08-29 | 2026-09-19 | repository_owner | [`sqlite_store.py`](../../src/task_state/sqlite_store.py) | Пути обработки повреждённых данных SQLite-хранилища задач не тестируются — в отличие от эквивалентной проверки в `owner_control` для того же класса риска. |
| AUD-020 | medium | open | 2026-08-29 | 2026-09-12 | repository_owner | [`repository_audit_system_prompt.md`](repository_audit_system_prompt.md) §7.5 | Фреймворк аудита и репозиторий не содержат ни одной проверки наличия eval/regression-набора для качества выхода модели; пробел останется незамеченным до появления реального провайдера ([`TASK_015`](../tasks/task_015_real_model_provider.md)). |

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

<a id="aud-009"></a>
### AUD-009 — Акт приёмки m01 заявляет недостоверный переход всех 9 ADR в accepted

- **Severity/Confidence/Evidence state:** high / high / CONFIRMED
- **Файл:** [`m01.json:27-63`](../acceptance/m01.json); коммит `a7831afbe2d3417ba71b1e68c0ee1254116151ca`; [`adr_001_language_and_runtime.md`](../../adr/adr_001_language_and_runtime.md) и остальные 8 ADR
- **Ожидаемый контракт:** акт приёмки милестона — канонический источник истины о завершении этапа ([`project_rules.md`](../../project_rules.md) §2); он не должен утверждать эффект, которого не было.
- **Наблюдаемое поведение:** [`m01.json`](../acceptance/m01.json) содержит массив `adr_transitions` из 9 записей, каждая `"state_change": "proposed → accepted"`. `git log -p --all -- adr/` не содержит ни одного вхождения строки `decision_state: accepted` за всю историю репозитория. `git show --stat a7831af` (коммит, чьё сообщение заявляет этот переход) не затрагивает ни одного файла под `adr/`. На SHA `218eb61` все 9 ADR остаются `decision_state: proposed`. Отдельно: [`ADR_005`](../../adr/adr_005_first_model_provider_selection.md)–009 указывают `traces_to` не на [`m01`](../../milestones.md#m01), а на [`m02`](../../milestones.md#m02)/[`m04`](../../milestones.md#m04)/[`m06`](../../milestones.md#m06) — переход для них не мог произойти в принципе по логике `apply.py`, независимо от того, что реально выполнялось.
- **Воздействие и достижимость:** не блокирует механически приёмку [`m01`](../../milestones.md#m01) (критерии [`milestones.md#m01`](../../milestones.md#m01) не требуют ADR-acceptance как gate), но высокоавторитетный evidence-документ содержит конкретное, опровержимое ложное утверждение — тот самый класс самообмана инструмента, который [`AGENTS.md`](../../AGENTS.md) §5.1 прямо запрещает для gate/evidence.
- **Как воспроизвести:** `git log -p --all -- adr/ | grep "decision_state: accepted"` (пусто); `git show --stat a7831afbe2d3417ba71b1e68c0ee1254116151ca` (нет пути `adr/`); `grep decision_state adr/adr_*.md` (все `proposed`).
- **Рекомендованное исправление:** решение владельца — либо реально выполнить переход [`ADR_001`](../../adr/adr_001_language_and_runtime.md)–004 (единственные, кто `traces_to: m01`) отдельным PR с честной evidence-записью, либо скорректировать нарратив [`m01.json`](../acceptance/m01.json)/[`adr_lifecycle.md`](../../operations/adr_lifecycle.md) корректирующей записью (без переписывания истории).
- **Как проверить исправление:** `grep decision_state adr/adr_00{1,2,3,4}_*.md` показывает `accepted`, либо [`m01.json`](../acceptance/m01.json) больше не содержит недостоверного `adr_transitions`.

<a id="aud-010"></a>
### AUD-010 — Owner-facing статус не показывает состояние gate/CI и переоценивает близость к цели milestone

- **Severity/Confidence/Evidence state:** medium / high / CONFIRMED
- **Файл:** [`project_status.md`](../../project_status.md)
- **Наблюдаемое поведение:** владелец, читающий только [`project_status.md`](../../project_status.md), не может увидеть ни AUD-007 (CI не работает), ни AUD-008 (gate реально красный локально), ни то, что ADR, на которые опираются заявленные возможности, всё ещё `proposed` (AUD-009). Рамка «13/17 задач [`m02`](../../milestones.md#m02) выполнено» не даёт сигнала, что все 4 оставшиеся задачи (`TASK_014-017`) несут ~100% внешнего, пользовательского риска milestone (все три внешних адаптера — Telegram Bot API, agent runtime, model provider — остаются эхо-заглушками).
- **Рекомендованное исправление:** добавить в генератор статуса поле состояния gate/CI (или явную пометку «последняя проверка недоступна»); добавить визуальное отличие component vs terminal-outcome задач в таблице (используя уже существующее поле `delivery_role`, см. AUD-012).
- **Как проверить исправление:** обновлённый [`project_status.md`](../../project_status.md) содержит статус последнего известного прогона gate и визуально выделяет оставшиеся terminal-outcome задачи.

<a id="aud-011"></a>
### AUD-011 — Конкурирующий, осиротевший документ о стандарте frontmatter

- **Severity/Confidence/Evidence state:** medium / high / CONFIRMED
- **Файл:** [`operations/document_frontmatter_standard.md`](../../operations/document_frontmatter_standard.md)
- **Наблюдаемое поведение:** документ объявляет себя «единственным источником истины» для YAML frontmatter, конфликтуя с реально применяемым и enforced [`change_process.md`](../../operations/change_process.md) §8. Ноль входящих ссылок из любого authority-файла или [`procedure_map.md`](../../operations/procedure_map.md). Правило порядка полей (§5) не соблюдается реальными ADR-файлами и не проверяется `metadata.py`/`check.py`. Пропускает живые поля (`delivery_role`, `blocker`, `owner_followups`).
- **Рекомендованное исправление:** слить уникальный контент (правило порядка полей, если оно того стоит) в [`change_process.md`](../../operations/change_process.md) §8, либо пометить `document_state: superseded`; убрать самозаявление «единственный источник истины». Требует явного согласования владельца (AGENTS.md §5 — не менять соглашения об именовании самостоятельно).
- **Как проверить исправление:** остаётся ровно один документ, claiming ownership фронтматтер-контракта; `grep "единственный источник истины"` возвращает только актуальных владельцев этого статуса.

<a id="aud-012"></a>
### AUD-012 — `delivery_role` не документирован ни в одном frontmatter-контракте

- **Severity/Confidence/Evidence state:** medium / high / CONFIRMED
- **Файл:** [`operations/templates/task_template.md`](../../operations/templates/task_template.md), [`work/tasks/task_014_real_runtime.md`](../tasks/task_014_real_runtime.md)…[`task_017_m02_live_e2e.md`](../tasks/task_017_m02_live_e2e.md), [`change_process.md`](../../operations/change_process.md) §8.1
- **Наблюдаемое поведение:** поле `delivery_role` (`component`/`terminal_outcome`) — структурно важно (различает stub-TASK от закрывающих milestone, [`change_process.md`](../../operations/change_process.md) §7.1), присутствует в 4 из 17 карточек TASK и в 2 генераторах, но отсутствует в обоих документах, претендующих на перечисление TASK-контракта, и не валидируется `check.py` — ни один запуск не проверяет, что terminal-outcome задача из очереди milestone действительно так помечена.
- **Рекомендованное исправление:** добавить `delivery_role` в таблицу полей TASK в [`change_process.md`](../../operations/change_process.md) §8.1; добавить проверку в `check.py`, что каждая задача из терминальной очереди milestone имеет `delivery_role: terminal_outcome`.
- **Как проверить исправление:** новая проверка `check.py` падает на синтетической TASK с несоответствующим/отсутствующим `delivery_role` в терминальной очереди.

<a id="aud-013"></a>
### AUD-013 — Блокировка sensitive-action не имеет timeout и recovery-процедуры

- **Severity/Confidence/Evidence state:** medium / high / CONFIRMED
- **Файл:** [`src/owner_control/control.py:86-103`](../../src/owner_control/control.py) (`_exclusive_state`)
- **Наблюдаемое поведение:** `os.mkdir`-блокировка вокруг `authorize_sensitive_action` не имеет timeout, retry или проверки «протухания» (PID/возраст держателя). Нигде в репозитории ([`change_process.md`](../../operations/change_process.md), [`state_machines.md`](../../operations/state_machines.md), `operations/procedures/`) не описано, что именно означает «recovery is required» операционно. Крах процесса между `os.mkdir` и `os.rmdir` (реалистичный сценарий — OOM-kill, принудительная остановка контейнера) навсегда блокирует все последующие чувствительные действия владельца, пока кто-то вручную не удалит `owner_control_actions.lock` — без единой инструкции в репозитории, что это правильное исправление.
- **Воздействие и достижимость:** напрямую достижимо любым крахом процесса во время удержания блокировки; поскольку [`ARC_CMP_002`](../../specifications/architecture_baseline.md#arc_cmp_002) — единая точка авторизации для всех чувствительных действий платформы, это правдоподобный полный self-lockout владельца. Fail-closed здесь — правильный default, но полное отсутствие runbook превращает спроектированное свойство безопасности в незадокументированную ловушку.
- **Рекомендованное исправление:** записывать PID и timestamp держателя блокировки в директорию блокировки; добавить явную (одобренную владельцем, не автоматическую) команду восстановления, которая проверяет, что держатель действительно мёртв, прежде чем очищать блокировку — либо, как минимум, добавить операционный runbook с точным описанием, что проверить и что удалить.
- **Как проверить исправление:** новый тест симулирует крах (создаёт директорию блокировки, не вызывая `authorize_sensitive_action` до завершения) и подтверждает, что документированная процедура восстанавливает нормальную работу без обхода identity/emergency-проверок.

<a id="aud-014"></a>
### AUD-014 — Шесть операционных документов недостижимы из карты процедур

- **Severity/Confidence/Evidence state:** medium / high / CONFIRMED
- **Файл:** [`operations/adr_lifecycle.md`](../../operations/adr_lifecycle.md), [`state_machines.md`](../../operations/state_machines.md), [`threat_review_triggers.md`](../../operations/threat_review_triggers.md), [`license_policy.md`](../../operations/license_policy.md), [`procedures/file_update_dependencies.md`](../../operations/procedures/file_update_dependencies.md), [`examples/sample_task_lifecycle.md`](../../operations/examples/sample_task_lifecycle.md)
- **Наблюдаемое поведение:** [`AGENTS.md`](../../AGENTS.md) называет [`procedure_map.md`](../../operations/procedure_map.md) «детальным деревом решений для каждой ситуации», но этот файл ведёт лишь к 3 из ~9+ реальных процедурных документов. Ни один из перечисленных 6 файлов не имеет входящей ссылки ни из одного authority-файла, [`procedure_map.md`](../../operations/procedure_map.md) или друг из друга. Содержимое всех шести прочитано полностью и признано реальным, не дублирующим — дефект чисто навигационный, не дублирование и не мёртвый код.
- **Рекомендованное исправление:** добавить по одной строке в таблицу [`procedure_map.md`](../../operations/procedure_map.md) (или в список утилит [`AGENTS.md`](../../AGENTS.md) §6) на каждый из 6 файлов, называя ситуацию, которую он описывает.
- **Как проверить исправление:** `grep -c "adr_lifecycle\|state_machines\|threat_review_triggers\|license_policy\|file_update_dependencies\|sample_task_lifecycle" operations/procedure_map.md` возвращает ≥6.

<a id="aud-015"></a>
### AUD-015 — Канонический traceability-checker глотает исключения из собственных коллекторов

- **Severity/Confidence/Evidence state:** medium / medium / SUSPECTED
- **Файл:** [`operations/scripts/documents/check.py:269-279, 856-872`](../../operations/scripts/documents/check.py) (`_known_reference_ids`, `check_test_specs`)
- **Наблюдаемое поведение:** оба места откатываются к пустому множеству/словарю при ЛЮБОМ исключении из `collect_traceable_elements`/`collect_milestones`/`load_quality_registry`, вместо того чтобы явно провалить проверку. На текущем SHA `check.py --all --json` проходит чисто (22/22) — ветка не была замечена сработавшей вживую, поэтому статус понижен до `SUSPECTED`, а не `CONFIRMED`.
- **Воздействие:** если будущее изменение документа/реестра внесёт реальный баг парсера в эти коллекторы, checker молча недосчитает известные ID (более безопасное направление ошибки — больше ложных «unknown reference», а не меньше), но это увеличит стоимость отладки и риск «исправления не того».
- **Рекомендованное исправление:** сузить типы перехватываемых исключений до реально ожидаемых, и/или логировать проглоченное исключение в `runtime/check_summary.json`, даже если общая проверка всё равно проходит.
- **Как проверить исправление:** новый тест подаёт заведомо некорректный вход в `collect_traceable_elements`/`collect_milestones`, достижимый из `check_test_specs`/`_known_reference_ids`, и подтверждает, что сбой становится видимым, а не тихо поглощается.

<a id="aud-016"></a>
### AUD-016 — Timeout-путь TelegramChannel.receive() недостижим и не тестирован

- **Severity/Confidence/Evidence state:** low / high / CONFIRMED
- **Файл:** [`src/channels/telegram.py:65-68`](../../src/channels/telegram.py)
- **Наблюдаемое поведение:** единственный документированный error-path канала (`Channel.receive()` → `ChannelError` при 30-секундном timeout) не вызывается ни одним текущим кодом (`Orchestrator` вызывает только `.send()`) и не покрыт ни одним из 16 тестов `test_channels.py`. Измеренное покрытие подтверждает: строки 67-68 явно отмечены как missing. Это ровно тот контракт, который понадобится [`TASK_016`](../tasks/task_016_real_telegram.md) (реальный Telegram Bot API).
- **Рекомендованное исправление:** добавить тест, сокращающий timeout (параметр или monkey-patch `asyncio.wait_for`), подтверждающий `ChannelError` при пустой очереди без ожидания реальных 30 секунд.
- **Как проверить исправление:** новый тест проходит; `coverage report` показывает `telegram.py` на 100% (или явно документирует остаток `# pragma: no cover` с причиной).

<a id="aud-017"></a>
### AUD-017 — Хрупкость теста регенерации к версии Python + xpass не выделяется отдельно

- **Severity/Confidence/Evidence state:** low / high / CONFIRMED
- **Файл:** [`operations/tests/test_quality_integration.py:119-148`](../../operations/tests/test_quality_integration.py); [`pre_commit_regenerate_dashboards.sh:16-26`](../../operations/hooks/pre_commit_regenerate_dashboards.sh); [`run_unittests.py:24-30`](../../operations/scripts/quality/run_unittests.py)
- **Наблюдаемое поведение:** (а) `find_python()` в хуке предпочитает новейший доступный интерпретатор (`python3.14`→…→`python3.12`) через `command -v`, который резолвится по реальному PATH, а не только по тестовому шиму — на любой машине с уже установленным `python3.13`/`3.14` тест ложно падает на несвязанном assertion; (б) "no skips" gate в `run_unittests.py` проверяет только `result.skipped`, не выделяя `result.unexpectedSuccesses` отдельным сообщением — пока безопасно (`wasSuccessful()` всё равно поймает xpass), но нет ни одного `expectedFailure`-теста, чтобы это проверить, и сообщение об ошибке было бы неотличимо от обычного провала.
- **Рекомендованное исправление:** (а) шимить все имена интерпретаторов, которые пробует цикл, либо передавать явный override; (б) отдельно проверять и называть `result.unexpectedSuccesses`.
- **Как проверить исправление:** тест (а) проходит и на машине с несколькими версиями Python; синтетический `expectedFailure`-тест для (б) даёт отдельное, узнаваемое сообщение.

<a id="aud-018"></a>
### AUD-018 — Мелкая гигиена evidence-документов

- **Severity/Confidence/Evidence state:** low / high / CONFIRMED
- **Файл:** [`work/tests/test_007.md:59,72,132`](../tests/test_007.md); [`operations/quality_registry.json`](../../operations/quality_registry.json); `.gitignore`
- **Наблюдаемое поведение:** [`TEST_007`](../tests/test_007.md) в разных разделах называет разное число тестов для одного файла (§4: 16, §5/§10: 8) — реальное число (посчитано напрямую) — 16; [`quality_registry.json`](../../operations/quality_registry.json) перечисляет `m02_security_tests`/`m02_e2e_tests`/`m02_infrastructure_tests` в `evidence_catalog`, но не в `m02_development.required_evidence`, без пояснения, преднамеренно ли это фазирование; `.gitignore` всё ещё описывает конвенцию «versioned generated markdown stays in git» для директории `generated/`, полностью удалённой коммитом `dc4ee8b`.
- **Рекомендованное исправление:** привести [`TEST_007`](../tests/test_007.md) к единому числу (16); владелец/мейнтейнер поясняет намерение по `required_evidence`; убрать устаревший комментарий и связанные с ним ignore-паттерны из `.gitignore` при следующем изменении файла.
- **Как проверить исправление:** все три раздела [`TEST_007`](../tests/test_007.md) согласованы; `.gitignore` не упоминает `generated/`, если директория не появится вновь как tracked.

<a id="aud-019"></a>
### AUD-019 — Пути обработки повреждённых данных в SQLite-хранилище задач не тестируются

- **Severity/Confidence/Evidence state:** low / medium / SUSPECTED
- **Файл:** [`src/task_state/sqlite_store.py:81-82,84,137-138`](../../src/task_state/sqlite_store.py) (`_decode`, `load_task`)
- **Наблюдаемое поведение:** измеренное покрытие подтверждает, что эти строки (обработка `JSONDecodeError`, не-dict значений, неизвестного `state`) никогда не исполняются; `test_persistent_task_state.py` содержит только 3 теста, ни один не пишет напрямую повреждённый `metadata_json`/`checkpoint_data_json` в SQLite-файл. Контрастирует с гораздо более строгой проверкой того же класса риска (JSON-в-хранилище, повреждение) в `owner_control`.
- **Рекомендованное исправление:** добавить тесты по образцу `test_owner_control.py` — напрямую записать невалидный JSON/не-dict/неизвестный `state` в строку SQLite и подтвердить, что `TaskLifecycleError` поднимается.
- **Как проверить исправление:** новые тесты проходят; строки из отчёта покрытия перестают быть missing.

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

## 5. Правило обновления

После зелёного `Project check` на точном SHA записи исправленных findings переводятся в `resolved` отдельным служебным PR. Для `accepted_risk` обязательно сохраняются явное решение владельца, ответственный, срок пересмотра и компенсирующий контроль. Удаление строк запрещено: закрытая finding остаётся историей реестра, а не удаляется.
