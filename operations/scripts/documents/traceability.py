from __future__ import annotations

import re
from pathlib import Path

from operations.scripts.common.project import iter_files, read_text, relative_posix
from operations.scripts.documents.metadata import (
    load_document,
    metadata_list,
    require_unique_identifier,
)
from operations.scripts.documents.repository_tree import GENERATED_HEADER

ELEMENT_HEADING_PATTERN = re.compile(
    r"^#{2,4}\s+((?:BR|SYS|THR|SEC_CTL|ARC_CMP|ARC_FLOW|INF_REQ|INF_CMP|INF_FLOW)_\d{3})\s+—\s+(.+?)\s*$",
    re.MULTILINE,
)
DOCUMENT_ELEMENT_ID = re.compile(r"^(ADR_\d{3}|TASK_\d{3}|TEST_\d{3})$")
MILESTONE_HEADING_PATTERN = re.compile(
    r"^##\s+(m\d{2})\s+—\s+(.+?)\s*$", re.MULTILINE | re.IGNORECASE
)
SCOPE_LINE_PATTERN = re.compile(r"(?m)^-\s+состав:\s*(.+?)\s*$", re.IGNORECASE)
RELATION_LINE_PATTERN = re.compile(
    r"^-\s+`?(traces_to|implements|mitigates|mitigated_by|implemented_by|depends_on|verifies|accepts)`?:\s*(.+?)\s*$",
    re.MULTILINE,
)
REFERENCE_PATTERN = re.compile(
    r"\b(?:BR|SYS|THR|SEC_CTL|ARC_CMP|ARC_FLOW|INF_REQ|INF_CMP|INF_FLOW)_\d{3}\b|\bADR_\d{3}\b|\bTASK_\d{3}\b|\bTEST_\d{3}\b|\bm\d{2}\b",
    re.IGNORECASE,
)
RANGE_PATTERN = re.compile(
    r"`?(?P<family>BR|SYS|THR|SEC_CTL|ARC_CMP|ARC_FLOW|INF_REQ|INF_CMP|INF_FLOW|ADR|TASK|TEST)_(?P<start>\d{3})`?"
    r"\s*[–—-]\s*"
    r"`?(?P=family)_(?P<end>\d{3})`?",
    re.IGNORECASE,
)
METADATA_RELATION_KEYS = (
    "traces_to",
    "implements",
    "mitigates",
    "implemented_by",
    "depends_on",
    "verifies",
    "accepts",
)
EVIDENCE_METADATA_KEYS = ("automated_evidence", "manual_evidence")
FAMILY_ORDER = {
    "BR": 10,
    "SYS": 20,
    "THR": 30,
    "SEC_CTL": 40,
    "ARC_CMP": 50,
    "ARC_FLOW": 60,
    "INF_REQ": 70,
    "INF_CMP": 80,
    "INF_FLOW": 90,
    "ADR": 100,
    "TASK": 110,
    "TEST": 120,
    "MILESTONE": 130,
}


def element_family(identifier: str) -> str:
    upper = identifier.upper()
    if upper.startswith("SEC_CTL_"):
        return "SEC_CTL"
    if upper.startswith("ARC_CMP_"):
        return "ARC_CMP"
    if upper.startswith("ARC_FLOW_"):
        return "ARC_FLOW"
    if upper.startswith("INF_REQ_"):
        return "INF_REQ"
    if upper.startswith("INF_CMP_"):
        return "INF_CMP"
    if upper.startswith("INF_FLOW_"):
        return "INF_FLOW"
    if re.fullmatch(r"m\d{2}", identifier, re.IGNORECASE):
        return "MILESTONE"
    return upper.split("_", 1)[0]


def _normalize_id(identifier: str) -> str:
    return (
        identifier.lower()
        if re.fullmatch(r"m\d{2}", identifier, re.IGNORECASE)
        else identifier.upper()
    )


def _relations_from_text(section: str) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for key, raw in RELATION_LINE_PATTERN.findall(section):
        refs = [_normalize_id(value) for value in REFERENCE_PATTERN.findall(raw)]
        if refs:
            result.setdefault(key, []).extend(refs)
    return {key: list(dict.fromkeys(values)) for key, values in result.items()}


def _relations_from_metadata(doc) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for key in METADATA_RELATION_KEYS:
        values = [
            _normalize_id(value.strip())
            for value in metadata_list(doc.metadata, key)
            if value.strip()
        ]
        if values:
            result[key] = list(dict.fromkeys(values))
    return result


def _evidence_from_metadata(doc) -> list[str]:
    return [
        value for key in EVIDENCE_METADATA_KEYS if (value := str(doc.metadata.get(key, "")).strip())
    ]


