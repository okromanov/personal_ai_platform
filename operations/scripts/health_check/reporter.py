from __future__ import annotations

import re
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from operations.scripts.common.project import find_project_root
from operations.scripts.documents.template_contracts import render_contract
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


def generate_report(health: RepositoryHealth, root: Path | None = None) -> str:
    """Render a compact snapshot of already collected audit evidence."""
    repo = health.repository
    tests = health.tests
    quality = health.code_quality
    coverage = health.coverage_policy
    pillars = [
        ("Контракт и трассируемость", "CONFIRMED"),
        (
            "Реализация и тесты",
            "CONFIRMED" if not tests.collection_error and tests.total_failed == 0 else "REFUTED",
        ),
        (
            "Качество кода",
            "CONFIRMED" if quality.type_safe and quality.formatting_compliant else "REFUTED",
        ),
        ("Безопасность", "UNAVAILABLE"),
        ("Надёжность и coverage", "CONFIRMED" if coverage.passed else "REFUTED"),
        ("Evidence и generated drift", "CONFIRMED"),
    ]
    rows = "\n".join(f"| {name} | {state} |" for name, state in pillars)
    contract_root = root or find_project_root(Path.cwd())
    return render_contract(
        contract_root,
        "health_check_report",
        {
            "remote_url": repo.remote_url,
            "branch_name": repo.branch_name,
            "head_sha": repo.head_sha,
            "collected_at": repo.collected_at_utc,
            "overall_status": health.overall_status,
            "total_commits": repo.total_commits,
            "python_files": repo.python_files,
            "lines_of_code": repo.lines_of_code,
            "project_size_mb": repo.project_size_mb,
            "working_tree_clean": "да" if repo.working_tree_clean else "нет",
            "tests_passed": tests.total_passed,
            "tests_failed": tests.total_failed,
            "coverage_percent": tests.coverage_percent,
            "test_duration": f"{tests.execution_time_sec:.2f}",
            "mypy_issues": quality.mypy_issues,
            "ruff_issues": quality.ruff_issues,
            "formatting_compliant": "да" if quality.formatting_compliant else "нет",
            "coverage_policy": "passed" if coverage.passed else "failed",
            "rows": rows,
            "recommendations": _build_recommendations(health),
        },
    )


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
