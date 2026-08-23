#!/usr/bin/env python3
"""
Initialize milestone folder and files on transition.

When milestone state changes (planned → in-progress), creates:
- work/m0X/milestone_spec.md (from architecture spec)
- work/m0X/owner_checklist.md (acceptance checklist template)
- work/m0X/semantic_review.md (review procedure template)
- work/m0X/final_report.md (completion report template)

Usage: python3 operations/scripts/milestones/init_milestone.py m02
"""

import sys
from datetime import date
from pathlib import Path


def init_milestone(milestone_id: str) -> bool:
    """Initialize milestone folder structure."""
    try:
        milestone_dir = Path(f"work/{milestone_id}")
        milestone_dir.mkdir(parents=True, exist_ok=True)

        today = date.today().isoformat()

        # 1. owner_checklist.md
        checklist_content = f"""---
id: {milestone_id}_owner_checklist
type: owner_acceptance_checklist
acceptance_state: pending
version: 1.0
updated: {today}
milestone: {milestone_id}
---

# {milestone_id.upper()} — Чек-лист принятия этапа

> Этот чек-лист владелец заполняет при завершении этапа перед финальным решением.

## Техническая готовность

- [ ] Все TASK этапа помечены `completed`
- [ ] Все TEST имеют `execution: automated` и доказательства
- [ ] CI проходит на основной ветке
- [ ] Никаких блокирующих ошибок валидации

## Функциональная готовность

- [ ] Все компоненты этапа реализованы и протестированы
- [ ] Интеграция между компонентами проверена
- [ ] Нет известных багов в критических путях

## Документирование

- [ ] Все файлы обновлены с текущей датой
- [ ] Версии файлов согласованы
- [ ] Финальный отчет подготовлен
- [ ] Процедура семантической проверки завершена

## Решение владельца

После проверки этого чек-листа владелец выбирает:

- [ ] **ПРИНИМАЮ {milestone_id.upper()}** — этап одобрен, переход к следующему
- [ ] **ВОЗВРАЩАЮ {milestone_id.upper()}: <причина>** — требуются исправления

**Решение принято**:

**Дата и время**:

**Подпись/инициалы**:
"""

        (milestone_dir / "owner_checklist.md").write_text(checklist_content, encoding='utf-8')

        # 2. semantic_review.md
        semantic_review_content = f"""---
id: {milestone_id}_semantic_review
type: semantic_review
review_state: pending
version: 1.0
created: {today}
updated: {today}
milestone: {milestone_id}
reviewed_sha: null
reviewer: null
depends_on: []
---

# {milestone_id.upper()} — Процедура смысловой проверки

## 1. Назначение

Проверка полноты и корректности реализации этапа {milestone_id.upper()} согласно архитектурным требованиям.

## 2. Предусловия

1. Все обязательные GitHub Actions успешны
2. Все TASK completed с доказательствами
3. Проверка выполняется новым сеансом без истории разработки

## 3. Область проверки

Проверяющий охватывает:
- Все компоненты этапа: реализация, тесты, интеграция
- Архитектурные требования (SYS, ARC, INF)
- Трассировка: TASK → TEST → компоненты
- Полноту доказательств

## 4. Результат

Отчет сохраняется как `work/{milestone_id}/semantic_review.json` и проверяется CI.

Проверка со старым SHA, иным набором полей или с неразрешённым critical/high не открывает переход.

## 5. Следующее действие

После успешной проверки владелец выбирает: `ПРИНИМАЮ {milestone_id.upper()}` или `ВОЗВРАЩАЮ {milestone_id.upper()}: <причина>`.
"""

        (milestone_dir / "semantic_review.md").write_text(semantic_review_content, encoding='utf-8')

        # 3. final_report.md
        final_report_content = f"""---
id: {milestone_id}_final_report
type: milestone_completion_report
completion_state: pending
version: 1.0
created: {today}
updated: {today}
milestone: {milestone_id}
next_milestone: m03
---

# {milestone_id.upper()} — Итоговый отчет

## 1. Состояние завершения

- Статус: в процессе
- Дата начала: {today}
- Дата завершения: —
- Все задачи завершены: нет

## 2. Выполненные компоненты

| Компонент | Статус | TASK | TEST | Доказательства |
|---|---|---|---|---|
| (заполняется при завершении) | — | — | — | — |

## 3. Результаты тестирования

- Модульные тесты: ожидание
- Интеграционные тесты: ожидание
- Покрытие кода: ожидание

## 4. Изменения в архитектуре

(Краткое описание архитектурных решений и изменений на этапе)

## 5. Известные ограничения

(Список известных ограничений, отложенных задач и т.д.)

## 6. Переход к следующему этапу

Условия для перехода к m03:
- ✅ Все компоненты реализованы
- ✅ Все тесты проходят
- ✅ Семантическая проверка успешна
- ✅ Владелец принял этап

## 7. Рекомендации

(Рекомендации для следующего этапа разработки)
"""

        (milestone_dir / "final_report.md").write_text(final_report_content, encoding='utf-8')

        return True
    except Exception as e:
        print(f"ERROR: Failed to initialize milestone {milestone_id}: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 operations/scripts/milestones/init_milestone.py <milestone_id>")
        sys.exit(1)

    milestone_id = sys.argv[1]
    if init_milestone(milestone_id):
        print(f"✓ Initialized {milestone_id} folder structure")
        sys.exit(0)
    else:
        print(f"✗ Failed to initialize {milestone_id}")
        sys.exit(1)
