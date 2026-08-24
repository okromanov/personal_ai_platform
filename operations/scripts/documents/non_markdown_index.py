from __future__ import annotations

import ast
from pathlib import Path

from operations.scripts.common.project import iter_files, relative_posix
from operations.scripts.common.status_types import TaskItem
from operations.scripts.documents.repository_tree import GENERATED_HEADER
from operations.scripts.tasks.generate import collect_tasks

NO_DESCRIPTION = (
    "_Описание не задано (для этого типа файла нет источника — "
    "docstring модуля или заголовочный комментарий скрипта)._"
)


def _deliverable_task_map(tasks: list[TaskItem]) -> dict[str, TaskItem]:
    """Non-.md file path -> the TASK whose `allowed_paths` shipped it, beyond
    the TASK's own card. Markdown deliverables are out of scope here (they
    already have their own honest source: the file's own docstring/comment
    header, not a shared TASK blurb) — a file with no owning TASK (most
    repository tooling predates the TASK system) is simply absent."""
    mapping: dict[str, TaskItem] = {}
    for task in tasks:
        own_path = str(task["path"])
        for path in task.get("allowed_paths", []):
            if path == own_path or path.endswith("/") or path.endswith(".md"):
                continue
            mapping.setdefault(path, task)
    return mapping


def _python_description(path: Path) -> str:
    """A module's own docstring, first paragraph only — never a translated
    or invented summary."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    except (SyntaxError, ValueError, UnicodeDecodeError):
        return ""
    doc = ast.get_docstring(tree)
    if not doc:
        return ""
    return " ".join(doc.strip().split("\n\n", 1)[0].split())


def _shell_description(path: Path) -> str:
    """The `#`-comment block immediately following the shebang line, if any
    — the same convention already used across this repo's own hooks."""
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeDecodeError):
        return ""
    start = 1 if lines and lines[0].startswith("#!") else 0
    comment_lines: list[str] = []
    for line in lines[start:]:
        stripped = line.strip()
        if not stripped.startswith("#"):
            break
        comment_lines.append(stripped.lstrip("#").strip())
    return " ".join(part for part in comment_lines if part)


def _file_description(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".py":
        return _python_description(path) or NO_DESCRIPTION
    if suffix == ".sh":
        return _shell_description(path) or NO_DESCRIPTION
    return NO_DESCRIPTION


def render_non_markdown_index(root: Path, generated_date: str | None = None) -> str:
    tasks = collect_tasks(root)["tasks"]
    task_by_path = _deliverable_task_map(tasks)

    rows: list[tuple[str, str]] = []
    for file_path in iter_files(root, include_generated=False):
        if file_path.suffix.lower() == ".md":
            continue
        relative = relative_posix(file_path, root)
        task = task_by_path.get(relative)
        task_cell = (
            f"[`{task['id']}`](../work/tasks/{Path(str(task['path'])).name})" if task else "—"
        )
        path_link = f"[`{relative}`](../{relative})"
        rows.append((relative, f"| {path_link} | {task_cell} | {_file_description(file_path)} |"))

    rows.sort(key=lambda item: item[0])
    total = len(rows)
    lines = [
        GENERATED_HEADER,
        "---",
        "id: generated_non_markdown_index",
        "type: generated_document",
        "generation_state: generated",
        "version: 1.0",
        "---",
        "",
        "# Индекс файлов вне Markdown",
        "",
        "| Параметр | Значение |",
        "|---|---|",
        f"| Всего файлов | `{total}` |",
        "",
        "> Каждая строка — один не-`.md` файл репозитория (код, конфигурация, данные), "
        "не документ: Markdown-документы перечислены в "
        "[`document_index.md`](document_index.md). «Задача» указана, только если файл "
        "входит в `allowed_paths` какой-то TASK за пределами её собственной карточки — "
        "у большинства файлов инфраструктуры репозитория такой TASK нет, это ожидаемо. "
        "«Описание» берётся из собственного источника файла (docstring модуля для `.py`, "
        "заголовочный комментарий для `.sh`) и никогда не выдумывается — для остальных "
        "типов файлов честно указано отсутствие источника.",
        "",
        "| Файл | Задача | Описание |",
        "|---|---|---|",
    ]
    lines.extend(row[1] for row in rows)
    return "\n".join(lines) + "\n"
