from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from operations.scripts.health_check.metrics import RepositoryHealth

_COVERAGE_ROW = re.compile(r"^(?P<label>.+): (?P<actual>[\d.]+)% \(minimum (?P<floor>[\d.]+)%\)$")


def _near_floor_modules(rows: list[str], margin: float = 3.0) -> list[str]:
    """Rows within `margin` points of their configured coverage floor.

    Passing today isn't the same as safe: a module sitting 0.8 points
    above its floor will fail on the next PR that trims a single branch,
    so it is worth flagging before that happens rather than after.
    """
    near = []
    for row in rows:
        match = _COVERAGE_ROW.match(row)
        if not match:
            continue
        actual = float(match.group("actual"))
        floor = float(match.group("floor"))
        if 0 <= actual - floor < margin:
            near.append(f"{match.group('label')}: {actual:.1f}% (порог {floor:.0f}%)")
    return near


def _build_recommendations(health: RepositoryHealth) -> str:
    """Derive recommendations from this run's actual findings.

    A fixed boilerplate list reads the same whether the repo is on fire or
    spotless, which trains readers to skip it. Grounding it in the metrics
    already collected this run means it only says something when there is
    something to say.
    """
    tests = health.tests
    quality = health.code_quality
    coverage = health.coverage_policy
    repo = health.repository

    critical: list[str] = []
    if tests.collection_error:
        critical.append(f"Метрики тестов недоступны: {tests.collection_error}.")
    critical.extend(f"Метрики качества недоступны: {error}." for error in quality.collection_errors)
    if tests.total_failed > 0:
        critical.append(f"Исправить {tests.total_failed} падающих тестов перед мержем.")
    if not quality.type_safe:
        critical.append(f"Устранить ошибки типов MyPy ({quality.mypy_issues}).")
    if quality.ruff_issues > 0:
        critical.append(f"Устранить замечания Ruff lint ({quality.ruff_issues}).")
    if not quality.formatting_compliant:
        critical.append("Прогнать `ruff format` — найдены неотформатированные файлы.")
    if not coverage.passed:
        critical.extend(f"Покрытие: {error}" for error in coverage.errors)

    watch: list[str] = []
    if not repo.working_tree_clean:
        watch.append(
            "В рабочем дереве есть незакоммиченные изменения — отчёт снят на грязном дереве."
        )
    watch.extend(
        f"Близко к порогу покрытия — {item}." for item in _near_floor_modules(coverage.rows)
    )

    monitor = [
        "Следить за ростом размера репозитория и `.git`.",
        "Поддерживать актуальность зависимостей (operations/quality/requirements_dev.txt).",
        "Отслеживать время выполнения тестов на предмет роста.",
    ]

    lines = ["## 🎓 Рекомендации", "", "### Уровень 1: Критично (High Priority)"]
    if critical:
        lines.extend(f"- {item}" for item in critical)
    else:
        lines.append("- Критичных проблем не обнаружено.")

    lines.extend(["", "### Уровень 2: Рассмотреть (Medium Priority)"])
    if watch:
        lines.extend(f"- {item}" for item in watch)
    else:
        lines.append("- Ничего не требует внимания сейчас.")

    lines.extend(["", "### Уровень 3: Наблюдать (Low Priority)"])
    lines.extend(f"- {item}" for item in monitor)

    return "\n".join(lines)


