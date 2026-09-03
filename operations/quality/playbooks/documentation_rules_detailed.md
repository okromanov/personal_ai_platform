---
id: documentation_rules_detailed
type: guide
document_state: current
applicability: normative
version: 1.2
updated: 2026-09-04
---

# Детальные правила документации

## Источники

- значения состояний и применимости: [`document_contracts.json`](../../document_contracts.json);
- тип и структура: [`template_registry.json`](../../template_registry.json) и его шаблон;
- процесс изменения: [`change_process.md`](../../change_process.md);
- исполнение правил: [`check.py`](../../scripts/documents/check.py) и [`links.py`](../../scripts/documents/links.py).

## Обязательные свойства

Каждый первичный Markdown-документ имеет уникальный `id`, ровно одно поле состояния своего типа, версию и дату. `applicability` принимает значение из машинного контракта; отсутствие означает `normative`. Архивный superseded-документ помечается `historical`.

Связи в front matter содержат ID, а ссылки в прозе — кликабельные относительные Markdown-ссылки. Существующий файл, упомянутый inline-code, также должен быть ссылкой. Датированные audit baseline неизменяемы и исключены из автоматического переписывания.

TASK не хранит историю работы и общие правила. TEST использует только `automated` или `manual` и ровно пять разделов зарегистрированного шаблона.

## Проверка

```bash
python3.12 operations/scripts/documents/check.py --fast
python3.12 operations/scripts/documents/check.py --all
```

Новые правила добавляются вместе с negative regression-test. Предупреждение считается незакрытым результатом для полного documentation audit.
