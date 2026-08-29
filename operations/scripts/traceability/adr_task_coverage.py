"""Guards for assigning proposed ADR decisions to delivery TASK cards."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TypedDict

from operations.scripts.documents.metadata import load_document, metadata_list

ADR_ID_PATTERN = re.compile(r"^ADR_\d{3}$")
MILESTONE_HEADING_PATTERN = re.compile(
    r"^##\s+(m\d{2})\s+—\s+.+?$", re.MULTILINE | re.IGNORECASE
)
MILESTONE_STATE_PATTERN = re.compile(
    r"(?m)^-\s+work_state:\s+`?([a-z-]+)`?\s*$", re.IGNORECASE
)
ACTIVE_OR_FINISHED_MILESTONE_STATES = {"in-progress", "blocked", "completed"}
UNFINISHED_TASK_STATES = {"planned", "in-progress", "blocked"}
TERMINAL_TASK_STATES = {"completed", "cancelled"}


class AdrRecord(TypedDict):
    state: str
    milestones: set[str]
    path: str


class TaskRecord(TypedDict):
    id: str
    state: str
    milestones: set[str]
    decides: set[str]
    path: str


def _milestone_states(root: Path) -> dict[str, str]:
    path = root / "milestones.md"
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8-sig")
    matches = list(MILESTONE_HEADING_PATTERN.finditer(text))
    result: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        section = text[match.end() : end]
        state = MILESTONE_STATE_PATTERN.search(section)
        if state:
            result[match.group(1).lower()] = state.group(1).lower()
    return result


def validate_adr_decision_tasks(root: Path) -> list[str]:
    """Validate the canonical relation TASK.decides -> proposed ADR.

    A proposed ADR becomes mandatory to assign when at least one milestone in
    its traces_to is active, blocked, or already completed. ADRs that belong
    only to planned future milestones are checked when that milestone is
    decomposed and started; this preserves the project's delivery horizon.
    """

    milestone_states = _milestone_states(root)
    adrs: dict[str, AdrRecord] = {}
    for path in sorted((root / "adr").glob("adr_*.md")):
        doc = load_document(path)
        adr_id = str(doc.metadata.get("id", "")).strip().upper()
        if not ADR_ID_PATTERN.fullmatch(adr_id):
            continue
        adrs[adr_id] = {
            "state": str(doc.metadata.get("decision_state", "")).strip().lower(),
            "milestones": {
                value.lower()
                for value in metadata_list(doc.metadata, "traces_to")
                if re.fullmatch(r"m\d{2}", value, re.IGNORECASE)
            },
            "path": path.relative_to(root).as_posix(),
        }

    tasks: list[TaskRecord] = []
    for path in sorted((root / "work" / "tasks").glob("task_*.md")):
        doc = load_document(path)
        tasks.append(
            {
                "id": str(doc.metadata.get("id", "")).strip().upper(),
                "state": str(doc.metadata.get("work_state", "")).strip().lower(),
                "milestones": {
                    value.lower()
                    for value in metadata_list(doc.metadata, "traces_to")
                    if re.fullmatch(r"m\d{2}", value, re.IGNORECASE)
                },
                "decides": {
                    value.upper() for value in metadata_list(doc.metadata, "decides")
                },
                "path": path.relative_to(root).as_posix(),
            }
        )

    errors: list[str] = []
    for task in tasks:
        for adr_id in sorted(task["decides"]):
            if adr_id not in adrs:
                errors.append(f"{task['id']}: decides ссылается на неизвестный {adr_id}")

    for adr_id, adr in sorted(adrs.items()):
        if adr["state"] != "proposed":
            continue
        relevant = {
            milestone
            for milestone in adr["milestones"]
            if milestone_states.get(milestone) in ACTIVE_OR_FINISHED_MILESTONE_STATES
        }
        if not relevant:
            continue

        owners = [task for task in tasks if adr_id in task["decides"]]
        unfinished = [task for task in owners if task["state"] in UNFINISHED_TASK_STATES]
        if len(owners) != 1 or len(unfinished) != 1:
            owner_ids = ", ".join(task["id"] for task in owners) or "нет"
            errors.append(
                f"{adr_id}: proposed ADR для {', '.join(sorted(relevant))} должен иметь "
                f"ровно одну незавершённую TASK с decides; найдено: {owner_ids}"
            )
            continue

        owner = unfinished[0]
        if not (owner["milestones"] & relevant):
            errors.append(
                f"{adr_id}: {owner['id']} должна traces_to один из этапов "
                f"{', '.join(sorted(relevant))}"
            )

    for task in tasks:
        if task["state"] not in TERMINAL_TASK_STATES:
            continue
        for adr_id in sorted(task["decides"]):
            adr = adrs.get(adr_id)
            if adr and adr["state"] == "proposed":
                errors.append(
                    f"{task['id']}: завершённая/отменённая TASK не может оставлять "
                    f"{adr_id} в decision_state proposed"
                )

    return errors
