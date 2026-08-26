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

`NetworkPolicy` определяет единую декларативную политику сети:

- baseline не открывает входящие порты и не разрешает внешний трафик;
- ingress и egress сопоставляются с точным сервисом, а egress — также с адресом и портом;
- DNS разрешён только через явно объявленный resolver, для которого существует отдельное правило egress;
- маршрут `secure_tunnel` пропускает трафик только при активном туннеле и не переходит на прямое соединение при его потере.

Так выполняются [`INF_REQ_003`](../../specifications/infrastructure_baseline.md#inf_req_003), [`INF_REQ_004`](../../specifications/infrastructure_baseline.md#inf_req_004) и [`INF_REQ_005`](../../specifications/infrastructure_baseline.md#inf_req_005) для состояния без внешних интеграций.

## 3. Автоматический запуск

Часть канонического набора unit-тестов:

```bash
python3 operations/scripts/quality/run_unittests.py
```

Отдельный прогон компонента:

```bash
python3 -m unittest operations.tests.product.test_network_policy -v
```

## 4. Критерий успеха

Все 8 тестов проходят. Проверяются отрицательные сценарии: незаявленные ingress/egress/DNS запрещены, изменение сервиса, адреса или порта не наследует разрешение, а потеря туннеля не создаёт direct fallback.

## 5. Граница доказательства

`automated_evidence: quality_suite`. Тесты доказывают программное правило; конкретный cloud firewall или VPN не выбран в [`m02`](../../milestones.md#m02) и не выдаётся за развёрнутый.
