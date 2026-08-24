<!-- generated file: do not edit manually -->
---
id: health_check_latest
type: generated_health_check
generation_state: generated
version: 1.0
updated: 2026-08-24
---

# 🏥 Repository Health Check Report
## `okromanov/personal_ai_platform`

**Дата проверки:** 24 August 2026
**Ветка:** claude/repo-checks-health-analysis-iu0tb8
**Общее состояние:** ⚠️ NEEDS ATTENTION

---

## 📊 Основные метрики

| Метрика | Значение | Статус |
|---------|---------|--------|
| **Всего коммитов** | 115 | ✅ |
| **Размер репозитория (.git)** | 1347 KB | ✅ |
| **Размер проекта** | 25.1 MB | ✅ |
| **Python файлов** | 111 | ✅ |
| **Строк кода** | 20,241 | ✅ |
| **Тесты (пройдено/всего)** | 314 passed | ✅ |
| **Ветки** | 4 | ✅ |

---

## ✅ Результаты проверок

### 1. **Тестирование**
- **Статус:** ✅ PASSED
- **Пройдено/Провалено:** 314/314
- **Время выполнения:** 34.63s
- **Охват:** 82.7%

### 2. **Проверка типов (MyPy)**
- **Статус:** ✅ SUCCESS (0 issues)
- **Результат:** Проверка типов прошла успешно

### 3. **Форматирование кода (Ruff)**
- **Статус:** ✅ COMPLIANT
- **Линтер:** E, F, W правила
- **Статус:** Все файлы соответствуют формату

### 4. **Git Статус**
- **Рабочая копия:** ❌ Имеются изменения
- **Remote URL:** https://github.com/okromanov/personal_ai_platform
- **Коммитов:** 115

### 5. **Недавние коммиты**
```
f1809f9 Regenerate health check report against the fixed metrics collector
964b24a Fix health-check metrics: stale test count and asterisked branch name
3c8ffb5 Merge pull request #25 from okromanov/claude/non-md-file-index
ed9e5b4 Русские описания в test_catalog.md, единообразные вступления markdown/non_markdown индексов
35c242f Переименовать document_index.md в markdown_index.md, доработать non_markdown_index.md, пересобрать m01_final_report.md
```

### 6. **Политика покрытия (pyproject.toml)**
- **Статус:** ✅ PASSED
```
overall: 82.70% (minimum 75.00%)
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
| Tests | ✅ | 314 passed |
| Coverage policy | ✅ | 82.7% overall — policy passed |

### Repository Management (Управление репозиторием)
| Аспект | Статус | Состояние |
|--------|--------|----------|
| Size | ✅ | 1347 KB (.git), 25.1 MB (total) |
| Branches | ✅ | 4 branches |
| Remote | ✅ | https://github.com/okromanov/personal_ai_platform |
| Working Tree | ❌ | Has changes |
| Commits | ✅ | 115 commits |

---

## ✨ Сильные стороны

- ✅ Comprehensive Python codebase (111 files, 20,241 LOC)
- ✅ Test coverage at 82.7%
- ✅ Type-safe codebase (MyPy: 0 issues)
- ✅ Clean git history (115 commits)
- ✅ Formatted according to standards
- ✅ Regular commits and clean working tree

---

## 🎓 Рекомендации

### Уровень 1: Критично (High Priority)
- Критичных проблем не обнаружено.

### Уровень 2: Рассмотреть (Medium Priority)
- В рабочем дереве есть незакоммиченные изменения — отчёт снят на грязном дереве.
- Близко к порогу покрытия — operations/scripts/acceptance/apply.py: 86.2% (порог 85%).
- Близко к порогу покрытия — operations/scripts/evidence/generate_bundle.py: 87.7% (порог 85%).
- Близко к порогу покрытия — operations/scripts/quality/record_quality_suite.py: 85.9% (порог 85%).

### Уровень 3: Наблюдать (Low Priority)
- Следить за ростом размера репозитория и `.git`.
- Поддерживать актуальность зависимостей (operations/quality/requirements_dev.txt).
- Отслеживать время выполнения тестов на предмет роста.

---

## 📝 Заключение

**Статус репозитория: ⚠️ NEEDS ATTENTION**

Репозиторий находится в требующем внимания состоянии с точки зрения:
- ✅ Качества кода (type safety, linting)
- ✅ Тестирования (314 passed)
- ✅ Форматирования
- ✅ Политики покрытия (pyproject.toml: overall/critical modules)
- ❌ Управления (git hygiene, commits)

**Рекомендация:** ⚠️ Устраните пункты из раздела «Рекомендации» перед продолжением.

---

**Сгенерировано:** Claude Code
**Версия отчета:** 1.0
**Время проверки:** 2026-08-24T20:40:18.438194Z
