---
id: TASK_009
type: task
title: Реализация INF_CMP_002
component: INF_CMP_002
work_state: in-progress
version: 1.7
updated: 2026-08-26
next_actor: automation
owner_action: none
depends_on:
  - TASK_008
allowed_paths:
  - work/tasks/task_009_inf_002.md
  - src/operations/network_policy.py
  - operations/tests/product/test_network_policy.py
  - work/tests/test_015.md
traces_to:
  - m02
implements:
  - INF_CMP_002
tests:
  - TEST_015
---

# TASK_009 — Реализация INF_CMP_002

## 1. Зачем это делаем

Определить сетевые маршруты, правила входящего и исходящего трафика, DNS и, при необходимости, защищённые туннели для явно назначенных адресов. Без контролируемого исходящего трафика вычислительная среда ([`TASK_008`](task_008_inf_001.md)) может обращаться к произвольным внешним адресам — это прямой риск для шлюза инструментов ([`TASK_005`](task_005_arc_005.md)), который должен быть единственной точкой авторизации внешних вызовов.

## 2. Результат

Реализована проверяемая fail-closed allowlist-политика `NetworkPolicy`: baseline не открывает входящий трафик, не разрешает egress и не использует неявный DNS. Будущее исключение задаётся точной тройкой `service + target + port`; маршрут `secure_tunnel` не использует прямой fallback. Политика дополняет, а не заменяет авторизацию `ToolGateway` ([`TASK_005`](task_005_arc_005.md)).

## 3. Где мы сейчас

Спецификация [`INF_CMP_002`](../../specifications/infrastructure_baseline.md#inf_cmp_002) определяет требования ([`INF_REQ_003`](../../specifications/infrastructure_baseline.md#inf_req_003), [`INF_REQ_004`](../../specifications/infrastructure_baseline.md#inf_req_004), [`INF_REQ_005`](../../specifications/infrastructure_baseline.md#inf_req_005)). Реализация находится в `src/operations/network_policy.py` и проверяется [`TEST_015`](../tests/test_015.md). Зависимость от [`TASK_008`](task_008_inf_001.md) сохранена: политика описывает сеть для уже определённой вычислительной среды.

## 4. Что делать сейчас

### Агенту

Реализация и локальные проверки выполнены. Следующий шаг — канонический серверный gate для SHA PR, когда GitHub Actions снова станет доступен.

## 5. План выполнения

- [x] Изучить требования к [`INF_CMP_002`](../../specifications/infrastructure_baseline.md#inf_cmp_002)
- [x] Дополнить allowed_paths фактическими путями реализации
- [x] Спроектировать fail-closed allowlist-политику
- [x] Реализовать компонент и negative tests
- [x] Создать [`TEST_015`](../tests/test_015.md), связанный с TASK и требованиями компонента
- [x] Проверить покрытие путей в allowed_paths
- [ ] Выполнить канонический server gate на SHA PR

## 6. Состав

`src/operations/network_policy.py` содержит декларативные `IngressRule`, `EgressRule` и `NetworkPolicy`; `CURRENT_NETWORK_POLICY` пуст и поэтому закрывает сеть по умолчанию. `RouteKind.SECURE_TUNNEL` разрешает правило только при активном туннеле. `operations/tests/product/test_network_policy.py` проверяет allowlist, DNS и negative сценарии; [`TEST_015`](../tests/test_015.md) фиксирует проверяемый контракт.

## 7. Проверки и доказательства

**Автоматические:**
1. [`TEST_015`](../tests/test_015.md): 8 unit-тестов входят в канонический quality suite.
2. Временная локальная проверка перед публикацией: 8/8 unit-тестов, Ruff lint и format — PASS.
3. Канонический server gate ещё не выполнялся: GitHub Actions недоступен из-за исчерпанного лимита.

**Ручные (code review):**
1. У продукта пока нет реальных внешних интеграций, поэтому пустая allowlist соответствует минимально необходимому доступу.
2. До выбора конкретного провайдера и туннеля не заявляются фиктивные IP, DNS-resolver или правила firewall.

## 8. Готово когда

- ✅ Реализация и связанные unit-тесты существуют.
- ✅ Пути реализации покрыты `allowed_paths`.
- 🔄 Серверный CI ожидает следующего доступного запуска GitHub Actions.
- 🔄 Финальное состояние TASK будет обновлено после server gate.

## 9. Что будет дальше

[`TASK_010`](task_010_inf_003.md) реализует хранилище секретов ([`INF_CMP_003`](../../specifications/infrastructure_baseline.md#inf_cmp_003)) — следующий инфраструктурный компонент, критичный для безопасной работы шлюза моделей ([`TASK_004`](task_004_arc_004.md)) и других компонентов, использующих внешние учётные данные.

## 10. Что это даёт владельцу

Пока сеть платформы безопасно закрыта. Когда появится первая реальная интеграция, её отдельная TASK должна одновременно добавить точное правило в `NetworkPolicy` и применить эквивалентное ограничение на выбранном host/cloud firewall; без обоих действий внешний трафик не допускается.
