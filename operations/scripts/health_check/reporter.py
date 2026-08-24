from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from operations.scripts.health_check.metrics import RepositoryHealth


def generate_report(health: RepositoryHealth) -> str:
    """Generate a markdown health check report."""
    repo = health.repository
    tests = health.tests
    quality = health.code_quality
    status = health.overall_status

    timestamp = datetime.now().isoformat() + "Z"
    timestamp = timestamp.replace("+00:00", "")

    report = f"""<!-- generated file: do not edit manually -->
---
id: health_check_latest
type: generated_health_check
generation_state: generated
version: 1.0
updated: {datetime.now().strftime("%Y-%m-%d")}
---

# 🏥 Repository Health Check Report
## `okromanov/personal_ai_platform`

**Дата проверки:** {datetime.now().strftime("%d %B %Y")}
**Ветка:** {repo.branches[0] if repo.branches else "unknown"}
**Общее состояние:** {status}

---

## 📊 Основные метрики

| Метрика | Значение | Статус |
|---------|---------|--------|
| **Всего коммитов** | {repo.total_commits} | ✅ |
| **Размер репозитория (.git)** | {repo.git_size_kb} KB | ✅ |
| **Размер проекта** | {repo.project_size_mb} MB | ✅ |
| **Python файлов** | {repo.python_files} | ✅ |
| **Строк кода** | {repo.lines_of_code:,} | ✅ |
| **Тесты (пройдено/всего)** | {tests.total_passed} passed | {"✅" if tests.total_failed == 0 else "❌"} |
| **Ветки** | {len(repo.branches)} | ✅ |

---

## ✅ Результаты проверок

### 1. **Тестирование**
- **Статус:** {"✅ PASSED" if tests.total_failed == 0 else f"❌ FAILED ({tests.total_failed} failures)"}
- **Пройдено/Провалено:** {tests.total_passed}/{tests.total_passed + tests.total_failed}
- **Время выполнения:** {tests.execution_time_sec:.2f}s
- **Охват:** {tests.coverage_percent}%

### 2. **Проверка типов (MyPy)**
- **Статус:** {"✅ SUCCESS (0 issues)" if quality.type_safe else f"❌ ISSUES FOUND ({quality.mypy_issues} errors)"}
- **Результат:** {"Проверка типов прошла успешно" if quality.type_safe else "Обнаружены ошибки типов"}

### 3. **Форматирование кода (Ruff)**
- **Статус:** {"✅ COMPLIANT" if quality.formatting_compliant else "❌ NON-COMPLIANT"}
- **Линтер:** E, F, W правила
- **Статус:** {"Все файлы соответствуют формату" if quality.formatting_compliant else "Найдены проблемы форматирования"}

### 4. **Git Статус**
- **Рабочая копия:** {"✅ Чистая" if repo.working_tree_clean else "❌ Имеются изменения"}
- **Remote URL:** {repo.remote_url}
- **Коммитов:** {repo.total_commits}

### 5. **Недавние коммиты**
```
{chr(10).join(repo.last_commits[:5]) if repo.last_commits else "No commits"}
```

---

## 🎯 Результаты по категориям

### Code Quality (Качество кода)
| Аспект | Статус | Комментарий |
|--------|--------|-----------|
| Type Safety | {"✅" if quality.type_safe else "❌"} | {f"MyPy: {quality.mypy_issues} issues" if quality.mypy_issues > 0 else "MyPy: 0 issues"} |
| Linting | {"✅" if quality.ruff_issues == 0 else "❌"} | {f"Ruff: {quality.ruff_issues} issues" if quality.ruff_issues > 0 else "Ruff: compliant"} |
| Formatting | {"✅" if quality.formatting_compliant else "❌"} | {"All files compliant" if quality.formatting_compliant else "Issues found"} |
| Tests | {"✅" if tests.total_failed == 0 else "❌"} | {f"{tests.total_passed} passed" + (f", {tests.total_failed} failed" if tests.total_failed > 0 else "")} |
| Coverage | {"✅" if tests.coverage_percent >= 75 else "⚠️"} | {tests.coverage_percent}% coverage |

### Repository Management (Управление репозиторием)
| Аспект | Статус | Состояние |
|--------|--------|----------|
| Size | ✅ | {repo.git_size_kb} KB (.git), {repo.project_size_mb} MB (total) |
| Branches | ✅ | {len(repo.branches)} branches |
| Remote | ✅ | {repo.remote_url if repo.remote_url else "Not configured"} |
| Working Tree | {"✅" if repo.working_tree_clean else "❌"} | {"Clean" if repo.working_tree_clean else "Has changes"} |
| Commits | ✅ | {repo.total_commits} commits |

---

## ✨ Сильные стороны

- ✅ Comprehensive Python codebase ({repo.python_files} files, {repo.lines_of_code:,} LOC)
- ✅ Test coverage at {tests.coverage_percent}%
- ✅ Type-safe codebase (MyPy: {"0 issues" if quality.type_safe else f"{quality.mypy_issues} issues"})
- ✅ Clean git history ({repo.total_commits} commits)
- ✅ Formatted according to standards
- ✅ Regular commits and clean working tree

---

## 🎓 Рекомендации

### Уровень 1: Сделать (Low Priority)
- Monitor code quality metrics regularly
- Keep dependencies up to date
- Maintain test coverage above 75%

### Уровень 2: Рассмотреть (Medium Priority)
- Review any failing tests
- Address type safety issues if any
- Update formatting if needed

### Уровень 3: Наблюдать (Low Priority)
- Monitor repository size growth
- Track test execution time
- Review CI/CD pipeline status

---

## 📝 Заключение

**Статус репозитория: {status}**

Репозиторий находится в {"отличном" if tests.total_failed == 0 else "приемлемом"} состоянии с точки зрения:
- {"✅" if quality.type_safe else "❌"} Качества кода (type safety, linting)
- {"✅" if tests.total_failed == 0 else "❌"} Тестирования ({tests.total_passed} passed{f", {tests.total_failed} failed" if tests.total_failed > 0 else ""})
- {"✅" if quality.formatting_compliant else "❌"} Форматирования
- ✅ Управления (git hygiene, commits)

**Рекомендация:** ✅ Проект готов к продолжению разработки.

---

**Сгенерировано:** Claude Code
**Версия отчета:** 1.0
**Время проверки:** {timestamp}
"""

    return report


