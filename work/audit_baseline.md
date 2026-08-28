---
id: audit_baseline
type: audit_register
document_state: current
version: 1.0
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
| AUD-001 | high | remediated_pending_verification | 2026-08-27 | 2026-09-02 | repository_owner | [`.github/workflows/project_check.yml`](../.github/workflows/project_check.yml) | Удалён отдельный write-capable workflow; health evidence остаётся SHA-bound Actions artifact. |
| AUD-002 | medium | remediated_pending_verification | 2026-08-27 | 2026-09-02 | repository_owner | [`pre_commit_hook.sh`](../operations/hooks/pre_commit_hook.sh), [`test_quality_integration.py`](../operations/tests/test_quality_integration.py) | Регенерация стала blocking; post-mutation fast gate и negative test исключают fail-open. |
| AUD-003 | medium | remediated_pending_verification | 2026-08-27 | 2026-09-02 | repository_owner | [`dockerfile`](../dockerfile), [`project_check.yml`](../.github/workflows/project_check.yml) | Base image закреплён digest; CI выполняет build/run/health и создаёт SBOM. |
| AUD-004 | medium | remediated_pending_verification | 2026-08-27 | 2026-09-02 | repository_owner | [`state_io.py`](../src/owner_control/state_io.py), [`test_owner_control.py`](../operations/tests/product/test_owner_control.py) | После replace выполняется POSIX directory fsync; отказ durability barrier распространяется вызывающему коду. |
| AUD-005 | low | remediated_pending_verification | 2026-08-27 | 2026-09-02 | repository_owner | [`run_suite.py`](../operations/scripts/quality/run_suite.py), [`test_quality_runner.py`](../operations/tests/tooling/test_quality_runner.py) | Каждый шаг gate ограничен 300 секундами и выдаёт локализованную ошибку timeout. |
| AUD-006 | low | remediated_pending_verification | 2026-08-27 | 2026-09-02 | repository_owner | [Раздел 3](#3-реестр), [`run_suite.py`](../operations/scripts/quality/run_suite.py) | Реестр создан; gate проверяет ID, состояния, owner и review date. |

## 4. Правило обновления

После зелёного `Project check` на точном SHA записи исправленных findings переводятся в `resolved` отдельным служебным PR. Для `accepted_risk` обязательно сохраняются явное решение владельца, ответственный, срок пересмотра и компенсирующий контроль. Удаление строк запрещено: закрытая finding остаётся историей baseline.
