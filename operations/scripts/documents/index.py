from __future__ import annotations

from operations.scripts.common.project import iter_files, relative_posix
from operations.scripts.documents.metadata import load_document, typed_state
from operations.scripts.documents.repository_tree import GENERATED_HEADER

ROOT_PRIMARY_DOCS = {
    "AGENTS.md",
    "milestones.md",
    "project_rules.md",
}


def is_primary_markdown(relative: str) -> bool:
    if relative in ROOT_PRIMARY_DOCS:
        return True
    if relative in {"project_status.md", "tasks.md"}:
        return False
    if not relative.endswith(".md"):
        return False
    return relative.startswith(
        (
            "adr/",
            "specifications/",
            "operations/",
            "work/tasks/",
            "work/tests/",
        )
    )


def render_index(root, generated_date: str | None = None) -> str:
    rows = []
    for path in iter_files(root, suffixes={".md"}, include_generated=False):
        relative = relative_posix(path, root)
        if not is_primary_markdown(relative):
            continue
        doc = load_document(path)
        state_field, state = typed_state(doc.metadata, relative)
        rows.append(
            {
                "path": relative,
                "id": str(doc.metadata.get("id", "")),
                "type": str(doc.metadata.get("type", "")),
                "state_field": state_field,
                "state": state,
                "version": str(doc.metadata.get("version", "")),
                "title": doc.title,
            }
        )

    total_docs = len(rows)
    lines = [
        GENERATED_HEADER,
        "---",
        "id: generated_document_index",
        "type: generated_document",
        "generation_state: generated",
        "version: 1.0",
        "---",
        "",
        "# Индекс документов",
        "",
        "| Параметр | Значение |",
        "|---|---|",
        f"| Всего документов | `{total_docs}` |",
        "",
        "> В список входят первичные Markdown-документы. Производные и периодические представления исключены.",
        "",
        "| Путь | ID | Тип | Поле состояния | Состояние | Версия | Название |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in sorted(rows, key=lambda row: row["path"]):
        path_link = f"[`{row['path']}`](../{row['path']})"
        lines.append(
            f"| {path_link} | `{row['id']}` | `{row['type']}` | `{row['state_field']}` | `{row['state']}` | `{row['version']}` | {row['title']} |"
        )
    return "\n".join(lines) + "\n"
