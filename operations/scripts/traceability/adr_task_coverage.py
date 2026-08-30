"""Guards for assigning proposed ADR decisions to delivery TASK cards."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TypedDict

from operations.scripts.documents.metadata import load_document, metadata_list

ADR_ID_PATTERN = re.compile(r"^ADR_\d{3}$")
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


def validate_adr_decision_tasks(root: Path) -> list[str]:
    """Validate the canonical relation TASK.decides -> proposed ADR.

    Every proposed ADR assigned to a milestone has exactly one unfinished
    decision TASK immediately, including ADRs of planned future milestones.
    """

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
                "decides": {value.upper() for value in metadata_list(doc.metadata, "decides")},
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
        relevant = adr["milestones"]
        if not relevant:
            continue

        owners = [task for task in tasks if adr_id in task["decides"]]
        unfinished = [task for task in owners if task["state"] in UNFINISHED_TASK_STATES]
        if len(owners) != 1 or len(unfinished) != 1:
            owner_ids = ", ".join(task["id"] for task in owners) or "нет"
            errors.append(
                f"{adr_id}: proposed ADR для {', '.join(sorted(relevant))} "
                "должен иметь ровно одну незавершённую TASK с decides; "
                f"найдено: {owner_ids}"
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
            terminal_adr = adrs.get(adr_id)
            if terminal_adr and terminal_adr["state"] == "proposed":
                errors.append(
                    f"{task['id']}: завершённая/отменённая TASK не может "
                    f"оставлять {adr_id} в decision_state proposed"
                )

    return errors
