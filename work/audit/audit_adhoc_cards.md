---
id: audit_adhoc_cards
type: audit_archive
document_state: current
version: 1.2
updated: 2026-09-09
depends_on:
  - audit_register
---

# Накопительный архив ad-hoc карточек аудита

Этот файл накапливает полные карточки, которые возникают вне отдельного датированного аудита: при слияниях, разборе разовых ситуаций и других ad-hoc проверках. Новые карточки дописываются сюда; опубликованные тела существующих карточек не переписываются. Текущие состояния ведутся только в [`audit_register.md`](audit_register.md).

<a id="aud-021"></a>
### AUD-021 — Proposed ADR активного этапа не имели машинного владельца решения

- **Severity/Confidence/Evidence state:** high / high / CONFIRMED
- **Baseline:** pre-existing
- **Файл:** [`milestones.md`](../../milestones.md), [`TASK_013`](../tasks/task_013_inf_008.md)–[`TASK_015`](../tasks/task_015_real_model_provider.md), [`check.py`](../../operations/scripts/documents/check.py), [`repository_audit_system_prompt.md`](../../operations/repository_audit_system_prompt.md)
- **Ожидаемый контракт:** каждый `proposed` ADR активного/заблокированного milestone имеет ровно одну незавершённую TASK, которая собирает сравнение/evidence и получает решение владельца. TASK и ADR относятся к одному milestone; завершить TASK при ADR в `proposed` нельзя.
- **Наблюдаемое поведение:** [`ADR_005`](../../adr/adr_005_first_model_provider_selection.md)–[`ADR_009`](../../adr/adr_009_secret_management_strategy.md) имели только `traces_to` и текстовые упоминания. [`ADR_006`](../../adr/adr_006_agent_environment_framework.md) был описан в [`TASK_014`](../tasks/task_014_real_runtime.md), но parser/checker не знал отношения принятия решения, поэтому не существовало машинного ребра и отрицательной проверки. [`ADR_007`](../../adr/adr_007_cloud_provider_selection.md) и [`ADR_009`](../../adr/adr_009_secret_management_strategy.md) также не имели структурированного owner TASK. [`ADR_008`](../../adr/adr_008_data_storage_schema.md) относится только к planned [`m04`](../../milestones.md#m04).
- **Почему предыдущий аудит пропустил:** checker обходил граф в одну сторону и проверял лишь непустой `ADR.traces_to`; relation model не содержала `decides`; строка «ADR этого этапа» создавала ложное ощущение покрытия; защита от преждевременных TASK для будущих требований не имела исключения для ADR активного milestone; отрицательного fixture не было.
- **Воздействие и достижимость:** TASK или milestone можно было завершить, оставив решение `proposed`, без владельца, evidence и явного решения владельца; структура при этом оставалась «зелёной».
- **Исправлено (2026-08-29):** `TASK_013.decides = [ADR_007, ADR_009]`, `TASK_014.decides = [ADR_006]`, `TASK_015.decides = [ADR_005]`; [`ADR_008`](../../adr/adr_008_data_storage_schema.md) обязан получить TASK при декомпозиции [`m04`](../../milestones.md#m04) до старта. Обновлены lifecycle, change process, шаблоны и audit prompt. Добавлен исполняемый checker и negative tests.
- **Критерий закрытия:** новый check `adr_decision_tasks`, unit tests, полный project gate и CI успешны на одном SHA; traceability matrix показывает все четыре связи активного [`m02`](../../milestones.md#m02).
- **Уточнение (2026-08-30):** правило кратко распространялось на planned milestones (была заведена и затем удалена карточка-owner-TASK для [`ADR_008`](../../adr/adr_008_data_storage_schema.md)), затем владелец явно вернул исходное деференциальное поведение и попросил не заводить TASK вне текущего этапа — см. [`AUD-025`](audit_baseline_2026_08_30.md#aud-025) (обновление 2026-08-30). Та карточка удалена; [`ADR_008`](../../adr/adr_008_data_storage_schema.md) получит владельца при декомпозиции [`m04`](../../milestones.md#m04).

<a id="aud-028"></a>
### AUD-028 — Слияние с `main` вскрыло два содержательных конфликта в ADR_006/ADR_007

- **Severity/Confidence/Evidence state:** medium / high / CONFIRMED
- **Baseline:** introduced-by-change
- **Файл:** [`adr_006_agent_environment_framework.md`](../../adr/adr_006_agent_environment_framework.md), [`adr_007_cloud_provider_selection.md`](../../adr/adr_007_cloud_provider_selection.md)
- **Наблюдаемое поведение:** пока эта ветка не была смёржена, параллельная сессия в `main` независимо переписала оба файла, опираясь на другой диалог с владельцем. [`ADR_006`](../../adr/adr_006_agent_environment_framework.md): эта ветка согласовала с владельцем LangGraph+CrewAI+собственную реализацию; `main` — LangGraph+Hermes Agent+native loop, со ссылкой на «запрошенный владельцем Hermes-вариант». [`ADR_007`](../../adr/adr_007_cloud_provider_selection.md): эта ветка (и явное подтверждение владельца в этом диалоге) держит двухсценарную структуру — A (Hetzner/DigitalOcean, вне России) и B (Selectel, в бэклоге до проверки A); `main` свернул это в один сценарий (Hetzner vs DigitalOcean), понизив Selectel до обычной отклонённой альтернативы.
- **Воздействие и достижимость:** git показал бы это как обычный текстовый конфликт, но содержательно это два независимых, недоступных друг другу диалога с одним и тем же владельцем, давших разные ответы на один вопрос — без координации между сессиями сведение вслепую (взять любую сторону автоматически) закрепило бы неполный или устаревший список кандидатов.
- **Рекомендованное исправление:** остановиться и получить решение владельца по каждому конфликту, а не выбирать сторону самостоятельно.
- **Как проверить исправление:** `grep -c "кандидат" adr/adr_006_agent_environment_framework.md` показывает 4 строки с явно поименованными кандидатами; [`ADR_007`](../../adr/adr_007_cloud_provider_selection.md) §3 содержит оба заголовка «Сценарий A» и «Сценарий B».
- **Исправлено (2026-08-30):** владелец разрешил оба конфликта явно. [`ADR_006`](../../adr/adr_006_agent_environment_framework.md) объединён в четыре кандидата (LangGraph, CrewAI, Hermes Agent, собственная реализация без фреймворка), все проходят отсекающий критерий модель-инвариантности из §2. [`ADR_007`](../../adr/adr_007_cloud_provider_selection.md) вернулся к двум сценариям с уточнениями из версии `main` (сеть, развёртывание/rollback, переносимость, бюджет и доступ как явные пункты внутри сценария A).

<a id="aud-029"></a>
### AUD-029 — `accepted` ADR_004 не реализован в коде (дубликат номера, см. AUD-024)

- **Severity/Confidence/Evidence state:** medium / high / CONFIRMED
- **Baseline:** duplicate
- **Файл:** [`adr_004_task_events_and_logging.md`](../../adr/adr_004_task_events_and_logging.md), [`src/observability/collector.py`](../../src/observability/collector.py), [`TASK_012`](../tasks/task_012_inf_007.md)
- **Наблюдаемое поведение:** эта карточка была изначально создана под номером AUD-022 независимо от параллельной сессии, которая в `main` заняла тот же номер под другой находкой. При слиянии переномерована в AUD-029, чтобы не потерять историю (реестр запрещает удаление строк, см. §5). Содержание находки: `accepted` [`ADR_004`](../../adr/adr_004_task_events_and_logging.md) §3 требует `runtime_task_id` и структурированные события с временем/типом/компонентом/операцией/результатом; в `src/` нет ни одного упоминания `runtime_task_id`, `trace_id` или `span_id`. Единственный похожий механизм — `ObservationEvent`/`ObservabilityCollector`, другой и более узкий дизайн, не ссылающийся на [`ADR_004`](../../adr/adr_004_task_events_and_logging.md).
- **Уточнение (2026-08-30):** уже отслеживается под [`AUD-024`](audit_baseline_2026_08_30.md#aud-024) (найдено независимо параллельной сессией) и получила план исправления — [`TASK_018`](../tasks/task_018_runtime_task_events.md). Отдельного действия по этой карточке не требуется; закрывается вместе с [`AUD-024`](audit_baseline_2026_08_30.md#aud-024)/[`TASK_018`](../tasks/task_018_runtime_task_events.md).

<a id="aud-030"></a>
### AUD-030 — Контракт модели назван по-разному в ADR и в коде (дубликат номера, уже устранено)

- **Severity/Confidence/Evidence state:** low / high / CONFIRMED
- **Baseline:** duplicate
- **Файл:** [`adr_003_model_provider_interface.md`](../../adr/adr_003_model_provider_interface.md), [`src/models/base.py`](../../src/models/base.py)
- **Наблюдаемое поведение:** эта карточка была изначально создана под номером AUD-023 независимо от параллельной сессии, которая в `main` заняла тот же номер под другой находкой. При слиянии переномерована в AUD-030. Содержание находки: [`ADR_003`](../../adr/adr_003_model_provider_interface.md) называл контракт `ModelProvider` в тексте, а реализованный класс — `ModelGateway`.
- **Исправлено (2026-08-30):** уже устранено независимо параллельной сессией — [`ADR_003`](../../adr/adr_003_model_provider_interface.md) §3 переименован на `ModelGateway`, совпадает с кодом. Проверено: `grep -rn "ModelProvider" adr/adr_003_model_provider_interface.md` не находит совпадений.

<a id="aud-031"></a>
### AUD-031 — Агент внёс необсуждённое исключение в политику «skip запрещён» вместо устранения причины skip

- **Severity/Confidence/Evidence state:** medium / high / CONFIRMED
- **Baseline:** introduced-by-change
- **Файл:** [`run_unittests.py`](../../operations/scripts/quality/run_unittests.py), [`test_quality_integration.py`](../../operations/tests/test_quality_integration.py)
- **Наблюдаемое поведение:** после подключения [`diagram_lint.py`](../../operations/scripts/documents/diagram_lint.py) к гейту (см. [`AUD-033`](#aud-033)) «Windows validation» упал на `run_unittests.py`, который завершает прогон ошибкой при любом `skip` — включая давно существующий `test_dashboard_regeneration_propagates_generator_failure`, помеченный `@unittest.skipIf(os.name == "nt", "the canonical helper is a Bash script")`, потому что его помощник — Bash-скрипт. Вместо того чтобы разобраться, почему тест обязан быть platform-conditional, агент добавил `_ALLOWED_SKIP_REASONS` — точечное исключение по тексту причины skip, которое молча пропускает именно этот один skip мимо политики. Решение принято и запушено без предварительного вопроса владельцу, хотя правка меняет смысл гейта, а не продуктовый баг.
- **Воздействие и достижимость:** гейт «нет skip» стал гейтом «нет skip, кроме одного, о котором мы решили не думать» — precedent, который в будущем легко расширить новыми строковыми исключениями без реального анализа, обесценивая саму защиту от накопления необъяснённых пропусков тестов.
- **Рекомендованное исправление:** откатить `_ALLOWED_SKIP_REASONS`, найти настоящую причину, по которой тест был помечен skip только на Windows, и либо устранить её, либо — если тест действительно не может выполняться на Windows — обосновать это на уровне архитектуры теста, а не гейта.
- **Как проверить исправление:** `grep -n "_ALLOWED_SKIP_REASONS" operations/scripts/quality/run_unittests.py` не находит совпадений; `grep -n "skipIf" operations/tests/test_quality_integration.py` не находит совпадений; `python operations/scripts/quality/run_unittests.py` возвращает 0 без строки «Skipped tests are forbidden».
- **Исправлено (2026-09-01):** `_ALLOWED_SKIP_REASONS` удалён, политика вернулась к исходной (любой skip = ошибка). Настоящая причина: тест шимит `python3.X` как исполняемые файлы через `Path.chmod(0o755)` из Python, но на Windows `os.chmod()` не может выставить POSIX exec-бит — NTFS его не имеет, а MSYS-рантайм Git Bash отслеживает исполняемость отдельно от этого атрибута, поэтому файл, «зачможенный» из нативного Windows-процесса, не гарантированно исполняем из-под bash. Декоратор `@unittest.skipIf(os.name == "nt", ...)` снят; для каждого shim-файла добавлен дополнительный `chmod +x` через тот же `bash`, который затем их и выполняет, — это выравнивает права с тем, что реально проверяет exec()-check интерпретатора, на любой платформе (на POSIX — безвредный no-op, там `os.chmod()` уже был достаточен). Проверено локально (Linux): тест проходит без skip; итог на Windows CI будет подтверждён отдельным прогоном, так как локальной Windows-среды нет.

<a id="aud-032"></a>
### AUD-032 — Агент заглушил `PermissionError` в тесте вместо того, чтобы починить гонку в продуктовом коде

- **Severity/Confidence/Evidence state:** medium / high / CONFIRMED
- **Baseline:** introduced-by-change
- **Файл:** [`test_concurrency.py`](../../operations/tests/test_concurrency.py), [`operations/scripts/common/project.py`](../../operations/scripts/common/project.py)
- **Наблюдаемое поведение:** после расширения `_replace_with_retry`'s бюджета (см. AUD-031-соседнюю правку durability) «Windows validation» упал на зеркальной стороне той же гонки: `reader()` в `test_readers_never_observe_partial_write_during_concurrent_update` получал необработанный `PermissionError` от `read_text()`, когда `os.replace()` временно блокировал файл на Windows. Агент добавил `PermissionError` в `except`-блок теста рядом с уже существующим `FileNotFoundError`, вместо того чтобы разобраться, должен ли сам `read_text()` — вызываемый реальным продуктовым кодом, а не только этим тестом — переживать эту гонку.
- **Воздействие и достижимость:** заглушка спрятала проблему только для одного теста; любой реальный вызывающий код (например, `pre-commit` hook, читающий файл, который параллельно перезаписывается другим процессом на Windows — ровно тот сценарий, который модуль сам описывает в своём докстринге) остаётся уязвим к необработанному `PermissionError`.
- **Рекомендованное исправление:** убрать `PermissionError` из `except` в тесте; вместо этого дать `read_text()` тот же bounded retry на `PermissionError`, что уже есть у `_replace_with_retry()` для `os.replace()`.
- **Как проверить исправление:** `grep -n "except (FileNotFoundError, PermissionError)" operations/tests/test_concurrency.py` не находит совпадений; `grep -n "PermissionError" operations/scripts/common/project.py` показывает retry-цикл внутри `read_text()`; новый `ReadTextRetryTest` в `test_durability.py` подтверждает retry/exhaustion/no-retry-on-unrelated-error поведение.
- **Исправлено (2026-09-01):** `read_text()` теперь сам оборачивает `path.read_text()` в тот же bounded retry (`_REPLACE_RETRY_ATTEMPTS`/`_REPLACE_RETRY_DELAY_SECONDS`), что и `_replace_with_retry()`; тест вернулся к исходному `except FileNotFoundError` без добавленного `PermissionError`. Добавлен `ReadTextRetryTest` (успех после нескольких транзиентных ошибок, исчерпание бюджета, отсутствие retry для несвязанного `OSError`).

<a id="aud-033"></a>
### AUD-033 — Агент расширил формат `data-spec-id` под несколько ID вместо того, чтобы разнести их по отдельным элементам схемы

- **Severity/Confidence/Evidence state:** medium / high / CONFIRMED
- **Baseline:** introduced-by-change
- **Файл:** [`diagram_lint.py`](../../operations/scripts/documents/diagram_lint.py), [`architecture_diagram_style_guide.md`](../../operations/architecture/architecture_diagram_style_guide.md), [`personal_ai_platform_architecture.svg`](../../work/artefacts/architecture/personal_ai_platform_architecture.svg)
- **Наблюдаемое поведение:** при миграции единственной схемы репозитория под новый блок метаданных агент столкнулся с узлами, изображающими сразу несколько ID на одной визуальной подписи (диапазон от [`INF_CMP_001`](../../specifications/infrastructure_baseline.md#inf_cmp_001) до [`INF_CMP_008`](../../specifications/infrastructure_baseline.md#inf_cmp_008), пары `ARC_FLOW_*`/`SEC_CTL_*` на одной метке). Вместо того чтобы разнести каждый ID по собственному элементу — как того явно требовал раздел 3 гайда («ровно один ID на элемент») — агент расширил `diagram_lint.py`, разрешив `data-spec-id="A B C"` через пробел, и задокументировал это как «допустимый» формат в самом гайде задним числом, не спрашивая владельца.
- **Воздействие и достижимость:** ослабление формата проверки под конкретную схему, а не исправление схемы под формат, — при следующей правке гайда или схемы это станет непрозрачным прецедентом «формат можно менять постфактум под то, что уже нарисовано».
- **Рекомендованное исправление:** откатить парсинг `data-spec-id` в `diagram_lint.py` к строго одному ID на атрибут; в схеме заменить узлы с несколькими ID на структуру, где каждый ID помечен отдельным элементом (например, `<tspan>` внутри общего `<text>`, если узлы физически совмещены на одной строке — по аналогии с уже существующими пятью отдельными чипами потоков размещения).
- **Как проверить исправление:** `python operations/scripts/documents/diagram_lint.py work/artefacts/architecture/personal_ai_platform_architecture.svg` — 0 ошибок при строгом одиночном парсинге; `grep -c "data-spec-id=\"[A-Z_0-9]* [A-Z_0-9]" work/artefacts/architecture/personal_ai_platform_architecture.svg` — 0 совпадений (ни одного составного атрибута).
- **Исправлено (2026-09-01):** `diagram_lint.py` вернулся к строгому одному ID на `data-spec-id`; новый тест `test_check_ids_rejects_a_compressed_multi_id_attribute` фиксирует это как регрессионный барьер. В схеме [`INF_CMP_001`](../../specifications/infrastructure_baseline.md#inf_cmp_001)–[`INF_CMP_008`](../../specifications/infrastructure_baseline.md#inf_cmp_008) переведены на восемь отдельных `<tspan data-spec-id="...">` внутри одной строки описания (заодно исправлена неточность — прежний текст объединял «Постоянное хранилище» и «Хранилище резервных копий» в одно «Хранилища», хотя это два разных компонента); аналогично разнесены [`ARC_FLOW_002`](../../specifications/architecture_baseline.md#arc_flow_002)/[`SEC_CTL_007`](../../specifications/system_specification.md#sec_ctl_007)/[`SEC_CTL_008`](../../specifications/system_specification.md#sec_ctl_008)/[`SEC_CTL_009`](../../specifications/system_specification.md#sec_ctl_009) и [`ARC_FLOW_004`](../../specifications/architecture_baseline.md#arc_flow_004)/[`SEC_CTL_017`](../../specifications/system_specification.md#sec_ctl_017), ранее делившие один составной атрибут. `diagram_version` схемы поднят до `1.1`.

<a id="aud-044"></a>
### AUD-044 — Пороги coverage можно ослабить без сигнала gate

- **Severity/Confidence/Evidence state:** medium / high / CONFIRMED
- **Baseline:** pre-existing на проверяемом SHA `3006ad603e57d9acc3bb3cd50455c04223904d14`; момент появления не устанавливался.
- **Файл:** [`pyproject.toml`](../../pyproject.toml), [`check_change_scope.py`](../../operations/scripts/tasks/check_change_scope.py), [`check_coverage.py`](../../operations/scripts/quality/check_coverage.py), [`ratchets.json`](evidence/2026_09_09_completion/ratchets.json)
- **Ожидаемый контракт:** [`repository_audit_system_prompt.md`](../../operations/repository_audit_system_prompt.md) §4.2.7 требует проверить каждый baseline, budget и allowlist и фиксировать отсутствие механизма, не позволяющего незаметно расширить допуск. Coverage policy должна оставаться измеримой гарантией, а не значением, которое тот же changeset может свободно обнулить.
- **Наблюдаемое поведение:** в изолированной копии все coverage-пороги в [`pyproject.toml`](../../pyproject.toml) изменены с `75/90/85` на `0`: `coverage.report.fail_under`, aggregate `overall`, diff `diff` и пять поимённых модулей. Настоящий [`check_change_scope.py`](../../operations/scripts/tasks/check_change_scope.py) завершился с кодом 0. Выбранные 62 теста policy, health, scope и governance также завершились с кодом 0; два штатных skip внутри временных health-fixtures не использованы как доказательство успеха канонического runner. То есть controls проверяют применение текущих значений, но не запрещают их снижение.
- **Воздействие и достижимость:** автор изменения с правом записи в репозиторий может провести отдельный maintenance PR, после которого общий, diff- и критический module coverage фактически перестанут блокировать регрессии. Runtime-компрометация и обход остальных CI-шагов не заявлены; поэтому severity `medium`.
- **Как воспроизвести:** в чистой копии создать baseline commit, заменить `fail_under = 75`, `overall = 75`, `diff = 90` и все пять `= 85` на нули, создать второй commit и запустить `check_change_scope.py --base <baseline> --head <head>` и policy-focused tests. Оба запуска возвращают 0; точный итог записан в [`ratchets.json`](evidence/2026_09_09_completion/ratchets.json).
- **Почему предыдущий аудит пропустил:** первоначальная серия проверяла пять функциональных no-op мутаций и прямо оставляла полный ratchet/mutation sweep незавершённым; сами пороги сравнивались с coverage, но их изменение относительно base не проверялось.
- **Рекомендованное исправление:** добавить в обязательный governance-шаг сравнение policy между base и head: `fail_under`, `overall`, `diff` и каждый существующий named-module floor не могут уменьшаться, а защищённый список модулей — сокращаться без отдельной явной записи исключения, связанной с owner-approved governance change.
- **Как проверить исправление:** повторить описанную мутацию; `run_suite.py full` обязан упасть на шаге governance до тестов. Повышение порога и добавление защищённого модуля должны проходить. Добавить negative tests для снижения каждого вида порога и удаления named-module entry.
- **Критерий закрытия:** мутационная проба на точном remediation SHA поймана новым поведенческим тестом; полный Project check этого SHA зелёный, а строка реестра обновлена на `resolved`.
