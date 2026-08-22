from __future__ import annotations

from pathlib import Path

from operations.scripts.common.project import iter_files, relative_posix

GENERATED_HEADER = "<!-- generated file: do not edit manually -->"
SELF_PATH = "generated/repository_structure.md"
PROJECT_ROOT_LABEL = "personal_ai_platform"


def render_repository_structure(root: Path, generated_date: str | None = None) -> str:
    files = [relative_posix(path, root) for path in iter_files(root)]
    files = sorted(set(files) | {SELF_PATH})
    file_count = len(files)
    lines = [
        GENERATED_HEADER,
        "---",
        "id: generated_repository_structure",
        "type: generated_document",
        "generation_state: generated",
        "version: 1.0",
        "---",
        "",
        "# Структура репозитория",
        "",
        "| Параметр | Значение |",
        "|---|---|",
        f"| Всего файлов | `{file_count}` |",
        "",
        "```text",
        f"{PROJECT_ROOT_LABEL}/",
    ]
    for item in files:
        lines.append(f"- {item}")
    lines.extend(["```", ""])
    return "\n".join(lines)
