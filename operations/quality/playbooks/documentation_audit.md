---
id: documentation_audit
type: guide
document_state: current
applicability: normative
version: 1.1
updated: 2026-09-04
---

# Аудит документации

## Запуск

```bash
python3.12 operations/scripts/documents/generate.py --all
python3.12 operations/scripts/documents/check.py --all
```

## Что подтверждает

Проверяются структура, front matter, машинные контракты, трассировка, TASK/TEST, ссылки, применимость, доступность, читаемость, audit register и отсутствие drift производных файлов.

## Критерий успеха

Процесс завершён с кодом 0, `error_count=0`, `warning_count=0`; повторная генерация не меняет дерево. Количество групп проверок не фиксируется в тексте: оно меняется вместе с checker.

## Границы

Структурная проверка не доказывает истинность требований, качество продуктового поведения или результат CI. Для смысловой проверки применяется [`semantic_review.md`](../../semantic_review.md).
