from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

from operations.scripts.common.project import IGNORED_DIRS, iter_files, relative_posix
from operations.scripts.documents.metadata import load_document
from operations.scripts.documents.traceability import (
    ELEMENT_HEADING_PATTERN,
    REFERENCE_PATTERN,
    RELATION_LINE_PATTERN,
    _normalize_id,
    collect_traceable_elements,
)

LINK_PATTERN = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
FULL_LINK_PATTERN = re.compile(r"!?\[[^\]]*\]\([^)]*\)")
INLINE_CODE_PATTERN = re.compile(r"`([^`\n]+)`")
# Клика­бельность обязательна только для ссылок на документы этих типов —
# .py и прочий код упоминаются по имени без требования их линковать.
CLICKABLE_EXTENSIONS = ("md", "txt", "yaml", "json")
MARKDOWN_PATH_PATTERN = re.compile(
    rf"^[A-Za-z0-9_./\\-]+\.(?:{'|'.join(CLICKABLE_EXTENSIONS)})(?:#[^\s]+)?$"
)
HEADING_PATTERN = re.compile(r"(?m)^#{1,6}\s+(.+?)\s*$")
EXPLICIT_ANCHOR_PATTERN = re.compile(r"""<a\s+(?:id|name)=["']([^"']+)["']""")
MARKDOWN_LINK_TEXT_PATTERN = re.compile(r"\[([^\]]*)\]\([^)]*\)")
FRONTMATTER_PATTERN = re.compile(r"^---\n.*?\n---\n", re.DOTALL)


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


def _mask_literal_code_spans(line: str) -> str:
    """Replace inline-code spans whose content is more than a single bare
    identifier (e.g. `ПРОДОЛЖАЙ TASK_002`, `traces_to: m01`) with blanks of
    the same length — these are literal commands/snippets to copy verbatim,
    not prose mentions that should become links."""

    def repl(match: re.Match[str]) -> str:
        content = match.group(1).strip()
        if REFERENCE_PATTERN.fullmatch(content):
            return match.group(0)
        return " " * len(match.group(0))

    return INLINE_CODE_PATTERN.sub(repl, line)


def _own_identifiers(path: Path, text: str) -> set[str]:
    own_ids = {_normalize_id(match.group(1)) for match in ELEMENT_HEADING_PATTERN.finditer(text)}
    try:
        doc = load_document(path)
    except ValueError:
        return own_ids
    doc_id = str(doc.metadata.get("id", "")).strip()
    if doc_id:
        own_ids.add(_normalize_id(doc_id))
    return own_ids


def _check_bare_identifier_references(
    root: Path, path: Path, text: str, records: dict[str, dict[str, object]]
) -> list[str]:
    """Упоминание элемента трассировки (BR_*, SYS_*, TASK_* и т.п. — включая
    вехи m01..m99) в прозе документа должно быть кликабельной ссылкой на его
    канонический источник, а не голым текстом или изолированным `код`."""
    errors: list[str] = []
    if text.lstrip("﻿").startswith("<!-- generated file"):
        return errors

    own_ids = _own_identifiers(path, text)
    frontmatter_match = FRONTMATTER_PATTERN.match(text)
    frontmatter_lines = frontmatter_match.group(0).count("\n") if frontmatter_match else 0
    in_fence = False
    fence_marker = ""
    for line_number, line in enumerate(text.splitlines(), start=1):
        if line_number <= frontmatter_lines:
            continue
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
        # Заголовки, таблицы и структурные строки связей (`- \`traces_to\`: ...`)
        # уже являются каноническим представлением связи, а не прозой.
        if HEADING_PATTERN.match(line) or stripped.startswith("|"):
            continue
        if RELATION_LINE_PATTERN.match(line):
            continue
        # Строки-якоря (`<a id="...">`) определяют идентификатор, а не
        # упоминают его — сам якорь не должен становиться ссылкой на себя.
        if EXPLICIT_ANCHOR_PATTERN.search(line):
            continue
        scrubbed = FULL_LINK_PATTERN.sub("", line)
        scrubbed = _mask_literal_code_spans(scrubbed)
        seen_on_line: set[str] = set()
        for match in REFERENCE_PATTERN.finditer(scrubbed):
            raw = match.group(0)
            identifier = _normalize_id(raw)
            # Пример неверного формата вроде `adr_001` (не каноническое
            # написание) или заглавное "M01" в подписи — не считается
            # упоминанием элемента, только точное написание требует ссылки.
            if raw != identifier or identifier in own_ids or identifier in seen_on_line:
                continue
            record = records.get(identifier)
            if record is None:
                continue
            seen_on_line.add(identifier)
            errors.append(
                f"{relative_posix(path, root)}:{line_number}: "
                f"упоминание {identifier} должно быть кликабельной ссылкой на "
                f"{record['path']}#{record['anchor']}"
            )
    return errors


def check_markdown_links(root: Path) -> list[str]:
    errors: list[str] = []
    anchor_cache: dict[Path, set[str]] = {}
    records = collect_traceable_elements(root)

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
        errors.extend(_check_bare_identifier_references(root, path, text, records))
    return errors
