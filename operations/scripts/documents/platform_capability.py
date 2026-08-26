from __future__ import annotations

import re
from pathlib import Path

from operations.scripts.documents.repository_tree import GENERATED_HEADER
from operations.scripts.tasks.generate import collect_tasks

CAPABILITY_SOURCE = Path("capability_summary.md")
SECTION_TITLE = "# Карта компетенций"
ENTRY_PATTERN = re.compile(
    r"(?ms)^### (?P<kind>Пользовательская|Системная) — (?P<title>.+?)$"
    r"(?P<body>.*?)(?=^### |^## |\Z)"
)
TASK_PATTERN = re.compile(r"\bTASK_\d{3}\b")


def _section(text: str) -> str:
    start = text.find(SECTION_TITLE)
    if start < 0:
        raise ValueError(f"{CAPABILITY_SOURCE}: отсутствует раздел '{SECTION_TITLE}'")
    return text[start + len(SECTION_TITLE) :].split("\n## ", 1)[0]


def _field(body: str, label: str) -> str:
    match = re.search(rf"(?m)^- \*\*{re.escape(label)}:\*\*\s*(.+)$", body)
    if match is None:
        raise ValueError(f"Запись компетенции: отсутствует поле '{label}'")
    return match.group(1).strip()


def _entries(source: str) -> list[tuple[str, str, list[str], str]]:
    entries: list[tuple[str, str, list[str], str]] = []
    for match in ENTRY_PATTERN.finditer(_section(source)):
        task_ids = TASK_PATTERN.findall(_field(match.group("body"), "TASK"))
        if not task_ids:
            raise ValueError(f"{match.group('title')}: не указана формирующая TASK")
        entries.append(
            (
                match.group("kind"),
                match.group("title"),
                task_ids,
                _field(match.group("body"), "Описание"),
            )
        )
    if not entries:
        raise ValueError(f"{CAPABILITY_SOURCE}: не найдена ни одна компетенция")
    return entries


def render_platfrom_capability(root: Path, generated_date: str | None = None) -> str:
    source = (root / CAPABILITY_SOURCE).read_text(encoding="utf-8-sig")
    task_paths = {
        str(item["id"]): Path(str(item["path"])).name for item in collect_tasks(root)["tasks"]
    }
    lines = [
        GENERATED_HEADER,
        "---",
        "id: generated_platfrom_capability",
        "type: generated_document",
        "generation_state: generated",
        "version: 1.0",
        "---",
        "",
        "# Компетенции платформы",
        "",
        "> Автоматически собранная карта завершённых возможностей. Источник данных — "
        "[capability_summary.md](../capability_summary.md).",
    ]
    for kind, title, task_ids, description in _entries(source):
        missing = [task_id for task_id in task_ids if task_id not in task_paths]
        if missing:
            raise ValueError(f"{title}: неизвестные TASK {', '.join(missing)}")
        task_links = ", ".join(
            f"[{task_id}](../work/tasks/{task_paths[task_id]})" for task_id in task_ids
        )
        lines.extend(
            [
                "",
                f"## {title}",
                "",
                f"**Тип:** {kind.lower()}.",
                "",
                f"**Сформирована задачами:** {task_links}.",
                "",
                f"**Новая функциональность:** {description}",
            ]
        )
    return "\n".join(lines) + "\n"
