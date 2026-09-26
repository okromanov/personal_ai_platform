---
id: audit_baseline_2026_09_25
type: audit_baseline
document_state: current
version: 1.0
updated: 2026-09-25
depends_on: []
---

# Аудит репозитория — 2026-09-25

## 1. Проверенная редакция

- Git SHA: `5713a82f440a318ee89a77cff825430b13adfdf2`.
- Ветка: `main`; режим: `FULL_REPOSITORY`, аудит только для чтения.
- Применённый prompt: [`repository_audit_system_prompt.md`](../../operations/repository_audit_system_prompt.md) v5.4.
- Manifest и machine-readable приложения: [`manifest.json`](evidence/2026_09_25_completion/manifest.json), [`findings.json`](evidence/2026_09_25_completion/findings.json), [`gate_mutation_sweep.json`](evidence/2026_09_25_completion/gate_mutation_sweep.json), [`self_check.json`](evidence/2026_09_25_completion/self_check.json), [`sha256sums.txt`](evidence/2026_09_25_completion/sha256sums.txt).
- Дата наблюдения: 2026-09-25; этот документ публикуется отдельным changeset после самого аудита.

## 2. Итог

**Readiness: NOT READY.** AUD-047 — подтверждённый HIGH: канонический локальный full gate невоспроизводим на Windows-среде владельца (пять независимых механизмов). Дополнительно восемь непринятых MEDIUM (AUD-048…AUD-055). Серверный CI на точном SHA зелёный (run 35919250552, все job success, включая gitleaks dir+git и pip-audit), но не заменяет локальное evidence. Сплошной мутационный проход подтвердил фальсифицируемость 43 из 45 проверок gate; две проверки (`check_owner_interface`, `validate_document_metadata`) обезвреживаются незаметно (AUD-049, AUD-050). Исправления AUD-045/046 подтверждены на точном SHA и переведены в `resolved` в общем реестре.

Глубина относительно предыдущего аудита расширена: выполнены полный изолированный checkout, реальный локальный gate, сплошной mutation sweep и ignored-file scan — ровно то, что предыдущий baseline назначил обязательным повтором. Рост числа находок читается как лучший обзор, а не как деградация репозитория.

### Манифест и краткий итог

| Поле | Значение |
|---|---|
| Режим | FULL_REPOSITORY, аудит только для чтения |
| Репозиторий / ветка / HEAD | `okromanov/personal_ai_platform` / `main` / `5713a82f440a318ee89a77cff825430b13adfdf2` |
| Предыдущий baseline | `fa707b3fd6efa238a62f3bade91636e8458ad266` от 2026-09-23 |
| Промпт / аудитор | `operations/repository_audit_system_prompt.md`, версия 5.4 / Kimi Code CLI |
| Проверяемый состав | Полный tracked-tree: 342 файла; изолированный worktree на detached HEAD; основная копия не изменялась |
| Среда | Windows 11 x64, Git Bash, Python 3.14.7 (CI использует 3.12), отдельный venv с pinned-инструментами |
| Канонический gate | Локально FAIL (пять механизмов, AUD-047); серверный CI exact SHA — зелёный (run 35919250552) |
| Мутационный проход | Сплошной, 45 проверок: 43 caught / 2 UNDETECTED; дерево чисто после каждой мутации |
| Артефакты | `manifest.json`, `findings.json`, `gate_mutation_sweep.json`, `self_check.json`, `sha256sums.txt`; SHA-256 в `sha256sums.txt` |

**Ограничения:** gitleaks локально недоступен (опора на CI-лог того же SHA); локальный Python 3.14 вместо CI 3.12; file-role inventory как артефакт и инвентарь непокрытого (7.5.2) не воспроизводились — `NOT_CHECKED` по правилам самопроверки; restore drill не выполнялся. Невошедшая выборка записей реестра перечислена в `manifest.json`. Stop-условий в проверенных данных не выявлено.

## 3. Реестр

