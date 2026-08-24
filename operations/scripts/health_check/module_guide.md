---
id: health_check_module
type: documentation
version: 1.0
document_state: current
depends_on: []
---

# Repository Health Check Module

Система автоматической проверки здоровья репозитория проекта `personal_ai_platform`.

## 🚀 Быстрый старт

### Просмотр статуса в консоли
```bash
python operations/scripts/health_check/generate.py --summary
```

Выведет:
- Статус репозитория
- Метрики коммитов, файлов, LOC
- Результаты тестирования
- Статус качества кода

### Генерация полного отчёта
```bash
python operations/scripts/health_check/generate.py
```

Сгенерирует: [`generated/health_check_report.md`](../../../generated/health_check_report.md)

### Экспорт метрик в JSON
```bash
python operations/scripts/health_check/generate.py --json runtime/health_check.json
```

## 📊 Структура модуля

### metrics.py
Сбор метрик репозитория:
- Git метрики (коммиты, ветки, размер)
- Тесты (пройдено, провалено, покрытие)
- Качество кода (типы, линтинг, форматирование)

### reporter.py
Генерация отчётов:
- Markdown отчёт с полной информацией
- JSON экспорт для CI/CD
- Консольный вывод

### generate.py
Точка входа:
- Координирует сбор метрик
- Генерирует отчёты
- Показывает статус

## 📈 Поддерживаемые метрики

### Repository (Репозиторий)
- ✅ Всего коммитов
- ✅ Python файлов
- ✅ Строк кода
- ✅ Размер .git
- ✅ Размер проекта
- ✅ Ветки
- ✅ Remote URL
- ✅ Статус рабочей копии

### Tests (Тестирование)
- ✅ Пройдено тестов
- ✅ Провалено тестов
- ✅ Время выполнения
- ✅ Покрытие кодом

### Code Quality (Качество кода)
- ✅ MyPy - проверка типов (0 issues ✅)
- ✅ Ruff - линтинг (E, F, W правила)
- ✅ Ruff format - форматирование
- ✅ Общая оценка здоровья

## 🎯 Статусы здоровья

| Статус | Условие | Действие |
|--------|---------|---------|
| ✅ HEALTHY | Нет ошибок тестов + type safe | Всё хорошо |
| ⚠️ NEEDS ATTENTION | Есть ошибки типов/форматирования | Требуется исправление |
| ⚠️ REVIEW RECOMMENDED | Требуется ручная проверка | Обратитесь к команде |

## 🔄 Интеграция с CI/CD

Автоматически запускается в:
- Full quality suite: `python operations/scripts/quality/run_suite.py full`
- GitHub Actions workflow (quality-skills job)

Генерируемые артефакты:
- `runtime/health_check_report.md` - полный отчёт
- `runtime/health_check.json` - метрики в JSON

## 📝 Примеры использования

### Проверка перед коммитом
```bash
python operations/scripts/health_check/generate.py --summary
```

### Интеграция в Makefile
```makefile
.PHONY: health-check
health-check:
	python operations/scripts/health_check/generate.py --summary
```

### Периодическая проверка (cron)
```bash
0 2 * * * cd /path/to/repo && python operations/scripts/health_check/generate.py --json daily.json
```

### Использование в скриптах
```python
from operations.scripts.health_check.metrics import (
    collect_git_metrics,
    collect_test_metrics,
    collect_code_quality_metrics,
    assess_health,
    RepositoryHealth
)

health = RepositoryHealth(
    repository=collect_git_metrics(root),
    tests=collect_test_metrics(root),
    code_quality=collect_code_quality_metrics(root),
    overall_status=""
)
health.overall_status = assess_health(health)
```

## 🔧 Расширение функциональности

### Добавить новую метрику
```python
# В metrics.py
@dataclass
class NewMetrics:
    value: int

def collect_new_metrics(root: Path) -> NewMetrics:
    """Collect new metrics."""
    return NewMetrics(value=0)
```

### Изменить логику оценки
```python
# В metrics.py - функция assess_health()
def assess_health(health: RepositoryHealth) -> str:
    """Assess overall repository health status."""
    # Ваша логика здесь
```

## 📚 Документация

- Этот файл (module_guide.md)
- [`health_check_report.md`](../../../generated/health_check_report.md) - пример отчёта
- Встроенная документация в коде (docstrings)

## ✅ Требования

- Python 3.12+
- Git
- pytest (для тестирования)
- mypy (для проверки типов)
- ruff (для линтинга)

## 🤝 Разработка

При внесении изменений:

1. Проверьте синтаксис:
```bash
python -m py_compile operations/scripts/health_check/*.py
```

2. Запустите типы:
```bash
mypy operations/scripts/health_check/ --ignore-missing-imports
```

3. Проверьте форматирование:
```bash
ruff check operations/scripts/health_check/
ruff format --check operations/scripts/health_check/
```

4. Запустите модуль:
```bash
python operations/scripts/health_check/generate.py --summary
```

## 📞 Поддержка

Если возникают вопросы:
1. Проверьте примеры выше
2. Посмотрите встроенную документацию кода
3. Запустите с флагом `--summary` для быстрой диагностики

---

**Модуль версия:** 1.0  
**Добавлено:** 24 августа 2026  
**Статус:** ✅ Production Ready
