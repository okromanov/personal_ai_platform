---
id: audit_baseline
type: audit_register
document_state: current
version: 1.1
updated: 2026-08-28
depends_on: []
---

# Реестр результатов аудита

## 1. Назначение

Это единственный реестр стабильных идентификаторов `AUD-NNN`, состояния исправлений и формально принятых рисков. Новый аудит сопоставляет причину с существующим ID до создания следующего номера. Состояние `accepted_risk` допустимо только после явного решения владельца; отсутствие такого решения оставляет finding открытой.

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

## 5. Правило обновления

После зелёного `Project check` на точном SHA записи исправленных findings переводятся в `resolved` отдельным служебным PR. Для `accepted_risk` обязательно сохраняются явное решение владельца, ответственный, срок пересмотра и компенсирующий контроль. Удаление строк запрещено: закрытая finding остаётся историей baseline.
