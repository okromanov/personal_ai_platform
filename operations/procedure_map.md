---
id: operations_procedure_map
type: operations
document_state: current
applicability: normative
version: 2.7
updated: 2026-09-09
depends_on:
  - operations_change_process
  - coding_agent_instruction
---

# Карта операционных процедур

## 1. Точка входа

Единственный маршрут начала работы:

1. открыть [`project_status.md`](../project_status.md);
2. перейти в указанную TASK или этапный рубеж;
3. выбрать процедуру из таблицы ниже;
4. завершить изменение через PR и подтверждённый CI по [`change_process.md`](change_process.md).

Корневой `README` не используется. Pre-commit hook обязателен; инструкции установки находятся в [`setup_precommit.md`](setup_precommit.md).

## 2. Карта процедур

| Ситуация | Источник | Результат |
|---|---|---|
| Любое изменение и публикация | [`change_process.md`](change_process.md) | Проверенный PR без прямой записи в `main` |
| Решение или замена ADR | [`adr_lifecycle.md`](lifecycle/adr_lifecycle.md) | Явное решение владельца и трассировка |
| Переход состояния | [`state_machines.md`](lifecycle/state_machines.md) | Допустимый переход по машинному контракту |
| Проверка смысла документов | [`semantic_review.md`](semantic_review.md) | Список противоречий или подтверждение |
| Принятие этапа | [`acceptance.md`](acceptance.md) | SHA-bound решение владельца |
| Зависимые файлы при правке | [`file_update_dependencies.md`](procedures/file_update_dependencies.md) | Полный связный diff |
| Зависшая sensitive-action lock | [`recover_stale_sensitive_action_lock.md`](procedures/recover_stale_sensitive_action_lock.md) | Безопасное ручное восстановление |
| Полный quality gate | [`readme.md`](quality/playbooks/readme.md) | Выбран канонический профиль и evidence |
| Детальные правила документации | [`documentation_rules_detailed.md`](quality/playbooks/documentation_rules_detailed.md) | Однозначная структура и ссылки |
| Диагностика health report | [`module_guide.md`](scripts/health_check/module_guide.md) | Воспроизводимый health snapshot |
| Полный аудит репозитория | [`repository_audit_system_prompt.md`](repository_audit_system_prompt.md) | Report, findings и self-check |
| Архитектурная SVG-схема | [`diagram_geometry_foundations.md`](architecture/diagram_geometry_foundations.md) → [`architecture_diagram_style_guide.md`](architecture/architecture_diagram_style_guide.md) | Проверенная схема |
| Процессная SVG/PPTX-схема | [`diagram_geometry_foundations.md`](architecture/diagram_geometry_foundations.md) → [`process_diagram_style_guide.md`](architecture/process_diagram_style_guide.md) | Проверенная схема |
| Threat review | [`threat_review_triggers.md`](policy/threat_review_triggers.md) | Решение об инциденте и дальнейшее действие |
| Лицензирование | [`license_policy.md`](policy/license_policy.md) | Понимание режима распространения |
| Пример TASK | [`sample_task_lifecycle.md`](examples/sample_task_lifecycle.md) | Справочный пример без копирования истории |

## 3. Типовые сценарии

### Разработка по TASK

1. Проверить `allowed_paths`, зависимости и критерий результата.
2. Изменить реализацию, TEST и необходимые первичные документы.
3. Запустить `python3.12 operations/scripts/quality/run_suite.py full`.
4. Запустить обязательный pre-commit, открыть PR, дождаться зелёного CI.
5. Обновить TASK только фактическим результатом и evidence.

### Служебная правка

1. Не создавать TASK.
2. Обновить версию и дату изменённых первичных документов.
3. Выполнить полный gate и тот же PR-маршрут.

### Ошибка CI

1. Привязать сбой к job, шагу и SHA.
2. Воспроизвести тот же профиль локально, если среда доступна.
3. Исправить причину или явно зафиксировать недоступность; не ослаблять проверку.
4. Отправить новый коммит в тот же PR и дождаться результата.

### Завершение этапа

1. Подтвердить все terminal-outcome TASK и TEST.
2. Провести [`semantic_review.md`](semantic_review.md).
3. Выполнить [`acceptance.md`](acceptance.md) только на проверенном SHA.

## 4. Быстрый выбор

| Нужно | Команда или маршрут |
|---|---|
| Проверить документацию | `python3.12 operations/scripts/documents/check.py --all` |
| Пересобрать производные файлы | `python3.12 operations/scripts/documents/generate.py --all` |
| Выполнить полный gate | `python3.12 operations/scripts/quality/run_suite.py full` |
| Проверить только быстрые инварианты | `python3.12 operations/scripts/documents/check.py --fast` |
| Добавить требование | requirement wizard → apply requirements → generate → full gate |
| Принять этап | semantic review → acceptance → отдельный PR |

## 5. Частые ошибки

- Редактировать [`project_status.md`](../project_status.md) вручную вместо генерации.
- Записывать напрямую в `main` или считать локальный успех серверным evidence.
- Копировать общие правила в TASK/TEST вместо ссылки на источник.
- Добавлять служебные, audit или governance-файлы в продуктовую TASK.
- Менять защищённую структуру без разрешённой миграции checker/tests и экземпляров.
- Использовать неканонический Python launcher вместо значения из [`document_contracts.json`](document_contracts.json).
- Оставлять существующий документ недоступным из этой карты или другого действующего источника.
