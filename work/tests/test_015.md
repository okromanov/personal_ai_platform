---
id: TEST_015
type: test
title: "INF_CMP_002 — сеть: fail-closed ingress, egress, DNS и обязательный туннель"
spec_state: current
execution: automated
automated_evidence: quality_suite
version: 1.0
updated: 2026-08-26
accepts:
  - m02
traces_to:
  - TASK_009
verifies:
  - INF_REQ_003
  - INF_REQ_004
  - INF_REQ_005
depends_on:
  - TEST_014
---

# TEST_015 — Сеть: fail-closed ingress, egress, DNS и обязательный туннель

Автоматическая проверка. Действия владельца не требуются.

## 1. Назначение

Доказать, что [`INF_CMP_002`](../../specifications/infrastructure_baseline.md#inf_cmp_002) начинает работу с закрытой публичной и исходящей сети, а каждое будущее исключение требует точного адресата, сервиса и маршрута.

## 2. Что проверяется

`src/operations/network_policy.py` определяет единую декларативную политику сети:

- текущий baseline не открывает входящие порты и не разрешает внешний трафик;
- правило исходящего трафика сопоставляется одновременно с сервисом, адресом и портом — маршрут одного сервиса не расширяет возможности другого;
- DNS разрешён только через явно объявленный resolver, для которого существует отдельное правило egress;
- маршрут `secure_tunnel` пропускает трафик только при активном туннеле и не переходит на прямое соединение при его потере.

Так выполняются [`INF_REQ_003`](../../specifications/infrastructure_baseline.md#inf_req_003), [`INF_REQ_004`](../../specifications/infrastructure_baseline.md#inf_req_004) и [`INF_REQ_005`](../../specifications/infrastructure_baseline.md#inf_req_005) для текущего состояния без внешних интеграций.

## 3. Автоматический запуск

Часть канонического набора unit-тестов, выполняемого в `Quality skills` на каждом push/PR:

```bash
python3 operations/scripts/quality/run_unittests.py
```

Отдельный прогон компонента:

```bash
python3 -m unittest operations.tests.product.test_network_policy -v
```

## 4. Критерий успеха

Все 8 тестов проходят. В частности, проверяются отрицательные сценарии: незаявленные ingress/egress/DNS запрещены, изменение сервиса, адреса или порта не наследует разрешение, а потеря туннеля не создаёт прямой fallback.

## 5. Состав доказательства

`automated_evidence: quality_suite`. Канонический прогон создаёт evidence текущего запуска и включает `operations/tests/product/test_network_policy.py`.

Граница доказательства прозрачна: конкретный cloud firewall или VPN не выбирается в [`m02`](../../milestones.md#m02), а реальных внешних обработчиков ещё нет. Поэтому TEST доказывает применяемое программное правило, с которым любая последующая интеграция обязана согласовать свой host/provider firewall; он не выдаёт это за уже развёрнутое правило у конкретного провайдера.

## 6. Реализованный компонент

`NetworkPolicy` — неизменяемая allowlist-политика. `CURRENT_NETWORK_POLICY` пуст: это намеренный default deny. Будущая TASK может добавить правило лишь вместе с конкретной интеграцией и её инфраструктурным применением.

## 7. Соответствие требованиям

| Требование | Статус | Примечание |
|---|---|---|
| [`INF_REQ_003`](../../specifications/infrastructure_baseline.md#inf_req_003): Минимальная публичная поверхность | ✅ | В baseline отсутствуют ingress rules |
| [`INF_REQ_004`](../../specifications/infrastructure_baseline.md#inf_req_004): Явная политика исходящей сети | ✅ | Только точное правило `service + target + port` разрешает egress и DNS |
| [`INF_REQ_005`](../../specifications/infrastructure_baseline.md#inf_req_005): Закрытие при отказе обязательного маршрута | ✅ | `secure_tunnel` без активного туннеля возвращает отказ |
