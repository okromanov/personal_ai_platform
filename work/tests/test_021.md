---
id: TEST_021
type: test
spec_state: current
execution: automated
version: 1.0
updated: 2026-09-27
traces_to:
  - TASK_019
verifies:
  - SEC_CTL_010
  - SEC_CTL_018
accepts:
  - m02
automated_evidence: project_checks
---

# TEST_021 — Покрытие SEC_CTL_010 и SEC_CTL_018 на m02

## 1. Назначение

Подтвердить, что меры [`SEC_CTL_010`](../../specifications/system_specification.md#sec_ctl_010) и [`SEC_CTL_018`](../../specifications/system_specification.md#sec_ctl_018), включённые в состав [`m02`](../../milestones.md#m02), имеют TEST-спецификацию, принимающую этот этап.

## 2. Что проверяется

- [`SEC_CTL_010`](../../specifications/system_specification.md#sec_ctl_010) «Явная сетевая политика» декларирован в scope [`m02`](../../milestones.md#m02).
- [`SEC_CTL_018`](../../specifications/system_specification.md#sec_ctl_018) «Защита от саморасширения автоматизации» декларирован в scope [`m02`](../../milestones.md#m02).
- Оба контроля покрыты настоящей TEST-спецификацией через [`verifies`](../../operations/change_process.md) и [`accepts: m02`](../../milestones.md#m02).

## 3. Автоматический запуск

Полный project check (`operations/scripts/quality/run_suite.py full`) вызывает [`test_coverage.py`](../../operations/scripts/quality/test_coverage.py), который для текущего этапа [`m02`](../../milestones.md#m02) проверяет, что каждое тестируемое требование из `scope` имеет TEST с `accepts: m02`. Никаких действий владельца не требуется.

## 4. Критерий успеха

Gate не сообщает, что [`SEC_CTL_010`](../../specifications/system_specification.md#sec_ctl_010) или [`SEC_CTL_018`](../../specifications/system_specification.md#sec_ctl_018) не покрыты TEST, который accepts [`m02`](../../milestones.md#m02).

## 5. Состав доказательства

- `project_checks` — запись полного project check на точном Git SHA.