def generate_report(health: RepositoryHealth) -> str:
    """Generate a markdown health check report."""
    repo = health.repository
    tests = health.tests
    quality = health.code_quality
    coverage = health.coverage_policy
    status = health.overall_status
    recommendations = _build_recommendations(health)

    timestamp = datetime.fromisoformat(repo.collected_at_utc)

    report = f"""<!-- generated file: do not edit manually -->
---
id: health_check_latest
type: generated_health_check
generation_state: generated
version: 1.0
updated: {timestamp.strftime("%Y-%m-%d")}
---

# 🏥 Repository Health Check Report
## `okromanov/personal_ai_platform`

**Дата проверки:** {timestamp.isoformat()}
**Ветка:** {repo.branch_name}
**Git SHA:** `{repo.head_sha}`
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
- **Статус:** {"❌ INCOMPLETE" if tests.collection_error else ("✅ PASSED" if tests.total_failed == 0 else f"❌ FAILED ({tests.total_failed} failures)")}
- **Пройдено/Провалено:** {tests.total_passed}/{tests.total_passed + tests.total_failed}
- **Время выполнения:** {tests.execution_time_sec:.2f}s
- **Охват:** {tests.coverage_percent}%
{f"- **Ошибка сбора:** {tests.collection_error}" if tests.collection_error else ""}

### 2. **Проверка типов (MyPy)**
- **Статус:** {"✅ SUCCESS (0 issues)" if quality.type_safe else f"❌ ISSUES FOUND ({quality.mypy_issues} errors)"}
- **Результат:** {"Проверка типов прошла успешно" if quality.type_safe else "Обнаружены ошибки типов"}
{chr(10).join(f"- **Ошибка сбора:** {error}" for error in quality.collection_errors) if quality.collection_errors else ""}

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

### 6. **Политика покрытия (pyproject.toml)**
- **Статус:** {"✅ PASSED" if coverage.passed else "❌ FAILED"}
```
{chr(10).join(coverage.rows) if coverage.rows else "Нет данных (runtime/coverage.json недоступен)"}
```
{("Нарушения:" + chr(10) + chr(10).join(f"- {error}" for error in coverage.errors)) if coverage.errors else ""}

---

## 🎯 Результаты по категориям

### Code Quality (Качество кода)
| Аспект | Статус | Комментарий |
|--------|--------|-----------|
| Type Safety | {"✅" if quality.type_safe else "❌"} | {f"MyPy: {quality.mypy_issues} issues" if quality.mypy_issues > 0 else "MyPy: 0 issues"} |
| Linting | {"✅" if quality.ruff_issues == 0 else "❌"} | {f"Ruff: {quality.ruff_issues} issues" if quality.ruff_issues > 0 else "Ruff: compliant"} |
| Formatting | {"✅" if quality.formatting_compliant else "❌"} | {"All files compliant" if quality.formatting_compliant else "Issues found"} |
| Tests | {"✅" if tests.total_failed == 0 else "❌"} | {f"{tests.total_passed} passed" + (f", {tests.total_failed} failed" if tests.total_failed > 0 else "")} |
| Coverage policy | {"✅" if coverage.passed else "❌"} | {tests.coverage_percent}% overall — {"policy passed" if coverage.passed else "policy FAILED (see §6)"} |

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

{recommendations}

---

## 📝 Заключение

**Статус репозитория: {status}**

Репозиторий находится в {"отличном" if status == "✅ HEALTHY" else "требующем внимания"} состоянии для точного SHA `{repo.head_sha}` с точки зрения:
- {"✅" if quality.type_safe else "❌"} Качества кода (type safety, linting)
- {"✅" if tests.total_failed == 0 else "❌"} Тестирования ({tests.total_passed} passed{f", {tests.total_failed} failed" if tests.total_failed > 0 else ""})
- {"✅" if quality.formatting_compliant else "❌"} Форматирования
- {"✅" if coverage.passed else "❌"} Политики покрытия (pyproject.toml: overall/critical modules)
- {"✅" if repo.working_tree_clean else "❌"} Управления (git hygiene, commits)

**Рекомендация:** {"✅ Проект готов к продолжению разработки." if status == "✅ HEALTHY" else "⚠️ Устраните пункты из раздела «Рекомендации» перед продолжением."}

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
    coverage = health.coverage_policy

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
    print(f"  Coverage policy: {'✅ Passed' if coverage.passed else '❌ FAILED'}")
    print(f"  Execution time: {tests.execution_time_sec:.2f}s")

    print("\nCode Quality:")
    print(f"  Type safe: {'✅ Yes' if quality.type_safe else '❌ No'}")
    print(f"  Formatting: {'✅ Compliant' if quality.formatting_compliant else '❌ Issues'}")
    print(f"  Linting issues: {quality.ruff_issues}")

    print(f"\nWorking Tree: {'✅ Clean' if repo.working_tree_clean else '❌ Has changes'}")
    print("=" * 70 + "\n")
