---
id: adr_content_traceability_audit_2026_08_29
type: audit_report
document_state: current
version: 1.0
updated: 2026-08-29
depends_on:
  - repository_audit_system_prompt
---

# Аудит содержания и трассировки ADR — 2026-08-29

## 1. Область и база проверки

Проверены все ADR репозитория `okromanov/personal_ai_platform` на ветке `main`,
базовый SHA `e4399e3de51f8eda176585cd22f9b6c5c7d9850e`, а также `milestones.md`,
`work/tasks/`, процедуры жизненного цикла, шаблоны, traceability-checker и
последний полный аудит.

Проверялись четыре независимых свойства:

1. содержание решения и соответствие текущему проектному контексту;
2. честность `decision_state`;
3. наличие структурированной связи с milestone и TASK принятия;
4. наличие TEST/evidence и явного решения владельца до перехода в `accepted`.

## 2. Итог

`ADR_001–ADR_004` приняты и остаются содержательно пригодными.
`ADR_005–ADR_009` имеют честный статус `proposed`.

Для активного `m02` отсутствовала машинная связь, показывающая, какая TASK
обязана подготовить решение и evidence для каждого proposed ADR. Текстовые
упоминания в `TASK_013–TASK_015` существовали, но не являлись трассировкой.
Это создавало возможность завершить TASK или milestone, оставив ADR
непринятым и не получив ошибку checker.

После исправления каноническая связь задаётся полем `TASK.decides`.
Для planned milestone связь становится обязательной при его декомпозиции и до
перехода в `in-progress`; это не заставляет создавать фиктивные TASK для
далёкого delivery horizon.

## 3. Результаты по каждому ADR

| ADR | Статус | Содержательная оценка | TASK принятия / следующее действие |
|---|---|---|---|
| `ADR_001` | `accepted` | Решение Python 3.12+ соответствует реализации и не запрещает обоснованный второй язык. | Исторически принято с `m01`; новой TASK не требуется. |
| `ADR_002` | `accepted` | Граница `RuntimePort` последовательно оставляет OwnerControl, состояние и шлюзы под контролем платформы. | Исторически принято с `m01`; `TASK_014` обязана не нарушить его. |
| `ADR_003` | `accepted` | Provider-neutral контракт соответствует риску смены поставщика. | Исторически принято с `m01`; `TASK_015` обязана ему соответствовать. |
| `ADR_004` | `accepted` | Минимальные структурированные события согласованы с task lifecycle и безопасным журналированием. | Исторически принято с `m01`; новая TASK не требуется. |
| `ADR_005` | `proposed` | Слишком рано центрирован на Claude как кандидате; выбор должен делаться по одной scorecard на фактическом сценарии, бюджете и правилах данных. | `TASK_015` (`decides: ADR_005`). |
| `ADR_006` | `proposed` | Содержательно неполон: сравнивает Claude Agent SDK с общими категориями, но не включает явно Hermes и минимальный native adapter, хотя это ключевая развилка проекта. | `TASK_014` (`decides: ADR_006`). |
| `ADR_007` | `proposed` | Устарел относительно текущей практической проверки: текст центрирован на AWS, тогда как `TASK_013` и runbook проверяют Hetzner. Нельзя принимать до единой scorecard и evidence Hetzner. | `TASK_013` (`decides: ADR_007`). |
| `ADR_008` | `proposed` | Слишком детально предрешает PostgreSQL, таблицы и индексы до `m04`. Следует сохранить как гипотезу и перепроверить против более простого варианта на реальных данных и recovery-сценарии. | `m04` ещё `planned`; TASK принятия обязана появиться при декомпозиции `m04` до его старта. |
| `ADR_009` | `proposed` | Предрешает AWS Secrets Manager до принятия облака. При Hetzner нужны provider-neutral варианты и минимально достаточный V1-контур. | `TASK_013` (`decides: ADR_009`) вместе с выбором площадки и runtime-secret механизма. |

## 4. Содержательные предложения

### 4.1 ADR_005

В `TASK_015` заменить кандидатный нарратив окончательным сравнением доступных
на момент выполнения поставщиков. Один и тот же сценарий должен измерять
качество, задержку, стоимость, доступность из выбранной сети, правила данных,
timeout/error handling и работу через `ModelProvider`. Claude остаётся
допустимым кандидатом, но не подразумеваемым победителем.

### 4.2 ADR_006

В `TASK_014` сравнить минимум:

- Hermes Agent через тонкий `RuntimePort` adapter;
- Claude Agent SDK через такой же adapter;
- минимальный native loop как контроль сложности и зависимости.

Hermes официально позиционируется как модельно-независимый агент с Telegram и
работой на VPS; Claude Agent SDK предоставляет программируемые agent loop,
tools и context management. Эти возможности не доказывают совместимость с
OwnerControl: сравнение обязано отдельно проверить отмену, состояние, tool
boundary, секреты и невозможность обхода Kill Switch.

### 4.3 ADR_007