| ID | Severity | State | First seen | Review date | Owner | Evidence | Resolution |
|---|---|---|---|---|---|---|---|
| [AUD-047](audit_baseline_2026_09_25.md#aud-047) | high | open | 2026-09-25 | 2026-10-25 | repository_owner | [`manifest.json`](evidence/2026_09_25_completion/manifest.json), [`findings.json`](evidence/2026_09_25_completion/findings.json), [`run_suite.py`](../../operations/scripts/quality/run_suite.py), [`check_coverage.py`](../../operations/scripts/quality/check_coverage.py) | Локальный full gate непроходим на Windows по пяти механизмам; требуется восстановление воспроизводимости и установка hooks. |
| [AUD-048](audit_baseline_2026_09_25.md#aud-048) | medium | open | 2026-09-25 | 2026-10-25 | repository_owner | [`findings.json`](evidence/2026_09_25_completion/findings.json), [`requirements_dev.txt`](../../operations/quality/requirements_dev.txt) | Транзитивный colorama не запинен; `--require-hashes` падает на чистой Windows-установке. |
| [AUD-049](audit_baseline_2026_09_25.md#aud-049) | medium | open | 2026-09-25 | 2026-10-25 | repository_owner | [`gate_mutation_sweep.json`](evidence/2026_09_25_completion/gate_mutation_sweep.json), [`check.py`](../../operations/scripts/documents/check.py) | Мутация `check_owner_interface` не ловится ни одним тестом; нужен negative-path тест. |
| [AUD-050](audit_baseline_2026_09_25.md#aud-050) | medium | open | 2026-09-25 | 2026-10-25 | repository_owner | [`gate_mutation_sweep.json`](evidence/2026_09_25_completion/gate_mutation_sweep.json), [`check_change_scope.py`](../../operations/scripts/tasks/check_change_scope.py) | Мутация `validate_document_metadata` не ловится ни одним тестом; нужен negative-path тест. |
| [AUD-051](audit_baseline_2026_09_25.md#aud-051) | medium | open | 2026-09-25 | 2026-10-25 | repository_owner | [`findings.json`](evidence/2026_09_25_completion/findings.json), [`control.py`](../../src/owner_control/control.py) | `os.kill(pid, 0)` на Windows завершает живой процесс; нужна платформенная проверка живости. |
| [AUD-052](audit_baseline_2026_09_25.md#aud-052) | medium | open | 2026-09-25 | 2026-10-25 | repository_owner | [`findings.json`](evidence/2026_09_25_completion/findings.json), [`milestones.md`](../../milestones.md) | Результат m02 зависит от контролей, назначенных m03; требуется согласование этапов. |
| [AUD-053](audit_baseline_2026_09_25.md#aud-053) | medium | open | 2026-09-25 | 2026-10-25 | repository_owner | [`findings.json`](evidence/2026_09_25_completion/findings.json), [`file_update_dependencies.md`](../../operations/procedures/file_update_dependencies.md), [`acceptance.md`](../../operations/acceptance.md) | Процедура противоречит acceptance-модели и называет несуществующий скрипт; требуется приведение к `apply.py`. |
| [AUD-054](audit_baseline_2026_09_25.md#aud-054) | medium | open | 2026-09-25 | 2026-10-25 | repository_owner | [`findings.json`](evidence/2026_09_25_completion/findings.json), [`acceptance.md`](../../operations/acceptance.md) | Автосоздание `m0X_final_report` описано, но не реализовано; m02 идёт без final_report. |
| [AUD-055](audit_baseline_2026_09_25.md#aud-055) | medium | open | 2026-09-25 | 2026-10-25 | repository_owner | [`findings.json`](evidence/2026_09_25_completion/findings.json), [`task_018_runtime_task_events.md`](../tasks/task_018_runtime_task_events.md) | Карточка `planned` при выполненных шагах и существующей реализации; требуется приведение статуса. |
| [AUD-056](audit_baseline_2026_09_25.md#aud-056) | low | open | 2026-09-25 | 2026-10-25 | repository_owner | [`findings.json`](evidence/2026_09_25_completion/findings.json), [`adr_009_secret_management_strategy.md`](../../adr/adr_009_secret_management_strategy.md) | Число кандидатов ADR_007 устарело; требуется правка формулировки. |
| [AUD-057](audit_baseline_2026_09_25.md#aud-057) | low | open | 2026-09-25 | 2026-10-25 | repository_owner | [`findings.json`](evidence/2026_09_25_completion/findings.json), [`task_015_real_model_provider.md`](../tasks/task_015_real_model_provider.md) | `decides: ADR_005` вне `allowed_paths`; требуется правка карточки при старте. |
| [AUD-058](audit_baseline_2026_09_25.md#aud-058) | low | open | 2026-09-25 | 2026-10-25 | repository_owner | [`findings.json`](evidence/2026_09_25_completion/findings.json), [`setup_precommit.md`](../../operations/setup_precommit.md) | Описание hook расходится с фактическими шагами; требуется сверка. |
| [AUD-059](audit_baseline_2026_09_25.md#aud-059) | low | open | 2026-09-25 | 2026-10-25 | repository_owner | [`findings.json`](evidence/2026_09_25_completion/findings.json), [`sample_task_lifecycle.md`](../../operations/examples/sample_task_lifecycle.md) | Мёртвые ссылки в примере; требуется исправление. |
| [AUD-060](audit_baseline_2026_09_25.md#aud-060) | low | open | 2026-09-25 | 2026-10-25 | repository_owner | [`findings.json`](evidence/2026_09_25_completion/findings.json), [`test_security_extended.py`](../../operations/tests/test_security_extended.py), [`TEST_020`](../tests/test_020.md) | Interim-проверка текста карточки вместо поведения; заменить при реализации TASK_016. |
| [AUD-061](audit_baseline_2026_09_25.md#aud-061) | low | open | 2026-09-25 | 2026-10-25 | repository_owner | [`findings.json`](evidence/2026_09_25_completion/findings.json), [`threat_model.md`](../../specifications/threat_model.md), [`system_specification.md`](../../specifications/system_specification.md) | SEC_CTL_018 продублирован в двух authority-документах; оставить одно каноническое место. |
| [AUD-062](audit_baseline_2026_09_25.md#aud-062) | low | open | 2026-09-25 | 2026-10-25 | repository_owner | [`findings.json`](evidence/2026_09_25_completion/findings.json), [`src/task_state`](../../src/task_state) | Мёртвый API защиты от дубликатов; удалить или задокументировать роль. |
| [AUD-063](audit_baseline_2026_09_25.md#aud-063) | low | open | 2026-09-25 | 2026-10-25 | repository_owner | [`findings.json`](evidence/2026_09_25_completion/findings.json), [`health.py`](../../src/operations/health.py) | `str(exc)` в health JSON; возвращать класс ошибки без текста исключения. |
| [AUD-064](audit_baseline_2026_09_25.md#aud-064) | low | open | 2026-09-25 | 2026-10-25 | repository_owner | [`findings.json`](evidence/2026_09_25_completion/findings.json), [`local_development_windows.md`](../../operations/local_development_windows.md) | Устаревшие статусные упоминания и счётчики тестов; требуется обновление. |
| [AUD-065](audit_baseline_2026_09_25.md#aud-065) | low | open | 2026-09-25 | 2026-10-25 | repository_owner | [`findings.json`](evidence/2026_09_25_completion/findings.json), [`system_specification.md`](../../specifications/system_specification.md), [`business_requirements.md`](../../specifications/business_requirements.md) | SEC_CTL_018/SYS_036 без этапа, BR_025/BR_029 без traces_to; закрыть дыры трассируемости. |
| [AUD-066](audit_baseline_2026_09_25.md#aud-066) | low | open | 2026-09-25 | 2026-10-25 | repository_owner | [`findings.json`](evidence/2026_09_25_completion/findings.json), [`src/observability`](../../src/observability) | Циклический импорт на порядке импортов; разорвать цикл. |
| [AUD-067](audit_baseline_2026_09_25.md#aud-067) | low | open | 2026-09-25 | 2026-10-25 | repository_owner | [`findings.json`](evidence/2026_09_25_completion/findings.json), [`threat_model.md`](../../specifications/threat_model.md) | Модель угроз старше спецификаций; пересмотреть по триггерам. |

## 4. Карточки findings

<a id="aud-047"></a>
### AUD-047 — канонический локальный full gate невоспроизводим на Windows-среде владельца

- **Severity/Confidence/Evidence state:** HIGH / HIGH / CONFIRMED.
- **Baseline:** pre-existing; в AUD-001–046 причина не зарегистрирована — предыдущие аудиты выполнялись на Linux либо помечали локальный gate `UNAVAILABLE`.
- **Файл:** [`run_suite.py`](../../operations/scripts/quality/run_suite.py), [`diagram_lint.py`](../../operations/scripts/documents/diagram_lint.py), [`check_coverage.py`](../../operations/scripts/quality/check_coverage.py), [`test_quality_integration.py`](../../operations/tests/test_quality_integration.py), [`AGENTS.md`](../../AGENTS.md) §3.7; `.gitattributes` отсутствует.
- **Ожидаемый контракт:** AGENTS.md §3.7 требует прогона полного локального gate перед каждой поставкой; команда обязана завершаться успехом на машине владельца.
- **Наблюдаемое поведение:** на изолированном checkout точного SHA: (1) `run_suite.py full` без `PYTHONUTF8=1` падает с `UnicodeEncodeError: 'charmap'` на консоли cp1251; (2) `diagram_render_lint` даёт 10 пиксельных ошибок 10.4–10.9px (порог 12.0px) из-за метрик шрифтов Windows; (3) `ruff format` считает 157/178 файлов неотформатированными из-за CRLF при `core.autocrlf=true` и отсутствии `.gitattributes` (LF-контент через stdin проходит); (4) 2 теста `test_quality_integration.py` падают с `RuntimeError: Git Bash not found at any expected Windows install location` (жёсткий список `C:\Program Files\Git\...`); (5) `check_coverage.py` не находит критические модули в `coverage.json` из-за обратных слэшей в ключах. На том же SHA CI (ubuntu и windows) зелёный.
- **Как воспроизвести:** `git worktree add` на SHA `5713a82f…`, venv из `requirements_dev.txt`, `python operations/scripts/quality/run_suite.py full` на Windows. Машинная запись — [`manifest.json`](evidence/2026_09_25_completion/manifest.json).
- **Воздействие и достижимость:** всё локальное evidence из обязательного цикла §3.7 недостижимо; hooks на машине не установлены, поэтому даже быстрый профиль не исполняется. Поставки опираются только на серверный CI. HIGH, потому что подрывает сам механизм доказательства, а не отдельную проверку.
- **Почему предыдущий аудит пропустил:** предыдущие аудиты не имели локального checkout на Windows и фиксировали gate как `UNAVAILABLE`, а не как проверяемый.
- **Рекомендованное исправление:** добавить `.gitattributes` с нормализацией eol; нормализовать пути в `check_coverage.py`; искать Git Bash через PATH/реестр вместо фиксированных путей; сделать пиксельные пороги `diagram_lint` кроссплатформенными; выставлять `PYTHONUTF8=1` внутри `run_suite.py` или задокументировать в §3.7; установить hooks по [`setup_precommit.md`](../../operations/setup_precommit.md) и [`pre_push_validation.md`](../../operations/quality/playbooks/pre_push_validation.md).
- **Как проверить исправление:** `python operations/scripts/quality/run_suite.py full` зелёный на чистой Windows-машине без переменных-обходов; pre-commit и pre-push hooks установлены и исполняются.
- **Критерий закрытия:** зелёный локальный full gate на Windows на одном точном SHA с серверным CI; ссылка на evidence в реестре.

<a id="aud-048"></a>
### AUD-048 — lock разработки не пинит Windows-транзитивный colorama

- **Severity/Confidence/Evidence state:** MEDIUM / HIGH / CONFIRMED.
- **Baseline:** pre-existing; в AUD-001–046 причина не зарегистрирована (AUD-040 касался лицензионной политики, не полноты lock).
- **Файл:** [`requirements_dev.txt`](../../operations/quality/requirements_dev.txt).
- **Ожидаемый контракт:** установка с `--require-hashes` обязана проходить на поддерживаемых платформах.
- **Наблюдаемое поведение:** `bandit` тянет `colorama` с маркером `platform_system=="Windows"`; в lock его нет, и `pip install --require-hashes` падает на чистой Windows-установке. CI Windows проходит только потому, что colorama 0.4.6 предустановлен в образе runner'а (лог job Windows validation, run 35504462050).
- **Как воспроизвести:** чистый venv на Windows, `pip install --require-hashes -r operations/quality/requirements_dev.txt`.
- **Воздействие и достижимость:** установка инструментов качества невозможна без ручного обхода; любой новый агент на Windows упирается в это на первом шаге §3.7.
- **Рекомендованное исправление:** перегенерировать lock на Windows или добавить `colorama` с хэшем явно.
- **Как проверить исправление:** установка в чистом venv на Windows завершается успешно.
- **Критерий закрытия:** воспроизведённая установка + зелёный CI на том же SHA.

<a id="aud-049"></a>
### AUD-049 — check_owner_interface обезвреживается незаметно

- **Severity/Confidence/Evidence state:** MEDIUM / HIGH / CONFIRMED.
- **Baseline:** pre-existing; в AUD-001–046 причина не зарегистрирована.
- **Файл:** [`check.py`](../../operations/scripts/documents/check.py), функция `check_owner_interface`.
- **Ожидаемый контракт:** каждая проверка gate обязана физически уметь краснеть при нарушении (AGENTS.md §5, раздел 4.5 промпта аудита).
- **Наблюдаемое поведение:** мутационная проба (тело функции заменено на возврат пустого результата) не вызывает падения ни одного теста — машинная запись [`gate_mutation_sweep.json`](evidence/2026_09_25_completion/gate_mutation_sweep.json).
- **Как воспроизвести:** заменить тело `check_owner_interface` на `_result("owner_interface", [])` и прогнать `run_unittests.py`: новых падений нет.
- **Воздействие и достижимость:** проверку можно удалить или сломать без видимого сигнала; зелёный gate не доказывает её работоспособность.
- **Рекомендованное исправление:** добавить negative-path тест, подающий нарушение owner-interface и ожидающий отказ.
- **Как проверить исправление:** повторная мутация даёт `caught`.
- **Критерий закрытия:** тест краснеет на обезвреженной проверке и зеленеет на исправной; CI на том же SHA.

<a id="aud-050"></a>
### AUD-050 — validate_document_metadata обезвреживается незаметно

- **Severity/Confidence/Evidence state:** MEDIUM / HIGH / CONFIRMED.
- **Baseline:** pre-existing; в AUD-001–046 причина не зарегистрирована.
- **Файл:** [`check_change_scope.py`](../../operations/scripts/tasks/check_change_scope.py), функция `validate_document_metadata`.
- **Ожидаемый контракт:** контроль честности даты `updated` и версий authority-документов обязан фальсифицироваться тестами.
- **Наблюдаемое поведение:** мутационная проба не вызывает падения ни одного теста — [`gate_mutation_sweep.json`](evidence/2026_09_25_completion/gate_mutation_sweep.json).
- **Как воспроизвести:** заменить тело функции на `return []` и прогнать `run_unittests.py`: новых падений нет.
- **Воздействие и достижимость:** контроль честности метаданных документов может silently перестать работать.
- **Рекомендованное исправление:** добавить negative-path тест с поддельной датой/версией.
- **Как проверить исправление:** повторная мутация даёт `caught`.
- **Критерий закрытия:** тест краснеет на обезвреженной проверке; CI на том же SHA.

<a id="aud-051"></a>
### AUD-051 — _process_is_alive убивает живой процесс на Windows

- **Severity/Confidence/Evidence state:** MEDIUM / HIGH / CONFIRMED.
- **Baseline:** pre-existing; смежная AUD-013 вводила сам recovery с отказом при живом PID, но не платформенную семантику проверки живости.
- **Файл:** [`control.py`](../../src/owner_control/control.py), строки 216–225; runbook [`recover_stale_sensitive_action_lock.md`](../../operations/procedures/recover_stale_sensitive_action_lock.md).
- **Ожидаемый контракт:** проверка живости держателя sensitive-action lock не имеет побочных эффектов.
- **Наблюдаемое поведение:** `_process_is_alive` вызывает `os.kill(pid, 0)`. На Windows `os.kill` с любым сигналом, кроме CTRL_C/CTRL_BREAK, вызывает `TerminateProcess` — «проверка» завершает живой процесс держателя лока.
- **Как воспроизвести:** на Windows вызвать `_process_is_alive(pid)` для живого процесса: процесс завершается с кодом 0.
- **Воздействие и достижимость:** runbook восстановления лока на Windows убьёт живой держателей процесс — прямо противоположно fail-closed назначению. Достижимо при любом восстановлении лока на Windows.
- **Рекомендованное исправление:** платформенная проверка живости (`OpenProcess`/`WaitForSingleObject` на Windows, `kill(pid, 0)` на POSIX).
- **Как проверить исправление:** unit-тест: живой процесс переживает проверку на Windows, мёртвый PID распознаётся.
- **Критерий закрытия:** тест + CI на том же SHA.

<a id="aud-052"></a>
### AUD-052 — результат m02 зависит от контролей, назначенных m03

- **Severity/Confidence/Evidence state:** MEDIUM / HIGH / CONFIRMED.
- **Baseline:** pre-existing; в AUD-001–046 причина не зарегистрирована.
- **Файл:** [`milestones.md`](../../milestones.md), строки 83, 89, 116.
- **Ожидаемый контракт:** результат этапа покрывается контролями того же или более раннего этапа.
- **Наблюдаемое поведение:** результат m02 (подэтап 6, строка 89) требует работающий VPN/обязательный сетевой путь, но SEC_CTL_010 и INF_REQ_004/005 отнесены к составу m03 (строка 116), а не m02 (строка 83).
- **Как воспроизвести:** сверка состава m02 и m03 в `milestones.md` с результатом подэтапа 6.
- **Воздействие и достижимость:** приёмка m02 потребует незапланированных контролей или будет принята без них; планирование трассируемости искажено.
- **Рекомендованное исправление:** перенести соответствующие контроли в состав m02 либо переформулировать результат m02.
- **Как проверить исправление:** `check_full_traceability` и ручная сверка: каждый результат этапа покрыт его контролями.
- **Критерий закрытия:** согласованные этапы + зелёный gate на том же SHA.

<a id="aud-053"></a>
### AUD-053 — file_update_dependencies противоречит acceptance-модели

- **Severity/Confidence/Evidence state:** MEDIUM / HIGH / CONFIRMED.
- **Baseline:** pre-existing; в AUD-001–046 причина не зарегистрирована.
- **Файл:** [`file_update_dependencies.md`](../../operations/procedures/file_update_dependencies.md), строки 24, 32, 69; [`acceptance.md`](../../operations/acceptance.md).
- **Ожидаемый контракт:** переходы `work_state` выполняются только через `apply.py`; владелец не редактирует состояние вручную (AGENTS.md §5).
- **Наблюдаемое поведение:** процедура требует от владельца вручную менять `work_state` этапа (строки 24, 32) и называет скрипт `acceptance.py` вместо `apply.py` (строка 69).
- **Как воспроизвести:** чтение процедуры и acceptance.md на проверяемом SHA.
- **Воздействие и достижимость:** следование процедуре ведёт к обходу acceptance-механизма и несуществующему скрипту.
- **Рекомендованное исправление:** привести текст к acceptance.md: переходы только через `apply.py`, исправить имя скрипта.
- **Как проверить исправление:** процедура не содержит ручных переходов; ссылки разрешаются.
- **Критерий закрытия:** зелёный gate (links + document policy) на том же SHA.

<a id="aud-054"></a>
### AUD-054 — описанное автосоздание m0X_final_report не реализовано

- **Severity/Confidence/Evidence state:** MEDIUM / HIGH / CONFIRMED.
- **Baseline:** pre-existing; в AUD-001–046 причина не зарегистрирована.
- **Файл:** [`acceptance.md`](../../operations/acceptance.md), [`file_update_dependencies.md`](../../operations/procedures/file_update_dependencies.md); каталог [`work/acceptance`](../acceptance).
- **Ожидаемый контракт:** шаги, существующие в документации как автоматические, существуют и исполняемы.
- **Наблюдаемое поведение:** процедуры описывают автоматическое создание `m0X_final_report` при старте этапа; автоматики нет — m02 `in-progress`, а `work/acceptance/m02_final_report.md` отсутствует.
- **Как воспроизвести:** сверка текста процедур с содержимым `work/acceptance/` и кодом `apply.py`.
- **Воздействие и достижимость:** acceptance-поток m02 идёт без обязательного артефакта; документация описывает несуществующее поведение.
- **Рекомендованное исправление:** реализовать создание final_report в `apply.py` либо убрать обещание автоматики из процедур.
- **Как проверить исправление:** старт этапа создаёт final_report, либо процедуры не обещают автоматику.
- **Критерий закрытия:** поведенческое подтверждение + CI на том же SHA.

<a id="aud-055"></a>
### AUD-055 — TASK_018 рассинхронизирована с фактическим состоянием

- **Severity/Confidence/Evidence state:** MEDIUM / HIGH / CONFIRMED.
- **Baseline:** pre-existing; в AUD-001–046 причина не зарегистрирована.
- **Файл:** [`task_018_runtime_task_events.md`](../tasks/task_018_runtime_task_events.md); [`task_events.py`](../../src/observability/task_events.py).
- **Ожидаемый контракт:** `work_state` карточки отражает фактическое состояние работы.
- **Наблюдаемое поведение:** карточка имеет `work_state: planned`, но все шаги отмечены `[x]`, а реализация (`task_events.py`) и тесты существуют на проверяемом SHA.
- **Как воспроизвести:** сверка карточки с деревом и историей.
- **Воздействие и достижимость:** покрытие путей TASK и статус-дашборд искажаются; следующий агент может начать уже выполненную работу.
- **Рекомендованное исправление:** привести `work_state` к фактическому состоянию по процедуре завершения TASK.
- **Как проверить исправление:** карточка отражает факт; gate подтверждает.
- **Критерий закрытия:** зелёный gate на том же SHA.

<a id="aud-056"></a>
### AUD-056 — устаревшее число кандидатов ADR_007 в ADR_009

- **Severity/Confidence/Evidence state:** LOW / HIGH / CONFIRMED.
- **Baseline:** pre-existing.
- **Файл:** [`adr_009_secret_management_strategy.md`](../../adr/adr_009_secret_management_strategy.md), строка 45.
- **Наблюдаемое поведение:** текст говорит о «трёх реальных кандидатах ADR_007»; в [`adr_007_cloud_provider_selection.md`](../../adr/adr_007_cloud_provider_selection.md) уже четыре кандидата (добавлен OVHcloud).
- **Воздействие:** читатель получает неверное представление о фактическом решении.
- **Рекомендованное исправление:** обновить число или убрать счётчик в пользу ссылки.
- **Критерий закрытия:** формулировка совпадает с ADR_007; зелёный gate.

<a id="aud-057"></a>
### AUD-057 — TASK_015 decides ADR_005 вне allowed_paths

- **Severity/Confidence/Evidence state:** LOW / HIGH / CONFIRMED.
- **Baseline:** pre-existing.
- **Файл:** [`task_015_real_model_provider.md`](../tasks/task_015_real_model_provider.md), строки 14–16.
- **Наблюдаемое поведение:** карточка объявляет `decides: ADR_005`, но [`adr_005_first_model_provider_selection.md`](../../adr/adr_005_first_model_provider_selection.md) не входит в `allowed_paths` — при старте работы актуализировать ADR будет нельзя без правки карточки.
- **Воздействие:** блокировка в момент старта TASK_015 либо соблазн обойти покрытие путей.
- **Рекомендованное исправление:** добавить ADR_005 в `allowed_paths` при старте TASK_015.
- **Критерий закрытия:** `allowed_paths` покрывает все обязательные к изменению файлы; зелёный gate.

<a id="aud-058"></a>
### AUD-058 — setup_precommit расходится с фактическим hook

- **Severity/Confidence/Evidence state:** LOW / HIGH / CONFIRMED.
- **Baseline:** pre-existing.
- **Файл:** [`setup_precommit.md`](../../operations/setup_precommit.md); [`pre_commit_hook.sh`](../../operations/hooks/pre_commit_hook.sh).
- **Наблюдаемое поведение:** документ описывает «three top-level steps» при фактических пяти шагах hook'а, заявляет «0.5–1 second» без основания и даёт bash-команды без указания исполнителя на Windows.
- **Воздействие:** установка по инструкции даёт неверные ожидания; на Windows-среде владельца команды не запускаются напрямую.
- **Рекомендованное исправление:** сверить число шагов с hook'ом, убрать недостоверную оценку времени, указать Git Bash.
- **Критерий закрытия:** описание совпадает с фактическим hook'ом.

<a id="aud-059"></a>
### AUD-059 — мёртвые ссылки в sample_task_lifecycle

- **Severity/Confidence/Evidence state:** LOW / HIGH / CONFIRMED.
- **Baseline:** pre-existing.
- **Файл:** [`sample_task_lifecycle.md`](../../operations/examples/sample_task_lifecycle.md).
- **Наблюдаемое поведение:** ссылки на несуществующий раздел [`procedure_map.md`](../../operations/procedure_map.md) и отсутствующий каталог `work/evidence/`.
- **Воздействие:** пример — учебная точка входа — ведёт в несуществующие места.
- **Рекомендованное исправление:** исправить или удалить ссылки.
- **Критерий закрытия:** links-проверка зелёная для файла.

<a id="aud-060"></a>
### AUD-060 — TEST_020 проверяет текст карточки вместо поведения

- **Severity/Confidence/Evidence state:** LOW / HIGH / CONFIRMED.
- **Baseline:** pre-existing; в [`TEST_020`](../tests/test_020.md) честно оговорено как interim до реализации TASK_016.
- **Файл:** [`test_security_extended.py`](../../operations/tests/test_security_extended.py), строки 210–220.
- **Наблюдаемое поведение:** «security-контракт» webhook-аутентификации проверяется `assertIn` фраз в тексте карточки TASK_016 — структурная, а не поведенческая гарантия.
- **Воздействие:** формулировку можно изменить или удалить смысл, сохранив фразы; защита не доказана.
- **Рекомендованное исправление:** при реализации TASK_016 заменить поведенческой проверкой (spoofed-owner-id на живом ingress/polling).
- **Критерий закрытия:** поведенческий тест отклоняет поддельный update; CI на том же SHA.

<a id="aud-061"></a>
### AUD-061 — SEC_CTL_018 продублирован в двух authority-документах

- **Severity/Confidence/Evidence state:** LOW / HIGH / CONFIRMED.
- **Baseline:** pre-existing.
- **Файл:** [`threat_model.md`](../../specifications/threat_model.md), строка 234; [`system_specification.md`](../../specifications/system_specification.md), строка 574.
- **Наблюдаемое поведение:** факт о защите ветки main записан в обоих документах — пара способна разойтись.
- **Рекомендованное исправление:** оставить факт в одном документе, из второго ссылаться.
- **Критерий закрытия:** единственное каноническое место для SEC_CTL_018.

<a id="aud-062"></a>
### AUD-062 — мёртвый API защиты от дубликатов в task_state

- **Severity/Confidence/Evidence state:** LOW / HIGH / CONFIRMED.
- **Baseline:** pre-existing.
- **Файл:** [`src/task_state`](../../src/task_state).
- **Наблюдаемое поведение:** `has_executed`/`mark_executed` нигде не вызываются; реальная защита от дубликатов — OwnerControlGate. Параллельный мёртвый механизм вводит в заблуждение о том, где живёт контроль.
- **Рекомендованное исправление:** удалить мёртвый API либо задокументировать его роль.
- **Критерий закрытия:** поиск вызовов и Vulture подтверждают отсутствие мёртвого кода; CI зелёный.

<a id="aud-063"></a>
### AUD-063 — health JSON раскрывает текст исключений

- **Severity/Confidence/Evidence state:** LOW / HIGH / CONFIRMED.
- **Baseline:** pre-existing.
- **Файл:** [`health.py`](../../src/operations/health.py), строка 77.
- **Наблюдаемое поведение:** в `detail` кладётся `str(exc)` — внутренние сообщения исключений уходят наружу через health-ответ.
- **Рекомендованное исправление:** возвращать класс ошибки без текста исключения.
- **Критерий закрытия:** тест: `detail` не содержит `str(exc)`; CI зелёный.

<a id="aud-064"></a>
### AUD-064 — устаревшие статусные упоминания и счётчики тестов

- **Severity/Confidence/Evidence state:** LOW / MEDIUM / CONFIRMED.
- **Baseline:** pre-existing.
- **Файл:** [`local_development_windows.md`](../../operations/local_development_windows.md), строка 31; [`adr_lifecycle.md`](../../operations/lifecycle/adr_lifecycle.md) §9; [`task_001`](../tasks/task_001_contract_and_harness.md), [`task_002`](../tasks/task_002_task_state.md), [`task_005`](../tasks/task_005_arc_005.md), [`task_012`](../tasks/task_012_owner_control.md); [`test_007.md`](../tests/test_007.md).
- **Наблюдаемое поведение:** `local_development_windows.md` считает m01 незавершённым (он `completed`); §9 adr_lifecycle частично устарел; счётчики тестов в карточках TASK не совпадают с фактическими; TEST_007 имеет нестандартный H1.
- **Воздействие:** статусные документы систематически отстают; доверие к навигации снижается.
- **Рекомендованное исправление:** обновить упоминания и счётчики; привести TEST_007 к шаблону.
- **Критерий закрытия:** упоминания совпадают с [`project_status.md`](../../project_status.md) и фактическим числом тестов.

<a id="aud-065"></a>
### AUD-065 — дыры планирования трассируемости

- **Severity/Confidence/Evidence state:** LOW / MEDIUM / CONFIRMED.
- **Baseline:** pre-existing.
- **Файл:** [`system_specification.md`](../../specifications/system_specification.md) (SEC_CTL_018, SYS_036); [`business_requirements.md`](../../specifications/business_requirements.md) (BR_025, BR_029).
- **Наблюдаемое поведение:** SEC_CTL_018 и SYS_036 не назначены ни одному этапу; BR_025 и BR_029 не имеют `traces_to`.
- **Воздействие:** контроль и требования без плана поставки могут остаться нереализованными незаметно.
- **Рекомендованное исправление:** назначить этап или явно зафиксировать отложенность; добавить `traces_to`.
- **Критерий закрытия:** `check_full_traceability` покрывает все ID; gate зелёный.

<a id="aud-066"></a>
### AUD-066 — циклический импорт держится на порядке импортов

- **Severity/Confidence/Evidence state:** LOW / MEDIUM / CONFIRMED.
- **Baseline:** pre-existing.
- **Файл:** [`src/observability`](../../src/observability), [`src/operations`](../../src/operations), [`src/task_state`](../../src/task_state).
- **Наблюдаемое поведение:** цикл observability → operations → task_state разрешается только текущим порядком импортов; хрупко при рефакторинге.
- **Рекомендованное исправление:** разорвать цикл, вынеся общий контракт в отдельный модуль.
- **Критерий закрытия:** граф импортов ацикличен; mypy и тесты зелёные.

<a id="aud-067"></a>
### AUD-067 — модель угроз старше спецификаций

- **Severity/Confidence/Evidence state:** LOW / MEDIUM / CONFIRMED.
- **Baseline:** pre-existing.
- **Файл:** [`threat_model.md`](../../specifications/threat_model.md); [`threat_review_triggers.md`](../../operations/policy/threat_review_triggers.md).
- **Наблюдаемое поведение:** модель угроз датирована 2026-08-24 и старше всех спецификаций; триггеры пересмотра существуют в отдельном policy, но изменения спецификаций (TASK_018 events, owner control) не привели к обновлению модели.
- **Воздействие:** решения по угрозам могут опираться на устаревшую модель.
- **Рекомендованное исправление:** пересмотреть threat_model по триггерам и обновить дату либо явно зафиксировать, что пересмотр проведён без изменений.
- **Критерий закрытия:** `updated` threat_model не старше последнего релевантного изменения спецификаций либо есть запись о пересмотре.
