from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from operations.scripts.common.project import run_command

ARCHITECTURE_SVG = "work/artefacts/architecture/personal_ai_platform_architecture.svg"
SOURCE_PREFIXES = {
    "specifications/architecture_baseline.md": ("ARC_CMP_", "ARC_FLOW_"),
    "specifications/infrastructure_baseline.md": ("INF_CMP_", "INF_FLOW_"),
}
SYSTEM_SOURCE = "specifications/system_specification.md"
TASK_PATH = re.compile(r"^work/tasks/task_\d+_[a-z0-9_]+\.md$")
ANCHOR = re.compile(r'(?m)^<a id="(?P<id>[a-z0-9_]+)"></a>\s*$')
METADATA = re.compile(r"<!--\s*diagram-metadata\s*.*?\s*end-diagram-metadata\s*-->", re.DOTALL)
VISIBLE_VERSION = re.compile(
    r'(<text\b[^>]*data-diagram-meta="version"[^>]*>).*?(</text>)', re.DOTALL
)


@dataclass(frozen=True)
class ArchitectureVisualizationReview:
    completed_tasks: tuple[str, ...]
    affected_ids: tuple[str, ...]
    errors: tuple[str, ...]

    @property
    def redraw_required(self) -> bool:
        return bool(self.affected_ids)

    def summary(self) -> str:
        tasks = ", ".join(self.completed_tasks) or "нет"
        affected = ", ".join(self.affected_ids) or "нет"
        decision = "требуется перерисовка" if self.redraw_required else "перерисовка не требуется"
        return (
            "Проверка архитектурной визуализации после TASK: "
            f"завершены [{tasks}]; затронуты [{affected}]; {decision}."
        )


def _blob_at(root: Path, revision: str, path: str) -> str | None:
    result = run_command(["git", "show", f"{revision}:{path}"], cwd=root, timeout=30)
    return result.stdout if result.ok else None


def _frontmatter_field(text: str, field: str) -> str:
    frontmatter = text.split("\n---", 1)[0]
    match = re.search(rf"(?m)^{re.escape(field)}:\s*([^\n]+)\s*$", frontmatter)
    return match.group(1).strip().strip("`\"'") if match else ""


def _completed_task_transitions(
    root: Path, base: str, head: str, changed_paths: list[str]
) -> tuple[str, ...]:
    completed: list[str] = []
    for path in sorted(set(changed_paths)):
        normalized = path.replace("\\", "/")
        if not TASK_PATH.fullmatch(normalized):
            continue
        before = _blob_at(root, base, normalized) or ""
        after = _blob_at(root, head, normalized) or ""
        if _frontmatter_field(after, "work_state").lower() != "completed":
            continue
        if _frontmatter_field(before, "work_state").lower() == "completed":
            continue
        completed.append((_frontmatter_field(after, "id") or normalized).upper())
    return tuple(completed)


def _sections(text: str) -> dict[str, str]:
    normalized = text.replace("\r\n", "\n")
    matches = list(ANCHOR.finditer(normalized))
    level_two_headings = list(re.finditer(r"(?m)^##\s+", normalized))
    result: dict[str, str] = {}
    for index, match in enumerate(matches):
        boundaries = [
            heading.start() for heading in level_two_headings if heading.start() > match.end()
        ]
        if index + 1 < len(matches):
            boundaries.append(matches[index + 1].start())
        end = min(boundaries, default=len(normalized))
        result[match.group("id").upper()] = normalized[match.end() : end].strip()
    return result


def _declared_svg_ids(text: str) -> set[str]:
    metadata = METADATA.search(text)
    if metadata is None:
        return set()
    return {
        match.group(1).upper()
        for match in re.finditer(r"(?m)^\s*id:\s*([A-Za-z0-9_]+)\s*$", metadata.group(0))
    }


def _changed_visual_ids(
    root: Path, base: str, head: str, declared_ids: set[str]
) -> tuple[str, ...]:
    affected: set[str] = set()
    for path, prefixes in SOURCE_PREFIXES.items():
        before = _sections(_blob_at(root, base, path) or "")
        after = _sections(_blob_at(root, head, path) or "")
        identifiers = {
            identifier
            for identifier in before.keys() | after.keys()
            if identifier.startswith(prefixes)
        }
        affected.update(
            identifier
            for identifier in identifiers
            if before.get(identifier) != after.get(identifier)
        )

    before_system = _sections(_blob_at(root, base, SYSTEM_SOURCE) or "")
    after_system = _sections(_blob_at(root, head, SYSTEM_SOURCE) or "")
    affected.update(
        identifier
        for identifier in declared_ids
        if identifier.startswith("SEC_CTL_")
        and before_system.get(identifier) != after_system.get(identifier)
    )
    return tuple(sorted(affected))


def _diagram_version(text: str) -> tuple[int, int] | None:
    match = re.search(r"(?m)^\s*diagram_version:\s*(\d+)\.(\d+)\s*$", text)
    return (int(match.group(1)), int(match.group(2))) if match else None


def _semantic_svg(text: str) -> str:
    without_metadata = METADATA.sub("<!-- diagram-metadata -->", text)
    return VISIBLE_VERSION.sub(r"\1<version>\2", without_metadata)


def review_task_architecture_visualization(
    root: Path, base: str, head: str, changed_paths: list[str]
) -> ArchitectureVisualizationReview:
    completed = _completed_task_transitions(root, base, head, changed_paths)
    if not completed:
        return ArchitectureVisualizationReview((), (), ())

    before_svg = _blob_at(root, base, ARCHITECTURE_SVG) or ""
    after_svg = _blob_at(root, head, ARCHITECTURE_SVG) or ""
    declared_ids = _declared_svg_ids(before_svg) | _declared_svg_ids(after_svg)
    affected = _changed_visual_ids(root, base, head, declared_ids)
    errors: list[str] = []

    if affected:
        normalized_paths = {path.replace("\\", "/") for path in changed_paths}
        if ARCHITECTURE_SVG not in normalized_paths or before_svg == after_svg:
            errors.append(
                f"завершение {', '.join(completed)} изменило "
                "показанные "
                "элементы "
                f"{', '.join(affected)}, но {ARCHITECTURE_SVG} не обновлён"
            )
        else:
            before_version = _diagram_version(before_svg)
            after_version = _diagram_version(after_svg)
            if before_version is None or after_version is None or after_version <= before_version:
                errors.append(
                    f"{ARCHITECTURE_SVG}: при перерисовке diagram_version обязан увеличиться"
                )
            if _semantic_svg(before_svg) == _semantic_svg(after_svg):
                errors.append(
                    f"{ARCHITECTURE_SVG}: изменены только метаданные; "
                    f"затронутые {', '.join(affected)} требуют "
                    "содержательной "
                    "перерисовки"
                )

    return ArchitectureVisualizationReview(completed, affected, tuple(errors))