Переписать после evidence `TASK_013`: Hetzner должен стать проверяемым
кандидатом, а AWS — альтернативой, а не наоборот. Scorecard включает стоимость,
SSH/firewall, исходящую Telegram-связность, backup/snapshot, recreate,
экспорт/перенос и операционную сложность. Hetzner документирует Cloud Firewall,
backups и snapshots, но это не заменяет проверку нашего deployment/restore.

### 4.4 ADR_008

На `m04` сравнить PostgreSQL с SQLite или другим более простым вариантом на
фактическом объёме и сценариях памяти. PostgreSQL действительно поддерживает
row-level security и штатные dump/recovery-инструменты, но текущий ADR не
доказывает, что эта сложность нужна личному V1. Индекс embeddings не следует
фиксировать без выбранного расширения и измеренного набора данных.

### 4.5 ADR_009

После выбора площадки сравнить как минимум:

- runtime-only защищённый файл/credentials для одного владельца;
- SOPS + age для зашифрованной конфигурации;
- централизованный manager (Vault либо provider-managed service).

AWS Secrets Manager поддерживает централизованное получение и ротацию, SOPS
шифрует YAML/JSON/ENV с age/KMS, Vault централизует static/dynamic secrets и
аудит. Для персональной платформы более функциональный вариант не считается
лучшим без доказанной эксплуатационной пользы.

## 5. Почему предыдущий аудит это пропустил

### 5.1 Односторонняя автоматическая проверка

`check_traceability` требовал только, чтобы ADR имел непустой `traces_to`.
Обратного правила «proposed ADR активного milestone → ровно одна незавершённая
TASK» не существовало. Поэтому все ADR формально проходили 22/22 структурных
проверок.

### 5.2 В модели связей не было отношения принятия ADR

Traceability parser знал `traces_to`, `implements`, `verifies`,
`accepts` и зависимости, но не знал `decides`. Текстовое упоминание
`ADR_006` в `TASK_014` и `ADR_005` в `TASK_015` выглядело разумно для
человека, однако не создавало машинного ребра.

### 5.3 Milestone создавал ложное ощущение покрытия

Строка «ADR этого этапа» в `milestones.md` связывала ADR со временем, но не
назначала ответственного TASK и не определяла evidence. Предыдущий аудит
проверил неверную запись принятия `m01`, но не выполнил обратный обход от
каждого оставшегося `proposed` ADR до TASK.

### 5.4 Методика защищала delivery horizon слишком широко

Системный prompt аудита правильно запрещал требовать TASK для будущего
требования вне активного delivery scope. Но он не делал обязательного
исключения для proposed ADR активного milestone. В результате правило,
предназначенное против преждевременной декомпозиции, скрыло реальный пробел
`m02`.

### 5.5 Отсутствовал отрицательный тест

Не было fixture, где active milestone содержит proposed ADR без TASK и checker
обязан упасть. Поэтому регрессия не могла проявиться ни локально, ни в CI.

## 6. Исправления

1. Введено каноническое поле `TASK.decides`.
2. `ADR_005`, `ADR_006`, `ADR_007`, `ADR_009` назначены незавершённым
   `TASK_015`, `TASK_014`, `TASK_013`, `TASK_013` соответственно.
3. Checker блокирует active/completed milestone, если proposed ADR не имеет
   ровно одной незавершённой decision TASK.
4. Завершённая или отменённая TASK не может оставлять назначенный ADR в
   `proposed`.
5. Процедуры ADR lifecycle, planning/decomposition и TASK template обновлены.
6. Audit prompt дополнен обязательным обратным проходом ADR → TASK → evidence.
7. Добавлены отрицательные unit tests и relation `decides` включено в
   сгенерированную traceability matrix.

## 7. Официальные источники для повторной проверки кандидатов

- [Claude Agent SDK](https://docs.anthropic.com/en/docs/claude-code/sdk)
- [Hermes Agent](https://github.com/NousResearch/hermes-agent)
- [Hetzner Cloud](https://docs.hetzner.com/cloud/)
- [Hetzner Cloud Firewalls](https://docs.hetzner.com/cloud/firewalls/overview/)
- [Hetzner Backups and Snapshots](https://docs.hetzner.com/cloud/servers/backups-snapshots/overview/)
- [AWS Secrets Manager](https://docs.aws.amazon.com/secretsmanager/)
- [SOPS](https://github.com/getsops/sops)
- [HashiCorp Vault](https://developer.hashicorp.com/vault/docs/about-vault/what-is-vault)
- [PostgreSQL row security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [PostgreSQL pg_dump](https://www.postgresql.org/docs/current/app-pgdump.html)

## 8. Gate проверки

Исправление считается подтверждённым, когда:

- новый ADR decision-task checker проходит на репозитории;
- отрицательные fixtures падают без `decides`, при дублировании owner TASK и
  при completed TASK с ADR в `proposed`;
- traceability matrix показывает `TASK_013 decides ADR_007, ADR_009`,
  `TASK_014 decides ADR_006`, `TASK_015 decides ADR_005`;
- полный project gate и CI успешны на одном SHA.
