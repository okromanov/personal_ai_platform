---
id: file_update_dependencies
type: procedure_reference
document_state: current
version: 1.0
created: 2026-08-23
updated: 2026-08-23
---

# Матрица зависимостей обновления файлов

Эта матрица определяет, какие файлы должны быть обновлены при изменении состояния проекта.

## Когда milestone переходит из planned → in-progress

| Файл | Поле | Действие | Кто/Как | Проверка |
|---|---|---|---|---|
| work/m0X/owner_checklist.md | - | Создаётся init_milestone.py | автомат (событие) | git добавляется |
| work/m0X/semantic_review.md | - | Создаётся init_milestone.py | автомат (событие) | git добавляется |
| work/m0X/final_report.md | - | Создаётся init_milestone.py | автомат (событие) | git добавляется |
| milestones.md | work_state | Меняется на `in-progress` | владелец вручную | check.py: milestones |
| project_status.md | текущий этап, файлы задач | Обновляется | автомат (generate.py) | check.py: generated |
| owner_dashboard.md | статистика документов/репозитория | Пересчитывается | автомат (render_owner_dashboard) | check.py: generated |

## Когда milestone переходит из in-progress → completed

| Файл | Поле | Действие | Кто/Как | Проверка |
|---|---|---|---|---|
| work/m0X/final_report.md | completion_state | `pending` → `completed` | update_completion_report.py | check.py: metadata |
| work/m0X/final_report.md | section 1 | "в процессе" → "завершено" | update_completion_report.py | manual review |
| work/m0X/final_report.md | дата завершения | "-" → date.today() | update_completion_report.py | manual review |
| milestones.md | work_state | Меняется на `completed` | владелец вручную | check.py: milestones |
| project_status.md | Прогресс | Обновляется | автомат (generate.py) | check.py: generated |
| owner_dashboard.md | "Что уже реализовано" | Добавляется раздел завершённой TASK | автомат (render_owner_dashboard) | check.py: tasks (запрет заглушки в "Результат") |

## Зависимости по типам файлов

### work/m0X/final_report.md
- **Зависит от:** milestones.md (work_state)
- **Влияет на:** project_status.md, owner_dashboard.md
- **Поля синхронизации:**
  - completion_state: должна соответствовать work_state
  - Содержимое раздела 1: должно отражать актуальный статус
  - updated: должна быть текущей датой при изменении

### work/m0X/owner_checklist.md  
- **Зависит от:** milestones.md (when created)
- **Поля синхронизации:**
  - Создаётся один раз при переходе planned → in-progress
  - Версия: автоинкрементируется при изменении содержимого

### project_status.md
- **Зависит от:** milestones.md, work/tasks/*, work/tests/*
- **Генерируется:** render_repository_project_status() в operations/scripts/status/human_status.py
- **Проверка:** check.py: generated (drift check), check.py: owner_interface (запрещённые внутренние детали)
- **Раздел "Файлы, созданные в рамках задач":** для каждой TASK, чей `allowed_paths` вышел за пределы собственной карточки (`_deliverable_paths()`), перечисляет эти пути гиперссылками; однострочное описание берётся из раздела "Назначение" первого связанного TEST (`_test_purpose()`, читает `task.tests[0].path` напрямую с диска). Если у TASK нет доказательства или её `allowed_paths` ещё не расширен — TASK не показывается вовсе, ничего не выдумывается.

### owner_dashboard.md
- **Зависит от:** весь трассируемый граф документов (для статистики по семействам), work/tasks/*, work/tests/*, локально записанные `runtime/coverage.json` и `runtime/step_timings.json` (не хранятся в git)
- **Генерируется:** render_owner_dashboard() в operations/scripts/documents/owner_dashboard.py
- **Разделы:**
  - "Статистика репозитория" — файлы/строки кода/тесты считаются вживую при каждой генерации (`iter_files`, построчный подсчёт, `unittest` discovery без запуска); покрытие и время прогона читаются из `runtime/*.json`, если они есть локально, иначе — явная пометка "нет данных"
  - "Статистика документов" — реальные счётчики через `collect_traceable_elements()` по семействам (BR/SYS/THR/SEC_CTL/INF_REQ/ADR) плюс `collect_tasks()`/`collect_test_specs()` для TASK/TEST; никогда не хардкодится
  - "Что уже реализовано" — для каждой `work_state: completed` TASK дословно показывает её раздел "Результат"; `check.py` (`check_tasks`) отдельно запрещает оставлять здесь автосгенерированную заглушку у завершённой TASK, поэтому текст в этом разделе не бывает пустым шаблоном
  - Не дублирует статус этапа/ворота/действие владельца — это зона project_status.md и milestones.md

## Процедура обновления при завершении milestone

1. **Владелец:** Вносит команду `ПРИНИМАЮ m0X` в project_status.md
2. **acceptance.py:** 
   - Меняет work_state в milestones.md на `completed`
3. **Автомат (pre-commit или CI):**
   - update_completion_report.py: обновляет work/m0X/final_report.md
   - generate.py: перегенерирует project_status.md и owner_dashboard.md
   - increment_file_version.py: обновляет версии изменённых файлов
4. **check.py:** Валидирует что:
   - completion_state соответствует work_state
   - generated файлы синхронизированы
   - Версии актуальны

## Чек-лист для добавления нового milestone

При создании нового milestone m0X должны быть:
- [ ] Шаблоны в work/m0X/ (created автоматически init_milestone.py)
- [ ] Запись в milestones.md с work_state: planned
- [ ] Профиль в operations/quality_registry.json если in-progress/completed
- [ ] Процедура обновления completion_state (update_completion_report.py)

## Проверка полноты

```bash
# Валидировать все зависимости
python3.13 operations/scripts/documents/check.py --all

# Проверить дрифт generated файлов
python3.12 operations/scripts/documents/generate.py --all && git status

# Проверить completion_state соответствие work_state
python3 -c "
from pathlib import Path
from operations.scripts.status.generate_project_status import collect_milestones

data = collect_milestones(Path('.'))
for m in data['items']:
    report = Path('work') / m['id'] / 'final_report.md'
    if report.exists():
        content = report.read_text()
        has_completed = 'completion_state: completed' in content
        should_be_completed = m['work_state'] == 'completed'
        match = '✅' if has_completed == should_be_completed else '❌'
        print(f'{match} {m[\"id\"]}: work_state={m[\"work_state\"]}, completion_state={has_completed}')
"
```
