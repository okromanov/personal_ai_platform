---
id: file_update_dependencies
type: procedure_reference
document_state: current
version: 1.6
created: 2026-08-23
updated: 2026-09-04
---

# Матрица зависимостей обновления файлов

Эта матрица определяет, какие файлы должны быть обновлены при изменении состояния проекта.

## Правило: ссылки на трассируемые ID

Любой генератор, который выводит ссылку на трассируемый ID (BR/SYS/THR/SEC_CTL/ARC_CMP/ARC_FLOW/INF_REQ/INF_CMP/INF_FLOW/ADR/TASK/TEST/этап), обязан оформлять её как markdown-ссылку, если этот ID разрешается через `collect_traceable_elements()` (`operations/scripts/documents/traceability.py`) — обычные обратные кавычки `` `ID` `` без ссылки для разрешимого ID запрещены. Не найденный в реестре ID (например, ещё не описанный) остаётся текстом в кавычках, а не выдумывается. Эталонные реализации:
`_link()`/`_requirement_links()` в `update_completion_report.py` и `_linked_ids()` в `operations/scripts/tasks/generate.py`.

## Когда milestone переходит из planned → in-progress

| Файл | Поле | Действие | Кто/Как | Проверка |
|---|---|---|---|---|
| work/acceptance/m0X_final_report.md | - | Создаётся init_milestone.py из зарегистрированного шаблона | автомат (событие) | реестр шаблонов и git |
| milestones.md | work_state | Меняется на `in-progress` | владелец вручную | check.py: milestones |
| project_status.md | текущий этап, файлы задач | Обновляется | автомат (generate.py) | check.py: generated |

## Когда milestone переходит из in-progress → completed

| Файл | Поле | Действие | Кто/Как | Проверка |
|---|---|---|---|---|
| work/acceptance/m0X_final_report.md | весь файл | Перегенерируется из состояния репозитория и зарегистрированного шаблона; разделы 6-7 сохраняются из ранее записанного файла | update_completion_report.py, запускается **после** коммита с `work_state: completed` | template registry и check.py: metadata |
| milestones.md | work_state | Меняется на `completed` | владелец вручную | check.py: milestones |
| project_status.md | Прогресс | Обновляется | автомат (generate.py) | check.py: generated |

## Зависимости по типам файлов

### work/acceptance/m0X_final_report.md
- **Зависит от:** milestones.md (work_state), work/tasks/* и work/tests/* этапа, состав требований этапа (`scope` в milestones.md), git-история изменений файлов между стартом и принятием этапа
- **Влияет на:** ничего не читает его содержимое автоматически — файл предназначен для владельца/агента, читающего репозиторий
- **Поля синхронизации:**
  - completion_state: должна соответствовать work_state
  - Содержимое разделов 1–5: пересчитывается целиком при каждом запуске update_completion_report.py, вручную не редактируется
  - updated: должна быть текущей датой при изменении

Файлы owner_checklist.md и semantic_review.md не создаются автоматически для каждого этапа: они пишутся вручную только когда этапу нужна запись сверх того, что уже описывают [`operations/acceptance.md`](../acceptance.md) и [`operations/semantic_review.md`](../semantic_review.md).

### project_status.md
- **Зависит от:** milestones.md, work/tasks/*, work/tests/*
- **Генерируется:** render_repository_project_status() в operations/scripts/status/human_status.py
- **Проверка:** check.py: generated (drift check), check.py: owner_interface (запрещённые внутренние детали)
- Файлы, поставленные TASK за пределы собственной карточки, в [`project_status.md`](../../project_status.md) не перечисляются: их границы фиксируются в `allowed_paths` и разделе «6. Состав» самой TASK.

  `allowed_paths` содержит только сами пути (маски, каталоги, файлы), без дополнительного текста — что представляет собой конкретный файл, описывается в разделе «6. Состав» карточки TASK, а не в самом списке путей.

### Диагностические представления

Индексы Markdown/не-Markdown файлов, дерево репозитория, каталог тестов и матрица трассировки не являются постоянными источниками истины и не коммитятся. Их renderer-функции могут использоваться проверками как on-demand представления в памяти или во временном каталоге. Добавление постоянного выхода требует отдельного зарегистрированного шаблона и явного решения владельца.

## Процедура обновления при завершении milestone

1. **Владелец:** даёт команду `ПРИНИМАЮ m0X` в диалоге
2. **acceptance.py:** 
   - Меняет work_state в milestones.md на `completed`
3. **Агент (после коммита принятия, до открытия запроса на слияние — см. [`operations/acceptance.md`](../acceptance.md#4-после-выполнения)):**
   - update_completion_report.py: пересобирает work/acceptance/m0X_final_report.md из состояния репозитория на этот момент
   - generate.py: перегенерирует project_status.md
   - increment_file_version.py: обновляет версии изменённых файлов
4. **check.py:** Валидирует что:
   - completion_state соответствует work_state
   - зарегистрированные генерируемые файлы синхронизированы
   - Версии актуальны

## Чек-лист для добавления нового milestone

При создании нового milestone m0X должны быть:
- [ ] work/acceptance/m0X_final_report.md (создаётся автоматически init_milestone.py)
- [ ] Запись в milestones.md с work_state: planned
- [ ] Профиль в operations/quality_registry.json если in-progress/completed
- [ ] Процедура обновления completion_state (update_completion_report.py)

## Проверка полноты

```bash
# Валидировать все зависимости
python3.12 operations/scripts/documents/check.py --all

# Проверить дрифт зарегистрированного owner status
python3.12 operations/scripts/documents/generate.py --all && git status

# Проверить completion_state соответствие work_state
python3.12 -c "
from pathlib import Path
from operations.scripts.status.generate_project_status import collect_milestones

data = collect_milestones(Path('.'))
for m in data['items']:
    report = Path('work/acceptance') / f"{m['id']}_final_report.md"
    if report.exists():
        content = report.read_text()
        has_completed = 'completion_state: completed' in content
        should_be_completed = m['work_state'] == 'completed'
        match = '✅' if has_completed == should_be_completed else '❌'
        print(f'{match} {m[\"id\"]}: work_state={m[\"work_state\"]}, completion_state={has_completed}')
"
```
