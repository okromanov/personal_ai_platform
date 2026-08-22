from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

from operations.scripts.common.project import IGNORED_DIRS, iter_files, relative_posix

LINK_PATTERN = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
INLINE_CODE_PATTERN = re.compile(r"`([^`\n]+)`")
MARKDOWN_PATH_PATTERN = re.compile(r"^[A-Za-z0-9_./\\-]+\.md(?:#[^\s]+)?$")
HEADING_PATTERN = re.compile(r"(?m)^#{1,6}\s+(.+?)\s*$")
EXPLICIT_ANCHOR_PATTERN = re.compile(r"""<a\s+(?:id|name)=["']([^"']+)["']""")
MARKDOWN_LINK_TEXT_PATTERN = re.compile(r"\[([^\]]*)\]\([^)]*\)")


def heading_anchor(heading: str) -> str:
    """Слаг заголовка по правилам GitHub: регистр, пунктуация, пробелы."""
    text = MARKDOWN_LINK_TEXT_PATTERN.sub(r"\1", heading).replace("`", "")
    text = re.sub(r"[^\w\s-]", "", text.lower(), flags=re.UNICODE)
    return text.strip().replace(" ", "-")


def collect_anchors(text: str) -> set[str]:
    anchors = {heading_anchor(match.group(1)) for match in HEADING_PATTERN.finditer(text)}
    anchors.update(match.group(1).lower() for match in EXPLICIT_ANCHOR_PATTERN.finditer(text))
    return {anchor for anchor in anchors if anchor}


def _reference_exists(root: Path, source: Path, reference: str) -> bool:
    without_anchor = unquote(reference.split("#", 1)[0]).replace("\\", "/")
    candidates = [source.parent / without_anchor, root / without_anchor]

    def is_project_document(candidate: Path) -> bool:
        if not candidate.is_file():
            return False
        try:
            parts = candidate.resolve().relative_to(root.resolve()).parts
        except ValueError:
            return False
        return not any(part.lower() in IGNORED_DIRS for part in parts)

    if any(is_project_document(candidate) for candidate in candidates):
        return True
    if "/" not in without_anchor:
        matches = [path for path in root.rglob(without_anchor) if is_project_document(path)]
        return len(matches) == 1
    return False


def _check_clickable_document_references(root: Path, path: Path, text: str) -> list[str]:
    errors: list[str] = []
    in_fence = False
    fence_marker = ""
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.lstrip()
        marker = stripped[:3]
        if marker in {"```", "~~~"}:
            if not in_fence:
                in_fence = True
                fence_marker = marker
            elif marker == fence_marker:
                in_fence = False
                fence_marker = ""
            continue
        if in_fence:
            continue
        for match in INLINE_CODE_PATTERN.finditer(line):
            reference = match.group(1).strip()
            if not MARKDOWN_PATH_PATTERN.fullmatch(reference):
                continue
            before = line[: match.start()]
            after = line[match.end() :]
            if before.endswith("[") and after.startswith("]("):
                continue
            if _reference_exists(root, path, reference):
                errors.append(
                    f"{relative_posix(path, root)}:{line_number}: "
                    f"ссылка на существующий документ должна быть кликабельной: {reference}"
                )
    return errors


def check_markdown_links(root: Path) -> list[str]:
    errors: list[str] = []
    anchor_cache: dict[Path, set[str]] = {}

    def anchors_of(document: Path) -> set[str]:
        if document not in anchor_cache:
            anchor_cache[document] = collect_anchors(document.read_text(encoding="utf-8-sig"))
        return anchor_cache[document]

    for path in iter_files(root, suffixes={".md"}, include_generated=True):
        text = path.read_text(encoding="utf-8-sig")
        for raw_target in LINK_PATTERN.findall(text):
            target = raw_target.strip().split(maxsplit=1)[0].strip("<>")
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            target_without_anchor = unquote(target.split("#", 1)[0])
            anchor = unquote(target.split("#", 1)[1]).lower() if "#" in target else ""
            if not target_without_anchor:
                if anchor and anchor not in anchors_of(path):
                    errors.append(
                        f"{relative_posix(path, root)}: ссылка ведёт на несуществующий якорь этого документа: {target}"
                    )
                continue
            resolved = (path.parent / target_without_anchor).resolve()
            try:
                resolved.relative_to(root.resolve())
            except ValueError:
                errors.append(
                    f"{relative_posix(path, root)}: ссылка выходит за пределы проекта: {target}"
                )
                continue
            if resolved == path.resolve():
                errors.append(
                    f"{relative_posix(path, root)}: документ не должен ссылаться сам на себя: {target}"
                )
                continue
            if not resolved.exists():
                errors.append(f"{relative_posix(path, root)}: не найден путь ссылки: {target}")
                continue
            if anchor and resolved.suffix.lower() == ".md" and anchor not in anchors_of(resolved):
                errors.append(
                    f"{relative_posix(path, root)}: ссылка ведёт на несуществующий якорь "
                    f"{relative_posix(resolved, root)}#{anchor}"
                )
        errors.extend(_check_clickable_document_references(root, path, text))
    return errors
