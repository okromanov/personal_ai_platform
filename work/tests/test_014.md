---
id: TEST_014
type: test
title: "INF_CMP_001 — Вычислительная среда выполнения: health-check CLI и структура образа"
spec_state: current
execution: automated
automated_evidence: quality_suite
version: 1.0
updated: 2026-08-25
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

Доказать, что вычислительная среда выполнения ([`INF_CMP_001`](../../specifications/infrastructure_baseline.md#inf_cmp_001)) даёт воспроизводимый цикл запуска и проверки работоспособности, работает без административных полномочий и несёт идентифицируемую версию — без реальной сборки Docker-образа, недоступной в этой среде разработки.

## 2. Что проверяется

Реализация `health_check.py` (`src/operations/health_check.py`) и структура корневого [`Dockerfile`](../../Dockerfile):

- CLI `health_check.main()` возвращает код `0` и отчёт `healthy: true`, если ни одна проверка не зарегистрирована (на [`m02`](../../milestones.md#m02) нет живой внешней зависимости для проверки).
- Возвращает код `1` и `healthy: false`, если зарегистрированная проверка нездорова — согласовано с `HealthAggregator` ([`TASK_007`](../tasks/task_007_arc_009.md)).
- Отчёт называет версию из переменной окружения `APP_VERSION` (баз в образ на этапе сборки) или `"unknown"`, если не задана — [`INF_REQ_010`](../../specifications/infrastructure_baseline.md#inf_req_010).
- `Dockerfile` закрепляет базовый образ на конкретную поддерживаемую версию Python, объявляет непривилегированного пользователя приложения, `HEALTHCHECK`, вызывающий эту CLI, и аргумент сборки `APP_VERSION`.
- `.dockerignore` исключает `.git` и кеши сборки Python из контекста образа.

## 3. Автоматический запуск

Часть канонического прогона юнит-тестов, выполняется в `Quality skills` на каждом push/PR:

```bash
python3 operations/scripts/quality/run_unittests.py
```

Отдельный прогон только этого компонента:

```bash
python3 -m unittest operations.tests.product.test_compute_environment -v
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

`automated_evidence: quality_suite`. Каждый запуск канонического набора юнит-тестов создаёт доказательство выполнения всех 10 тестов на текущем Git SHA. Результат успеха фиксируется в evidence записи с временем выполнения и версией платформы.

**Известный пробел (задокументирован, не скрыт):** реальный `docker build` корневого `Dockerfile` не выполнялся ни в этой среде разработки (нет запущенного демона Docker), ни в CI (минуты GitHub Actions исчерпаны, автоматический запуск недоступен). Автоматизированное доказательство здесь ограничено статической структурой `Dockerfile` и поведением CLI без контейнера. Практическая воспроизводимость сборки должна быть подтверждена владельцем или следующим прогоном CI на Ubuntu-раннере (там демон Docker доступен по умолчанию).

## 6. Реализованные компоненты

### Компонент: Вычислительная среда выполнения

**Данные**: JSON-отчёт `health_check.main()` — `healthy`, `version`, `dependencies`

**Реализация**: `src/operations/health_check.py` — тонкий CLI-адаптер поверх `HealthAggregator` ([`TASK_007`](../tasks/task_007_arc_009.md)), вызываемый `Dockerfile`'ом как `HEALTHCHECK` и как команда по умолчанию. `Dockerfile` — закреплённый образ `python:3.12-slim`, непривилегированный пользователь `app`, аргумент сборки `APP_VERSION`.

## 7. Структура кода

```
src/operations/
└── health_check.py — CLI: build_health_aggregator(), main()

Dockerfile — вычислительная среда (корень репозитория)
.dockerignore — исключения контекста сборки

operations/tests/product/
└── test_compute_environment.py — юнит-тесты, часть канонического run_unittests.py (CI/CD)
```

## 8. Соответствие требованиям

| Требование | Статус | Примечание |
|---|---|---|
| [`INF_REQ_001`](../../specifications/infrastructure_baseline.md#inf_req_001): Поддерживаемая и воспроизводимая рабочая среда | ✅ | Закреплённая версия базового образа, `HEALTHCHECK`; реальная сборка образа — известный пробел (см. §5) |
| [`INF_REQ_002`](../../specifications/infrastructure_baseline.md#inf_req_002): Разделение административных и прикладных полномочий | ✅ | Непривилегированный пользователь `app`, подтверждено статическим тестом структуры `Dockerfile` |
| [`INF_REQ_010`](../../specifications/infrastructure_baseline.md#inf_req_010): Идентифицируемая версия развёртывания | ✅ | `APP_VERSION` встроен в образ на этапе сборки, отражается в отчёте `health_check` |
| [`INF_REQ_015`](../../specifications/infrastructure_baseline.md#inf_req_015): Разделение среды разработки и рабочей среды | ➖ | Задокументировано прямо в `Dockerfile` (локальный прогон тестов не подтверждает рабочий контур); механической проверки нет — политика, а не код |

## 9. Доказательства

- **Исходный код**: [`src/operations/health_check.py`](../../src/operations/health_check.py), [`Dockerfile`](../../Dockerfile), [`.dockerignore`](../../.dockerignore)
- **Тесты**: 10 юнит-тестов в [`operations/tests/product/test_compute_environment.py`](../../operations/tests/product/test_compute_environment.py), часть обязательного gate `Quality skills`
- **Отсутствие регрессий**: Запуск `check.py --all` прошёл успешно

## 10. Готово когда

- ✅ 10 тестов пройдено
- ✅ `health_check.py` согласован с `HealthAggregator` ([`TASK_007`](../tasks/task_007_arc_009.md))
- ✅ `Dockerfile` статически подтверждает непривилегированного пользователя, закреплённый образ, `HEALTHCHECK`, идентифицируемую версию
- ⚠️ Реальная сборка Docker-образа не проверена (см. §5) — ожидает подтверждения владельцем или CI

## 11. Что будет дальше

[`TASK_009`](../tasks/task_009_inf_002.md) реализует Сеть и контролируемый исходящий трафик ([`INF_CMP_002`](../../specifications/infrastructure_baseline.md#inf_cmp_002)).

## 12. Примечания для разработчика

- `health_check.py` не регистрирует ни одной реальной проверки зависимости: на [`m02`](../../milestones.md#m02) нет постоянно работающего процесса с живой внешней зависимостью (канал и шлюзы моделей/инструментов ещё не соединены в цикл). Регистрация реальных проверок — задача той будущей работы, которая свяжет компоненты в единый процесс.
- Образ намеренно не содержит специфики облачного провайдера ([`ADR_007`](../../adr/adr_007_cloud_provider_selection.md)) или SDK среды агента ([`ADR_006`](../../adr/adr_006_agent_environment_framework.md)) — оба решения остаются `proposed`.

Действия владельца не требуются: тест полностью автоматизирован, но §5/§10 отмечают пробел (сборка образа не проверена), требующий подтверждения владельцем при следующей возможности запустить CI или Docker.
