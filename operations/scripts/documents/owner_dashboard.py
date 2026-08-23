from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from operations.scripts.common.project import iter_files, today_iso
from operations.scripts.common.status_types import TaskItem
from operations.scripts.documents.traceability import collect_traceable_elements
from operations.scripts.status.generate_project_status import collect_test_specs
from operations.scripts.tasks.generate import collect_tasks

CODE_DIRECTORIES = (
    ("src", "Исходный код продукта (src/)"),
    ("operations/scripts", "Инструментарий (operations/scripts/)"),
    ("operations/tests", "Тесты (operations/tests/)"),
)
DOCUMENT_FAMILIES = (
    ("BR", "Бизнес-требования"),
    ("SYS", "Системные требования"),
    ("THR", "Угрозы"),
    ("SEC_CTL", "Меры безопасности"),
    ("INF_REQ", "Инфраструктурные требования"),
    ("ADR", "ADR"),
)
RESULT_SECTION = re.compile(r"(?ms)^##\s+(?:\d+\.\s*)?Результат\s*$\n(.*?)(?=^##\s|\Z)")


def _count_tracked_files(root: Path) -> int:
    return sum(1 for _ in iter_files(root))


def _lines_of_code(root: Path, directory: str) -> int:
    prefix = f"{directory}/"
    total = 0
    for path in iter_files(root, suffixes={".py"}):
        if path.relative_to(root).as_posix().startswith(prefix):
            try:
                with path.open("r", encoding="utf-8") as handle:
                    total += sum(1 for _ in handle)
            except OSError:
                continue
    return total


def _count_test_cases(root: Path) -> int:
    discovery_root = root / "operations" / "tests"
    if not discovery_root.is_dir():
        return 0
    suite = unittest.TestLoader().discover(
        str(discovery_root), pattern="test_*.py", top_level_dir=str(discovery_root)
    )
    return suite.countTestCases()


