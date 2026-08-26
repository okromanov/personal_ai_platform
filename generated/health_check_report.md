<!-- generated file: do not edit manually -->
---
id: health_check_latest
type: generated_health_check
generation_state: generated
generated_at: 2026-08-26T12:40:00Z
version: 2.2
updated: 2026-08-25
---

# 🏥 Repository Health Check Report
## `okromanov/personal_ai_platform`

> **Актуальность:** это исторический снимок запуска, а не подтверждение текущей ревизии. Достоверный результат для точного SHA создаётся в `runtime/health_check_report.md` каноническим `run_suite.py` и хранится как artifact успешного запуска `Project check`; отсутствие такого artifact означает `INCOMPLETE`.


---

## ✅ Результаты проверок

### 1. **Тестирование**
- **Статус:** ✅ PASSED
- **Пройдено/Провалено:** 421/421
- **Время выполнения:** 55.61s
- **Охват:** 84.8%

### 2. **Проверка типов (MyPy)**
- **Статус:** ✅ SUCCESS (0 issues)
- **Результат:** Проверка типов прошла успешно

### 3. **Форматирование кода (Ruff)**
- **Статус:** ✅ COMPLIANT
- **Линтер:** E, F, W правила
- **Статус:** Все файлы соответствуют формату

### 4. **Git Статус**
- **Рабочая копия:** ✅ Чистая
- **Remote URL:** https://github.com/okromanov/personal_ai_platform
- **Коммитов:** 187

### 5. **Недавние коммиты**
```
8a15c3b Покрыть тестами новые ветки owner_followups в check.py/generate.py
5f7c0db Добавить owner_followups: неблокирующий бэклог владельца в карточках TASK
3ae0df4 AGENTS.md: закрепить запрет менять именование/шаблоны без согласования
7d18c2d Обновить generated/health_check_report.md после переименования dockerfile
4b16948 Переименовать Dockerfile в dockerfile: соблюсти lower_snake_case без исключений
```

### 6. **Политика покрытия (pyproject.toml)**
- **Статус:** ✅ PASSED
```
overall: 84.80% (minimum 75.00%)
operations/scripts/acceptance/apply.py: 86.16% (minimum 85.00%)
operations/scripts/evidence/generate_bundle.py: 87.72% (minimum 85.00%)
operations/scripts/evidence/record.py: 94.12% (minimum 85.00%)
operations/scripts/quality/record_quality_suite.py: 85.92% (minimum 85.00%)
operations/scripts/quality/registry.py: 92.13% (minimum 85.00%)
```


---

## 🎯 Результаты по категориям

### Code Quality (Качество кода)
| Аспект | Статус | Комментарий |
|--------|--------|-----------|
| Type Safety | ✅ | MyPy: 0 issues |
| Linting | ✅ | Ruff: compliant |
| Formatting | ✅ | All files compliant |
| Tests | ✅ | 421 passed |
| Coverage policy | ✅ | 84.8% overall — policy passed |

### Repository Management (Управление репозиторием)
| Аспект | Статус | Состояние |
|--------|--------|----------|
| Size | ✅ | 3394 KB (.git), 26.7 MB (total) |
| Branches | ✅ | 6 branches |
| Remote | ✅ | https://github.com/okromanov/personal_ai_platform |
| Working Tree | ✅ | Clean |
| Commits | ✅ | 187 commits |

---

## ✨ Главное

Текущий снимок показывает стабильную базу: обязательные проверки прошли, а три модуля находятся близко к порогу покрытия и требуют внимания при следующих изменениях.

---

## 🎓 Рекомендации

### Уровень 1: Критично (High Priority)
- Критичных проблем не обнаружено.

### Уровень 2: Рассмотреть (Medium Priority)
- Близко к порогу покрытия — operations/scripts/acceptance/apply.py: 86.2% (порог 85%).
- Близко к порогу покрытия — operations/scripts/evidence/generate_bundle.py: 87.7% (порог 85%).
- Близко к порогу покрытия — operations/scripts/quality/record_quality_suite.py: 85.9% (порог 85%).

### Уровень 3: Наблюдать (Low Priority)
- Следить за ростом размера репозитория и `.git`.
- Поддерживать актуальность зависимостей (operations/quality/requirements_dev.txt).
- Отслеживать время выполнения тестов на предмет роста.

---