def parse_scope_references(section: str) -> list[str]:
    """Вернуть идентификаторы только из строки этапа `- состав:`, разворачивая диапазоны."""
    lines = SCOPE_LINE_PATTERN.findall(section)
    if not lines:
        return []
    raw = " ".join(lines)
    refs: list[str] = []
    for match in RANGE_PATTERN.finditer(raw):
        family = match.group("family").upper()
        start_raw = match.group("start")
        end_raw = match.group("end")
        start = int(start_raw)
        end = int(end_raw)
        if end < start:
            raise ValueError(
                f"Некорректный диапазон состава {family}_{start_raw}–{family}_{end_raw}"
            )
        width = max(len(start_raw), len(end_raw))
        refs.extend(f"{family}_{number:0{width}d}" for number in range(start, end + 1))
    without_ranges = RANGE_PATTERN.sub(" ", raw)
    refs.extend(
        _normalize_id(value)
        for value in REFERENCE_PATTERN.findall(without_ranges)
        if not value.lower().startswith("m")
    )
    return list(dict.fromkeys(refs))


def collect_traceable_elements(root: Path) -> dict[str, dict[str, object]]:
    records: dict[str, dict[str, object]] = {}
    record_paths: dict[str, str] = {}

    for path in iter_files(root, suffixes={".md"}, include_generated=False):
        relative = relative_posix(path, root)
        text = read_text(path)
        matches = list(ELEMENT_HEADING_PATTERN.finditer(text))
        for index, match in enumerate(matches):
            identifier = _normalize_id(match.group(1))
            require_unique_identifier(record_paths, identifier, relative, label="трассируемый ID")
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            section = text[match.end() : end]
            records[identifier] = {
                "id": identifier,
                "family": element_family(identifier),
                "title": match.group(2).strip(),
                "path": relative,
                "anchor": identifier.lower(),
                "relations": _relations_from_text(section),
                "section": section,
            }

        try:
            doc = load_document(path)
        except ValueError:
            continue
        doc_id = _normalize_id(str(doc.metadata.get("id", "")).strip())
        if DOCUMENT_ELEMENT_ID.fullmatch(doc_id):
            require_unique_identifier(record_paths, doc_id, relative, label="трассируемый ID")
            records[doc_id] = {
                "id": doc_id,
                "family": element_family(doc_id),
                "title": doc.title or doc_id,
                "path": relative,
                "anchor": doc_id.lower(),
                "relations": _relations_from_metadata(doc),
                "evidence": _evidence_from_metadata(doc),
                "section": doc.body,
            }

    milestones = root / "milestones.md"
    if milestones.is_file():
        text = read_text(milestones)
        matches = list(MILESTONE_HEADING_PATTERN.finditer(text))
        for index, match in enumerate(matches):
            identifier = match.group(1).lower()
            require_unique_identifier(
                record_paths, identifier, "milestones.md", label="milestone ID"
            )
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            section = text[match.end() : end]
            scope_refs = parse_scope_references(section)
            records[identifier] = {
                "id": identifier,
                "family": "MILESTONE",
                "title": match.group(2).strip(),
                "path": "milestones.md",
                "anchor": identifier,
                "relations": {"scope": scope_refs} if scope_refs else {},
                "section": section,
            }

    return records


def collect_requirement_records(root: Path) -> dict[str, dict[str, object]]:
    return {
        identifier: record
        for identifier, record in collect_traceable_elements(root).items()
        if record["family"] == "SYS"
    }


def collect_requirements(root: Path) -> dict[str, str]:
    return {
        identifier: str(record["title"])
        for identifier, record in collect_requirement_records(root).items()
    }


def _sort_key(record: dict[str, object]) -> tuple[int, int, str]:
    family = str(record["family"])
    identifier = str(record["id"])
    number_match = re.search(r"(\d+)$", identifier)
    number = int(number_match.group(1)) if number_match else 0
    return FAMILY_ORDER.get(family, 999), number, identifier


def _compact_relation_cell(relations: dict[str, list[str]]) -> str:
    chunks: list[str] = []
    for key in sorted(relations):
        targets = ", ".join(f"`{target}`" for target in relations[key])
        chunks.append(f"`{key}`: {targets}")
    return "<br>".join(chunks) if chunks else "—"


def render_traceability(root: Path, generated_date: str | None = None) -> str:
    """Render canonical outgoing edges; incoming edges are derivable and are not duplicated."""
    records = collect_traceable_elements(root)
    element_count = len(records)
    lines = [
        GENERATED_HEADER,
        "---",
        "id: generated_traceability_matrix",
        "type: generated_report",
        "generation_state: generated",
        "version: 1.0",
        "---",
        "",
        "# Матрица трассируемости",
        "",
        "| Параметр | Значение |",
        "|---|---|",
        f"| Отслеживаемых элементов | `{element_count}` |",
        "",
        "> Производное представление канонических исходящих связей. Входящие связи однозначно выводятся из тех же рёбер и здесь не дублируются.",
        "",
        "| Элемент | Тип | Исходящие связи | Доказательство |",
        "|---|---|---|---|",
    ]
    for record in sorted(records.values(), key=_sort_key):
        raw_relations = record.get("relations", {})
        relations = raw_relations if isinstance(raw_relations, dict) else {}
        raw_evidence = record.get("evidence", [])
        evidence = raw_evidence if isinstance(raw_evidence, list) else []
        lines.append(
            f"| `{record['id']}` | `{record['family']}` | "
            f"{_compact_relation_cell(relations)} | "
            f"{', '.join(f'`{value}`' for value in evidence) or '—'} |"
        )
    return "\n".join(lines) + "\n"