def _document_family_counts(root: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in collect_traceable_elements(root).values():
        family = str(record["family"])
        counts[family] = counts.get(family, 0) + 1
    return counts


def _load_json_if_present(path: Path) -> dict[str, object] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _coverage_stat(root: Path) -> tuple[str, str] | None:
    """(процент, время записи) из локального runtime/coverage.json, если он есть.

    runtime/ не хранится в git (см. IGNORED_DIRS в common/project.py), поэтому
    эти данные — как локальный агент/владелец в последний раз запустил
    run_suite.py full, а не гарантированный статус текущего SHA в CI.
    """
    data = _load_json_if_present(root / "runtime" / "coverage.json")
    if data is None:
        return None
    totals = data.get("totals")
    meta = data.get("meta")
    if not isinstance(totals, dict) or not isinstance(meta, dict):
        return None
    percent = totals.get("percent_covered_display")
    timestamp = meta.get("timestamp")
    if percent is None or not isinstance(timestamp, str):
        return None
    return f"{percent}%", timestamp[:19].replace("T", " ")


def _step_timings(root: Path) -> dict[str, float]:
    data = _load_json_if_present(root / "runtime" / "step_timings.json")
    if data is None:
        return {}
    return {key: float(value) for key, value in data.items() if isinstance(value, (int, float))}


def _result_section(body: str) -> str:
    match = RESULT_SECTION.search(body)
    return match.group(1).strip() if match else ""


def _completed_task_results(root: Path) -> list[tuple[TaskItem, str]]:
    tasks = collect_tasks(root)["tasks"]
    return [
        (task, _result_section(str(task["body"])))
        for task in tasks
        if task["work_state"] == "completed"
    ]


def render_owner_dashboard(root: Path, date: str | None = None) -> str:
    """Render owner dashboard: repository statistics and functional readiness.

    Deliberately does not restate current-milestone status, gates or the
    owner's next action — milestones.md and project_status.md already own
    that, and duplicating it here just gives it a second, driftable copy.
    """
    generated_date = date or today_iso()

    total_files = _count_tracked_files(root)
    loc_rows = [(label, _lines_of_code(root, directory)) for directory, label in CODE_DIRECTORIES]
    test_count = _count_test_cases(root)
    coverage = _coverage_stat(root)
    timings = _step_timings(root)

    family_counts = _document_family_counts(root)
    task_count = collect_tasks(root)["count"]
    test_spec_count = collect_test_specs(root)["count"]

    lines = [
        "<!-- generated file: do not edit manually -->",
        "---",
        "id: owner_dashboard",
        "type: operations_guide",
        "document_state: current",
        "version: 2.0",
        f"updated: {generated_date}",
        "depends_on:",
        "  - project_milestones",
        "  - project_rules",
        "  - operations_change_process",
        "  - coding_agent_instruction",
        "---",
        "",
        "# Полный дашборд проекта",
        "",
        "Статистика репозитория и то, что уже реализовано и подтверждено доказательствами. "
        "Для текущего действия используйте [`project_status.md`](project_status.md); "
        "для состава и статуса этапов — [`milestones.md`](milestones.md).",
        "",
        "## Статистика репозитория",
        "",
        "| Параметр | Значение |",
        "|---|---|",
        f"| Файлов в репозитории | `{total_files}` |",
    ]
    for label, count in loc_rows:
        lines.append(f"| Строк кода: {label} | `{count}` |")
    lines.append(f"| Unit-тестов (обнаружено) | `{test_count}` |")
    if coverage is not None:
        percent, recorded_at = coverage
        lines.append(f"| Покрытие кода | `{percent}` (записано {recorded_at}) |")
    else:
        lines.append("| Покрытие кода | нет данных — запустите `run_suite.py full` |")
    test_time = timings.get("Unit tests with branch coverage")
    if test_time is not None:
        lines.append(f"| Время прогона тестов (с покрытием) | `{test_time:.1f}s` |")
    else:
        lines.append("| Время прогона тестов | нет данных — запустите `run_suite.py full` |")
    scan_time = timings.get("Documentation audit")
    if scan_time is not None:
        lines.append(
            f"| Время полной проверки документов (`check.py --all`) | `{scan_time:.1f}s` |"
        )
    else:
        lines.append("| Время проверки документов | нет данных — запустите `run_suite.py full` |")
    lines.extend(
        [
            "",
            "> Покрытие и время прогона — из последнего локального запуска "
            "`operations/scripts/quality/run_suite.py full` на этой машине "
            "(`runtime/*.json`, не хранится в git). Это не статус конкретного SHA в CI — "
            "см. раздел «GitHub Actions» ниже.",
            "",
            "## Статистика документов",
            "",
            "| Тип | Количество |",
            "|---|---|",
        ]
    )
    for family, label in DOCUMENT_FAMILIES:
        lines.append(f"| {label} | `{family_counts.get(family, 0)}` |")
    lines.append(f"| Проектные TASK | `{task_count}` |")
    lines.append(f"| Спецификации TEST | `{test_spec_count}` |")
    lines.append("")

    lines.append("## Что уже реализовано")
    lines.append("")
    completed = _completed_task_results(root)
    if not completed:
        lines.append(
            "Пока ни одна проектная TASK не завершена. Текущую работу и следующий шаг "
            "см. в [`project_status.md`](project_status.md)."
        )
    else:
        for task, result_text in completed:
            component = str(task.get("component", "")) or "—"
            task_id = str(task["id"])
            path = str(task["path"])
            tests = (
                ", ".join(f"[`{test['id']}`]({test['path']})" for test in task.get("tests", []))
                or "—"
            )
            lines.append(f"### `{component}` — {task['title']} (`{task_id}`)")
            lines.append("")
            lines.append(result_text or "_Раздел «Результат» пуст._")
            lines.append("")
            lines.append(f"[Карточка задачи]({path}) · Доказательство: {tests}")
            lines.append("")

    lines.extend(
        [
            "## GitHub Actions",
            "",
            "Статус серверной проверки не хранится в этом документе, потому что он быстро "
            "устаревает. Перед смысловой проверкой агент обязан получить результат GitHub "
            "Actions для точного проверяемого SHA и сверить evidence artifact. Пока это не "
            "выполнено, серверная готовность считается неподтверждённой.",
            "",
            "## Ссылки на правила",
            "",
            "- **Как работает процесс:** [`project_rules.md`](project_rules.md)",
            "- **Как вносятся изменения:** [`operations/change_process.md`](operations/change_process.md)",
            "- **Инструкция агенту:** [`AGENTS.md`](AGENTS.md)",
            "",
        ]
    )

    return "\n".join(lines)
