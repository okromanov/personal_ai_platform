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
| project_status.md | текущий этап | Обновляется | автомат (generate.py) | check.py: generated |
| owner_dashboard.md | Ворота и действия | Обновляются динамически | автомат (render_owner_dashboard) | check.py: generated |

## Когда milestone переходит из in-progress → completed

| Файл | Поле | Действие | Кто/Как | Проверка |
|---|---|---|---|---|
| work/m0X/final_report.md | completion_state | `pending` → `completed` | update_completion_report.py | check.py: metadata |
| work/m0X/final_report.md | section 1 | "в процессе" → "завершено" | update_completion_report.py | manual review |
| work/m0X/final_report.md | дата завершения | "-" → date.today() | update_completion_report.py | manual review |
| milestones.md | work_state | Меняется на `completed` | владелец вручную | check.py: milestones |
| project_status.md | Прогресс | Обновляется | автомат (generate.py) | check.py: generated |
| owner_dashboard.md | Статус m0X | Обновляется | автомат (render_owner_dashboard) | check.py: generated |
| owner_dashboard.md | Ворота и действия | Обновляются на следующий этап | автомат (render_owner_dashboard) | check.py: generated |

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
- **Генерируется:** render_repository_project_status()
- **Проверка:** check.py: generated (drift check)

### owner_dashboard.md
- **Зависит от:** milestones.md (current_id, work_state)
- **Генерируется:** render_owner_dashboard()
- **Динамические части:**
  - "Оставшиеся ворота" → get_gates_for_milestone()
  - "Действия" → get_actions_for_milestone()
  - "Статус проверок" → depends on current_id

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
- [ ] Функции в owner_dashboard.py для gates и actions (если не in-progress)
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
