---
id: TEST_014
type: test
title: "INF_CMP_001 — Вычислительная среда выполнения: health-check CLI и структура образа"
spec_state: current
execution: automated
automated_evidence: quality_suite
version: 1.3
updated: 2026-09-04
accepts:
  - m02
traces_to:
  - TASK_008
  - INF_REQ_001
  - INF_REQ_002
  - INF_REQ_010
depends_on:
  - TEST_013
---

# TEST_014 — Вычислительная среда выполнения: health-check CLI и структура образа

Автоматическая проверка. Действия владельца не требуются.

## 1. Назначение

Доказать, что вычислительная среда выполнения ([`INF_CMP_001`](../../specifications/infrastructure_baseline.md#inf_cmp_001)) даёт воспроизводимый цикл запуска и проверки работоспособности, работает без административных полномочий и несёт идентифицируемую версию. Серверный Project check дополнительно собирает и запускает Docker-образ.

## 2. Что проверяется

Реализация `health_check.py` (`src/operations/health_check.py`) и структура корневого [`dockerfile`](../../dockerfile):

- CLI `health_check.main()` возвращает код `0` и отчёт `healthy: true`, если ни одна проверка не зарегистрирована (на [`m02`](../../milestones.md#m02) нет живой внешней зависимости для проверки).
- Возвращает код `1` и `healthy: false`, если зарегистрированная проверка нездорова — согласовано с `HealthAggregator` ([`TASK_007`](../tasks/task_007_arc_009.md)).
- Отчёт называет версию из переменной окружения `APP_VERSION` (баз в образ на этапе сборки) или `"unknown"`, если не задана — [`INF_REQ_010`](../../specifications/infrastructure_baseline.md#inf_req_010).
- `dockerfile` закрепляет базовый образ на конкретную поддерживаемую версию Python, объявляет непривилегированного пользователя приложения, `HEALTHCHECK`, вызывающий эту CLI, и аргумент сборки `APP_VERSION`.
- `.dockerignore` исключает `.git` и кеши сборки Python из контекста образа.

## 3. Автоматический запуск

Часть канонического прогона юнит-тестов, выполняется в `Quality skills` на каждом push/PR:

```bash
python3.12 operations/scripts/quality/run_unittests.py
```

Отдельный прогон только этого компонента:

```bash
python3.12 -m unittest operations.tests.product.test_compute_environment -v
```

## 4. Критерий успеха

Все 10 тестов проходят, включая сценарии:

- ✓ build_health_aggregator_returns_an_aggregator
- ✓ main_exits_zero_and_reports_healthy_with_no_registered_checks
- ✓ main_exits_nonzero_when_a_registered_check_is_unhealthy
- ✓ main_reports_the_app_version_from_the_environment / main_reports_unknown_version_when_unset
- ✓ base_image_is_pinned_to_a_supported_python_version
- ✓ runs_as_a_non_root_application_user
- ✓ declares_a_health_check
- ✓ accepts_an_identifiable_version_build_argument
- ✓ dockerignore_excludes_version_control_and_caches

## 5. Состав доказательства

`automated_evidence: quality_suite`. Локальный suite фиксирует десять unit-тестов на текущем Git SHA. Серверный Project check отдельно выполняет Docker build/run, health probe, фиксирует digest образа и создаёт SBOM; локальное доказательство не подменяет этот CI-результат.
