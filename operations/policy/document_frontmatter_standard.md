---
id: document_frontmatter_standard
type: guide
document_state: superseded
version: 1.4
updated: 2026-09-01
depends_on:
  - project_rules
---

# Стандарт frontmatter для документов (заменён)

**Заменён [`change_process.md`](../change_process.md#8-стандарт-yaml-frontmatter-и-правила-создания-файлов) §8, который реально применяется и проверяется `check.py`.** Этот файл заявлял себя «единственным источником истины», конфликтуя с §8, ноль документов на него не ссылались, а перечисленные здесь типы документов (`architecture`, `infrastructure`, `operations_guide`) не совпадают с типами, которые реально проверяет `check_frontmatter_standard` (`architecture_baseline`, `infrastructure_baseline` и т.д.) — см. [`AUD-011`](../../work/audit/audit_register.md#aud-011). Единственное, чего не было в §8 — рекомендуемый порядок полей frontmatter (раздел 5 ниже) и версионная семантика (раздел 3-4) — перенесено в [`change_process.md`](../change_process.md#82-правила-формирования-и-валидации) §8.2. Остальное содержимое этого файла сохранено ниже как история, но не действует.

Этот документ ранее заявлял себя единственным источником истины для структуры YAML frontmatter во всех типах документов проекта.

## 1. Требуемые поля для всех документов

Каждый документ Markdown в репозитории должен начинаться с YAML frontmatter, содержащего:

```yaml
---
id: unique_identifier
type: document_type
document_state: current
version: 1.0
updated: 2026-08-18
depends_on:
  - dependency_id_1
  - dependency_id_2
---
```

### Описание полей

| Поле | Тип | Обязательное | Описание |
|---|---|---|---|
| `id` | строка | Да | Уникальный идентификатор документа в формате `snake_case`. Должен совпадать с `document_state_*` типом документа. |
| `type` | строка | Да | Один из определённых типов документа (см. раздел 2). |
| `document_state` | строка | Да | Одно из значений: `current`, `superseded`. Для ADR используется `decision_state`. |
| `version` | строка | Да | Версия документа в формате `X.Y` (например, `1.0`, `1.1`). Должна бумпиться при семантических изменениях. |
| `updated` | дата | Да | Дата последнего обновления в формате `YYYY-MM-DD`. Обновляется при любом семантическом изменении документа. |
| `depends_on` | список | Нет | Список идентификаторов документов, от которых зависит этот документ. Пусто, если зависимостей нет. |

## 2. Типы документов и дополнительные поля

### 2.1 business_requirements
Бизнес-требования и их приоритизация.

```yaml
type: business_requirements
document_state: current
```

Дополнительные поля: нет.

### 2.2 system_specification
Системные требования и технические меры.

```yaml
type: system_specification
document_state: current
```

Дополнительные поля: нет.

### 2.3 threat_model
Модель угроз и их классификация.

```yaml
type: threat_model
document_state: current
```

Дополнительные поля: нет.

### 2.4 architecture
Архитектурное решение и компоненты.

```yaml
type: architecture
document_state: current
```

Дополнительные поля: нет.

### 2.5 infrastructure
Инфраструктурные требования.

```yaml
type: infrastructure
document_state: current
```

Дополнительные поля: нет.

### 2.6 adr (Architecture Decision Record)
Архитектурное решение с альтернативами.

```yaml
type: adr
decision_state: accepted
traces_to:
  - BR_001
  - SYS_001
```

Дополнительные поля:
- `decision_state`: `proposed`, `accepted`, `rejected`, `superseded`
- `traces_to`: список требований, которые реализует это решение

### 2.7 project_rules
Фундаментальные принципы и правила проекта.

```yaml
type: project_rules
document_state: current
```

Дополнительные поля: нет.

### 2.8 operations
Процедуры и операционные руководства.

```yaml
type: operations
document_state: current
```

Дополнительные поля: нет.

### 2.9 operations_guide
Руководства для операционной деятельности.

```yaml
type: operations_guide
document_state: current
```

Дополнительные поля: нет.

### 2.10 agent_instruction
Инструкции для агентов.

```yaml
type: agent_instruction
document_state: current
```

Дополнительные поля: нет.

### 2.11 task
Задача реализации.

```yaml
type: task
title: Название задачи
component: ARC_CMP_001
work_state: in-progress
version: 1.0
next_actor: agent
owner_action: none
allowed_paths:
  - specifications/**
  - src/**
implements:
  - ARC_CMP_001
```

Дополнительные поля:
- `title`: название задачи
- `component`: один канонический архитектурный или инфраструктурный компонент
- `work_state`: `planned`, `in-progress`, `blocked`, `completed`, `cancelled`
- `next_actor`: `agent` или `owner` или `none`
- `owner_action`: описание требуемого действия владельца
- `allowed_paths`: список путей, которые эта задача может изменять — только сам путь (маска, каталог или файл), без дополнительного текста. Что представляет собой конкретный файл, описывается в разделе «6. Состав» карточки, а не в самом списке путей.
- `implements`: собственный component и только семантически связанные элементы его цепочки требований

### 2.12 test
Тест или проверка.

```yaml
type: test
title: Название проверки
spec_state: current
execution: automated
automated_evidence: unit_tests
accepts:
  - m01
verifies:
  - SYS_001
```

Дополнительные поля:
- `title`: название проверки
- `spec_state`: `current`, `superseded`
- `execution`: `automated` или `manual`
- `automated_evidence` (для automated): тип доказательства
- `manual_evidence` (для manual): тип доказательства
- `accepts`: список этапов, которые эта проверка может принять
- `verifies`: список требований, которые проверяет этот тест

### 2.13 roadmap
Дорожная карта проекта.

```yaml
type: roadmap
document_state: current
```

Дополнительные поля: нет.

### 2.14 generated_* (автоматически генерируемые документы)

```yaml
type: generated_document  # или другой generated_* тип
document_state: current
```

Дополнительные поля: нет. Эти документы генерируются автоматически и не должны редактироваться вручную.

## 3. Требования к версионированию

1. Версия документа представляет в формате `MAJOR.MINOR` (например, `1.0`, `1.5`, `2.3`).
2. **MAJOR** версия бумпится при критических изменениях (переструктурирование, смена семантики).
3. **MINOR** версия бумпится при любом семантическом изменении содержания.
4. Версия НЕ бумпится при:
   - Орфографических исправлениях
   - Форматировании
   - Добавлении перекрёстных ссылок без изменения смысла
   - Автоматической регенерации (для generated_*документов)

## 4. Правило синхронизации даты и версии

Если документ был семантически изменён:
- Дата `updated` ДОЛЖНА быть текущей датой (дата коммита)
- Версия ДОЛЖНА быть бумпнута (MAJOR или MINOR)

Если версия или дата бумпнуты, но содержание не изменилось семантически:
- Это ошибка, которая должна быть найдена pre-commit проверкой

## 5. Порядок полей frontmatter

Поля frontmatter должны быть расположены в следующем порядке:

1. `id`
2. `type`
3. `title` (если применимо)
4. Поля состояния (`document_state`, `decision_state`, `work_state`, `spec_state`)
5. Специальные поля (execution, automated_evidence, manual_evidence и т.д.)
6. `version`
7. `updated`
8. `depends_on` (в конце)

## 6. Примеры правильного frontmatter

### Пример 1: Требование
```yaml
---
id: business_requirements
type: business_requirements
document_state: current
version: 1.0
updated: 2026-08-18
depends_on:
  - project_rules
---
```

### Пример 2: Решение (ADR)
```yaml
---
id: adr_001_agent_framework
type: adr
decision_state: accepted
traces_to:
  - BR_001
  - SYS_001
version: 1.0
updated: 2026-08-18
depends_on:
  - project_rules
  - system_specification
---
```

### Пример 3: Задача
```yaml
---
id: TASK_001
type: task
title: Реализация основного цикла
work_state: in-progress
version: 1.0
next_actor: agent
owner_action: none
updated: 2026-08-18
allowed_paths:
  - src/**
  - operations/scripts/**
depends_on:
  - TASK_000
---
```

### Пример 4: Автоматический тест
```yaml
---
id: TEST_001
type: test
title: Проверка модели документов
spec_state: current
execution: automated
automated_evidence: project_checks
version: 1.0
updated: 2026-08-18
accepts:
  - m01
verifies:
  - SYS_001
depends_on: []
---
```
