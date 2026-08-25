from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import unquote

from operations.scripts.common.project import IGNORED_DIRS, atomic_write, iter_files, relative_posix
from operations.scripts.documents.metadata import load_document
from operations.scripts.documents.traceability import (
    ELEMENT_HEADING_PATTERN,
    MILESTONE_HEADING_PATTERN,
    REFERENCE_PATTERN,
    _normalize_id,
    collect_traceable_elements,
)

# TASK_*/TEST_*/ADR_* are conventionally linked to the whole file, without an
# anchor — none of them carry an <a id="..."> heading anchor of their own.
_WHOLE_FILE_FAMILIES = {"TASK", "TEST", "ADR"}

_BARE_ID_ERROR = re.compile(
    r"^(?P<file>[^:]+):(?P<line>\d+): упоминание (?P<id>\S+) "
    r"должно быть кликабельной ссылкой на (?P<target>\S+)$"
)
_CLICKABLE_REF_ERROR = re.compile(
    r"^(?P<file>[^:]+):(?P<line>\d+): "
    r"ссылка на существующий документ должна быть кликабельной: (?P<reference>.+)$"
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


def _resolve_document_reference(root: Path, source: Path, reference: str) -> Path | None:
    """Same resolution rules as _reference_exists, but returns the match so a
    fix can compute a correct relative href instead of just flagging it."""
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

    for candidate in candidates:
        if is_project_document(candidate):
            return candidate
    if "/" not in without_anchor:
        matches = [path for path in root.rglob(without_anchor) if is_project_document(path)]
        if len(matches) == 1:
            return matches[0]
    return None


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
    """Идентификатор документа целиком (frontmatter `id`, например TASK_003
    для карточки TASK) — самоссылка независимо от места в файле. Элемент,
    определённый заголовком где-то в этом же файле (BR_*, ARC_CMP_* и т.п.),
    сюда не входит: в файле вроде architecture_baseline.md таких элементов
    много, и упоминание одного из них в разделе другого — это ссылка на
    соседний элемент, а не самоссылка (см. `_current_section_id` в
    `_check_bare_identifier_references`, которая ограничивает исключение
    только текущим разделом)."""
    own_ids: set[str] = set()
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
    # Раздел (### BR_001 — ..., ## m02 — ...) определяет элемент, к которому
    # относится текущий текст, — упоминание ЭТОГО элемента внутри его же
    # раздела является самоссылкой и не требует ссылки. Упоминание любого
    # другого элемента (в том числе определённого заголовком в другом месте
    # того же файла) — обычная перекрёстная ссылка и ссылки требует.
    current_section_id: str | None = None
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
        heading_match = ELEMENT_HEADING_PATTERN.match(line) or MILESTONE_HEADING_PATTERN.match(line)
        if heading_match:
            current_section_id = _normalize_id(heading_match.group(1))
        # Заголовки и таблицы уже являются каноническим представлением
        # связи, а не прозой. Строки relation-полей (`- \`traces_to\`: ...`,
        # `- \`implements\`: ...` и т.п.) больше не исключение — упоминание
        # там элемента требует такой же кликабельной ссылки, как и в прозе.
        if HEADING_PATTERN.match(line) or stripped.startswith("|"):
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
            if (
                raw != identifier
                or identifier in own_ids
                or identifier == current_section_id
                or identifier in seen_on_line
            ):
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


def _is_literal_command_span(line: str, start: int, end: int) -> bool:
    """True if [start, end) sits inside a backtick span whose content is a
    multi-word literal (e.g. `ПРОДОЛЖАЙ TASK_002`) rather than a bare
    identifier — such spans are copy-paste commands, not prose mentions."""
    for match in INLINE_CODE_PATTERN.finditer(line):
        if match.start() <= start and end <= match.end():
            content = match.group(1).strip()
            return not REFERENCE_PATTERN.fullmatch(content)
    return False


def _href_for_record(record: dict[str, object], source: Path, root: Path) -> str:
    target_path = str(record["path"])
    family = str(record["family"])
    if (root / target_path).resolve() == source.resolve():
        return "" if family in _WHOLE_FILE_FAMILIES else f"#{record['anchor']}"
    rel = Path(os.path.relpath(root / target_path, source.parent)).as_posix()
    return rel if family in _WHOLE_FILE_FAMILIES else f"{rel}#{record['anchor']}"


def _fix_bare_identifier_references(
    root: Path,
    errors: list[str],
    records: dict[str, dict[str, object]],
    only_files: set[str] | None,
) -> set[str]:
    changed: set[str] = set()
    by_file: dict[str, list[re.Match[str]]] = {}
    for error in errors:
        match = _BARE_ID_ERROR.match(error)
        if match and (only_files is None or match.group("file") in only_files):
            by_file.setdefault(match.group("file"), []).append(match)

    for file, matches in by_file.items():
        path = root / file
        text = path.read_text(encoding="utf-8-sig")
        lines = text.split("\n")
        by_line: dict[int, list[re.Match[str]]] = {}
        for match in matches:
            by_line.setdefault(int(match.group("line")), []).append(match)
        for line_no_1based, line_matches in sorted(by_line.items()):
            idx = line_no_1based - 1
            if idx >= len(lines):
                continue
            line = lines[idx]
            for match in line_matches:
                identifier = match.group("id")
                record = records.get(
                    identifier.lower()
                    if re.fullmatch(r"m\d{2}", identifier, re.IGNORECASE)
                    else identifier.upper()
                )
                if record is None:
                    continue
                href = _href_for_record(record, path, root)
                pattern = re.compile(rf"`{re.escape(identifier)}`|\b{re.escape(identifier)}\b")
                found = pattern.search(line)
                if not found or _is_literal_command_span(line, found.start(), found.end()):
                    continue
                replacement = f"[`{identifier}`]({href})"
                line = line[: found.start()] + replacement + line[found.end() :]
            lines[idx] = line
        new_text = "\n".join(lines)
        if new_text != text and atomic_write(path, new_text):
            changed.add(file)
    return changed


def _fix_clickable_document_references(
    root: Path, errors: list[str], only_files: set[str] | None
) -> set[str]:
    changed: set[str] = set()
    by_file: dict[str, list[re.Match[str]]] = {}
    for error in errors:
        match = _CLICKABLE_REF_ERROR.match(error)
        if match and (only_files is None or match.group("file") in only_files):
            by_file.setdefault(match.group("file"), []).append(match)

    for file, matches in by_file.items():
        path = root / file
        text = path.read_text(encoding="utf-8-sig")
        lines = text.split("\n")
        by_line: dict[int, list[re.Match[str]]] = {}
        for match in matches:
            by_line.setdefault(int(match.group("line")), []).append(match)
        for line_no_1based, line_matches in sorted(by_line.items()):
            idx = line_no_1based - 1
            if idx >= len(lines):
                continue
            line = lines[idx]
            for match in line_matches:
                reference = match.group("reference")
                resolved = _resolve_document_reference(root, path, reference)
                if resolved is None:
                    continue
                anchor = reference.split("#", 1)[1] if "#" in reference else ""
                rel = Path(os.path.relpath(resolved, path.parent)).as_posix()
                href = f"{rel}#{anchor}" if anchor else rel
                target = f"`{reference}`"
                found = line.find(target)
                if found == -1:
                    continue
                replacement = f"[`{reference}`]({href})"
                line = line[:found] + replacement + line[found + len(target) :]
            lines[idx] = line
        new_text = "\n".join(lines)
        if new_text != text and atomic_write(path, new_text):
            changed.add(file)
    return changed


def fix_markdown_links(
    root: Path, *, only_files: set[str] | None = None, max_passes: int = 6
) -> list[str]:
    """Auto-fix what check_markdown_links can safely rewrite on its own:
    wrapping bare mentions of tracked IDs and existing-document references in
    clickable links. Several passes may be needed because a line reporting
    one bare mention can still contain a second, distinct one after the
    first is fixed (the checker dedupes per line, not per occurrence).

    `only_files` restricts which files get rewritten (e.g. to what's staged
    for commit) while target resolution still uses the whole-repo `records`,
    so an unrelated pre-existing violation elsewhere never rides along into
    someone else's commit."""
    changed: set[str] = set()
    for _ in range(max_passes):
        errors = check_markdown_links(root)
        records = collect_traceable_elements(root)
        progressed = _fix_bare_identifier_references(root, errors, records, only_files)
        progressed |= _fix_clickable_document_references(root, errors, only_files)
        if not progressed:
            break
        changed |= progressed
    return sorted(changed)


if __name__ == "__main__":
    import sys

    project_root = Path(__file__).resolve().parents[3]
    scope = set(sys.argv[1:]) or None
    fixed = fix_markdown_links(project_root, only_files=scope)
    if fixed:
        print(f"✓ Auto-linked {len(fixed)} file(s):")
        for name in fixed:
            print(f"  {name}")
    remaining = check_markdown_links(project_root)
    if scope is not None:
        remaining = [error for error in remaining if error.split(":", 1)[0] in scope]
    if remaining:
        print(f"⚠️  {len(remaining)} link issue(s) require manual attention:", file=sys.stderr)
        for error in remaining:
            print(f"  {error}", file=sys.stderr)
        sys.exit(1)
    sys.exit(0)
