---
id: TASK_008
type: task
title: Реализация INF_CMP_001
component: INF_CMP_001
work_state: completed
version: 2.7
updated: 2026-09-03
next_actor: none
owner_action: none
owner_followups: []
depends_on:
  - TASK_007
allowed_paths:
  - work/tasks/task_008_inf_001.md
  - dockerfile
  - .dockerignore
  - src/operations/health_check.py
  - src/operations/__init__.py
  - operations/tests/product/test_compute_environment.py
  - work/tests/test_014.md
traces_to:
  - m02
implements:
  - INF_CMP_001
tests:
  - TEST_014
---

# TASK_008 — Реализация INF_CMP_001

## 1. Зачем это делаем

Определить и задокументировать вычислительную среду выполнения — физическую или виртуальную среду, в которой работают сервисы платформы и выбранная реализация среды агента (`RuntimePort` из [`TASK_003`](task_003_arc_003.md)). Без явного описания среды выполнения архитектурные компоненты ([`ARC_CMP_001`](../../specifications/architecture_baseline.md#arc_cmp_001)–[`ARC_CMP_009`](../../specifications/architecture_baseline.md#arc_cmp_009)) остаются кодом без определённого места запуска, и CI/CD пайплайн не может гарантировать одинаковое поведение между окружениями.

## 2. Результат

Задокументированная и, при необходимости, автоматизированная (файл сборки образа, конфигурация виртуальной машины или облачного сервиса) вычислительная среда, на которой развёртываются сервисы платформы. Совместима с текущим CI/CD пайплайном (Windows + Ubuntu валидация).

## 3. Где мы сейчас

Спецификация и реализация [`INF_CMP_001`](../../specifications/infrastructure_baseline.md#inf_cmp_001) завершены и покрыты [`TEST_014`](../tests/test_014.md): корневой [`dockerfile`](../../dockerfile) определяет воспроизводимую вычислительную среду (Python 3.12.14 slim-trixie, закреплённый OCI digest, непривилегированный пользователь приложения, идентифицируемая версия сборки, цикл проверки работоспособности через [`HealthAggregator`](../../src/operations/health.py) из [`TASK_007`](task_007_arc_009.md)). Канонический CI выполняет реальную build/run/health-проверку, фиксирует base/image digest и SPDX SBOM. Выбор конкретного облачного провайдера ([`ADR_007`](../../adr/adr_007_cloud_provider_selection.md), `proposed`) и среды агента ([`ADR_006`](../../adr/adr_006_agent_environment_framework.md), `proposed`) остаются открытыми — эта TASK не привязывается ни к одному из них: образ переносим и не содержит специфики облачного провайдера или SDK среды агента.

## 4. Что делать сейчас

### Агенту

Работа завершена, следующего действия по этой TASK нет.

## 5. План выполнения

- [x] Изучить требования к [`INF_CMP_001`](../../specifications/infrastructure_baseline.md#inf_cmp_001)
- [x] Дополнить allowed_paths реальными путями
- [x] Спроектировать реализацию
- [x] Реализовать компонент
- [x] Написать [`TEST_014`](../tests/test_014.md), связанный с TASK и требованиями компонента
- [x] Проверить покрытие путей в allowed_paths

## 6. Состав

[`dockerfile`](../../dockerfile) — воспроизводимая вычислительная среда: базовый образ `python:3.12.14-slim-trixie` закреплён полным OCI digest ([`INF_REQ_001`](../../specifications/infrastructure_baseline.md#inf_req_001)), непривилегированный пользователь `app` не имеет административных прав ([`INF_REQ_002`](../../specifications/infrastructure_baseline.md#inf_req_002)), аргумент сборки `APP_VERSION` встроен в образ как идентифицируемая версия развёртывания ([`INF_REQ_010`](../../specifications/infrastructure_baseline.md#inf_req_010)), а `HEALTHCHECK` вызывает [`src/operations/health_check.py`](../../src/operations/health_check.py) — тонкий CLI поверх [`HealthAggregator`](../../src/operations/health.py) ([`TASK_007`](task_007_arc_009.md)). Обновление digest выполняется отдельным reviewable PR вместе с build/run/health и SBOM evidence. Файл назван строчными буквами по соглашению репозитория (все пути — `lower_snake_case`, без исключений) — из-за этого Docker не находит его автоматически по `docker build .`, сборка требует явного `docker build -f dockerfile .`. [`.dockerignore`](../../.dockerignore) исключает служебные и документные пути из образа. [`work/tests/test_014.md`](../tests/test_014.md) — описание проверок компонента. [`operations/tests/product/test_compute_environment.py`](../../operations/tests/product/test_compute_environment.py) — юнит-тесты CLI и статическая проверка структуры файла сборки образа.

Разделение сред разработки и рабочего контура ([`INF_REQ_015`](../../specifications/infrastructure_baseline.md#inf_req_015)) задокументировано прямо в `dockerfile`: успешный локальный прогон `run_suite.py` (среда разработчика) не подтверждает эту рабочую среду — только собранный, версионированный образ является собственным доказательством рабочего контура.

## 7. Проверки и доказательства

Автоматическая проверка подтверждает, что все изменённые пути входят в `allowed_paths`. Требования компонента проверяет [`TEST_014`](../tests/test_014.md): юнит-тесты [`operations/tests/product/test_compute_environment.py`](../../operations/tests/product/test_compute_environment.py), часть обязательного gate `Quality skills`.

Локальная среда без Docker daemon выполняет статическую проверку digest, непривилегированного пользователя, `HEALTHCHECK` и аргумента версии. Канонический Linux CI дополнительно собирает образ на точном SHA, запускает встроенную проверку работоспособности, сверяет `APP_VERSION` с source SHA и сохраняет base digest, image digest и SPDX JSON SBOM в evidence artifact.

**Ручные (code review):**
1. `dockerfile` не содержит секретов или конкретных учётных данных — подтверждено сканером секретов ([`check.py`](../../operations/scripts/documents/check.py))
2. Образ не привязывается к конкретному облачному провайдеру или SDK среды агента — не использует специфичные для провайдера базовые образы или SDK
3. Ресурсы (CPU/память) для этого минимального образа не указываются явно: конкретные лимиты — решение развёртывания в конкретной инфраструктуре ([`ADR_007`](../../adr/adr_007_cloud_provider_selection.md)), не свойство самого образа

## 8. Готово когда

- ✅ Все шаги плана выполнены
- ✅ Локальные проверки успешны ([`operations/tests/product/test_compute_environment.py`](../../operations/tests/product/test_compute_environment.py): 10/10 тестов прошли, часть CI gate)
- ✅ Pre-commit валидация успешна
- ✅ Код review (смысловая проверка) пройден

## 9. Что будет дальше

[`TASK_009`](task_009_inf_002.md) реализует Сеть и контролируемый исходящий трафик ([`INF_CMP_002`](../../specifications/infrastructure_baseline.md#inf_cmp_002)) — правила того, что вычислительной среде из этой TASK разрешено делать в сети.

## 10. Что это даёт владельцу

Пока напрямую ничего не доступно: платформа ещё не запущена как постоянно работающий процесс (канал и шлюзы моделей/инструментов ещё не соединены в единый цикл). Появилось воспроизводимое, версионируемое и непривилегированное описание того, где и как сервисы платформы будут запускаться, перезапускаться и проверяться на работоспособность, когда это произойдёт.
