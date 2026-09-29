---
id: operations_sample_task_lifecycle
type: guide
document_state: current
version: 1.4
updated: 2026-09-26
depends_on:
  - operations_change_process
  - operations_procedure_map
---

# SAMPLE_TASK_001 — Пример полного цикла задачи

Эта карточка показывает, как выглядит полный путь задачи от создания к доказательству. Используется только для обучения и демонстрации процесса.

## 1. Назначение

Задача демонстрирует:
- Структуру карточки TASK
- Связь между TASK и требованиями
- Как ограничиваются изменяемые пути (allowed_paths)
- Связь с доказательствами (test_sample.md)

## 2. Требования к выполнению

Эта задача просто показывает пример и не требует реальной реализации. Однако если бы она была реальной, выполнение включало бы:

1. ✅ Обновить спецификацию требований
2. ✅ Создать или обновить TEST для этого требования
3. ✅ Реализовать код (если требуется)
4. ✅ Запустить локальные проверки
5. ✅ Создать PR с описанием
6. ✅ Дождаться зелёного CI
7. ✅ Обновить статус TASK на `completed`

## 3. Связанные документы

- Спецификация требования: [`specifications/system_specification.md`](../../specifications/system_specification.md)
- Примеры тестов: [`work/tests/test_001.md`](../../work/tests/test_001.md)
- Инструкция агенту: [`AGENTS.md`](../../AGENTS.md) раздел 3 (цикл разработки)
- Процедура проверки: [`operations/procedure_map.md`](../procedure_map.md)

## 4. Критерии завершения

TASK переводится в `completed` только когда:

- ✅ Все изменения покрыты разрешёнными путями (allowed_paths)
- ✅ Локальный прогон даёт errors=0, warnings=0
- ✅ Связанный TEST проходит (result: passed)
- ✅ CI зелёный (все проверки pass)
- ✅ PR заслужил approval или owner разрешил прямую запись

## 5. Пример пути выполнения

Если бы это была реальная задача, цикл выглядел бы так:

```
Агент получает: ПРОДОЛЖАЙ SAMPLE_TASK_001
       ↓
1. Прочитать TASK и понять allowed_paths
   └─ Пути: operations/examples/**, specifications/system_specification.md, ...
       
2. Выполнить change_process.md § 2 (создать ветку)
   └─ git checkout -b work/sample-task-0001
       
3. Внести изменения
   ├─ Обновить specifications/system_specification.md
   ├─ Обновить/создать work/tests/test_sample.md
   └─ Создать operations/examples/sample_implementation.md (если нужно)

4. Пересобрать производные
   └─ python3.12 operations/scripts/documents/generate.py --all

5. Полный локальный прогон
   ├─ generate.py --all (повторно)
   ├─ check.py --all (errors=0, warnings=0)
   └─ unittest discover (все тесты pass)

6. Проверить рабочую разницу
   ├─ git status (разница понятна)
   └─ project_status.md не меняется при повторной регенерации

7. Коммит
   └─ git commit -m "пример: описание изменения"
         
8. Опубликовать
   └─ git push -u origin work/sample-task-0001 → PR на GitHub

9. Дождаться CI
   ├─ Linux validation ✅
   ├─ Windows validation ✅
   └─ Project check ✅

10. Слить PR
    └─ Статус TASK меняется на completed
```

## 6. Что происходит дальше

После завершения TASK:
- Результат добавляется в базу доказательств (`work/audit/evidence/`)
- project_status.md автоматически обновляется
- Владелец видит новый результат и может принять решение

## 7. Общие ошибки и как их избежать

| Ошибка | Решение |
|---|---|
| Изменены файлы вне allowed_paths | Перечитать allowed_paths перед началом |
| Забыли запустить generate.py | Всегда: generate.py → check.py → unittest |
| CI красный, не знаем почему | Запустить локально (check.py), затем обратиться к [`operations/procedure_map.md`](../procedure_map.md) § 3 |
| Коммит содержит > 1 независимых изменения | Разделить на несколько коммитов или PR |
| Изменили authority document без версии | Всегда обновлять version на authority docs |

## 8. Дальнейшее обучение

Если вам нужны подробные примеры и процедуры, см.:
- [`operations/procedure_map.md`](../procedure_map.md) — полная карта сценариев и процедур
- [`AGENTS.md`](../../AGENTS.md) — инструкции для агента разработки
- [`operations/change_process.md`](../change_process.md) — полный цикл изменений