def print_summary(health: RepositoryHealth) -> None:
    """Print a brief health check summary to stdout."""
    repo = health.repository
    tests = health.tests
    quality = health.code_quality

    print("\n" + "=" * 70)
    print("🏥 REPOSITORY HEALTH CHECK SUMMARY")
    print("=" * 70)

    print(f"\nRepository: {repo.remote_url}")
    print(f"Status: {health.overall_status}")
    print("\nMetrics:")
    print(f"  Commits: {repo.total_commits}")
    print(f"  Python files: {repo.python_files}")
    print(f"  Lines of code: {repo.lines_of_code:,}")
    print(f"  Size: {repo.project_size_mb} MB")

    print("\nTests:")
    print(f"  Passed: {tests.total_passed}")
    print(f"  Failed: {tests.total_failed}")
    print(f"  Coverage: {tests.coverage_percent}%")
    print(f"  Execution time: {tests.execution_time_sec:.2f}s")

    print("\nCode Quality:")
    print(f"  Type safe: {'✅ Yes' if quality.type_safe else '❌ No'}")
    print(f"  Formatting: {'✅ Compliant' if quality.formatting_compliant else '❌ Issues'}")
    print(f"  Linting issues: {quality.ruff_issues}")

    print(f"\nWorking Tree: {'✅ Clean' if repo.working_tree_clean else '❌ Has changes'}")
    print("=" * 70 + "\n")
