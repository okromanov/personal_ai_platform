from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from operations.scripts.common.project import read_text

STATE_FIELDS = ("document_state", "decision_state", "work_state", "spec_state")
STATE_VALUES = {
    "document_state": {"current", "superseded"},
    "decision_state": {"proposed", "accepted", "rejected", "superseded"},
    "work_state": {"planned", "in-progress", "blocked", "completed", "cancelled"},
    "spec_state": {"current", "superseded"},
}


@dataclass(frozen=True)
class MarkdownDocument:
    path: Path
    metadata: dict[str, Any]
    body: str
    title: str


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    lower = value.lower()
    if lower in {"true", "yes", "on"}:
        return True
    if lower in {"false", "no", "off"}:
        return False
    if lower in {"null", "none", "~"}:
        return None
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        return [] if not inner else [_parse_scalar(part) for part in inner.split(",")]
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def parse_front_matter(text: str) -> tuple[dict[str, Any], str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if not normalized.startswith("---\n"):
        return {}, normalized
    end = normalized.find("\n---\n", 4)
    if end == -1:
        return {}, normalized
    raw = normalized[4:end]
    body = normalized[end + 5 :]
    metadata: dict[str, Any] = {}
    current_list_key: str | None = None
    for line_number, raw_line in enumerate(raw.splitlines(), start=2):
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if raw_line.startswith("  - ") or raw_line.startswith("- "):
            if current_list_key is None:
                raise ValueError(f"Элемент списка без ключа, строка {line_number}")
            item = raw_line.split("- ", 1)[1]
            current = metadata.setdefault(current_list_key, [])
            if not isinstance(current, list):
                raise ValueError(f"Ключ {current_list_key} не является списком")
            current.append(_parse_scalar(item))
            continue
        if ":" not in raw_line:
            raise ValueError(f"Некорректная строка front matter {line_number}: {raw_line}")
        key, value = raw_line.split(":", 1)
        key = key.strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]+", key):
            raise ValueError(f"Некорректный ключ front matter: {key}")
        if value.strip() == "":
            metadata[key] = []
            current_list_key = key
        else:
            metadata[key] = _parse_scalar(value)
            current_list_key = None
    return metadata, body


def extract_title(body: str, fallback: str) -> str:
    for line in body.splitlines():
        match = re.match(r"^#\s+(.+?)\s*$", line)
        if match:
            return match.group(1).strip()
    return fallback


def load_document(path: Path) -> MarkdownDocument:
    metadata, body = parse_front_matter(read_text(path))
    return MarkdownDocument(
        path=path, metadata=metadata, body=body, title=extract_title(body, path.stem)
    )


def metadata_list(metadata: dict[str, Any], key: str) -> list[str]:
    value = metadata.get(key, [])
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def require_unique_identifier(
    seen: dict[str, str],
    identifier: str,
    path: str,
    *,
    label: str = "ID",
) -> None:
    """Зарегистрировать ID или остановить обработку с единым сообщением об ошибке."""
    previous = seen.get(identifier)
    if previous is not None:
        raise ValueError(f"Дублирующий {label} {identifier}: {previous} и {path}")
    seen[identifier] = path


def expected_state_field(relative: str) -> str:
    if relative.startswith("adr/"):
        return "decision_state"
    if relative.startswith("work/tasks/"):
        return "work_state"
    if relative.startswith("work/tests/"):
        return "spec_state"
    return "document_state"


def typed_state(metadata: dict[str, Any], relative: str) -> tuple[str, str]:
    field = expected_state_field(relative)
    return field, str(metadata.get(field, "")).strip().lower()
