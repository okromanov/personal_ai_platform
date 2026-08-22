"""Deterministic semantic guards for relations that syntax alone cannot validate."""

from __future__ import annotations

import re
from pathlib import Path

from operations.scripts.documents.traceability import collect_traceable_elements
from operations.scripts.status.generate_project_status import v1_milestone_ids

REFERENCE_PATTERN = re.compile(
    r"\b(?:BR|SYS|THR|SEC_CTL|ARC_CMP|ARC_FLOW|INF_REQ|INF_CMP|INF_FLOW)_\d{3}\b"
)


def _relation_values(record: dict[str, object], key: str) -> set[str]:
    relations = record.get("relations", {})
    if not isinstance(relations, dict):
        return set()
    values = relations.get(key, [])
    return {str(value) for value in values} if isinstance(values, list) else set()


def _milestone_membership(root: Path, records: dict[str, dict[str, object]]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for milestone_id in v1_milestone_ids(root):
        record = records.get(milestone_id.lower(), {})
        for target in _relation_values(record, "scope"):
            result.setdefault(target, set()).add(milestone_id.lower())
    return result


def validate_semantic_consistency(root: Path) -> list[str]:
    """Validate implicit dependencies and ADR-to-milestone meaning alignment."""
    errors: list[str] = []
    records = collect_traceable_elements(root)

    for identifier, record in sorted(records.items()):
        if record.get("family") != "SYS":
            continue
        declared = _relation_values(record, "depends_on") | _relation_values(record, "traces_to")
        mentioned = set(REFERENCE_PATTERN.findall(str(record.get("section", ""))))
        implicit = sorted(
            value for value in mentioned - declared - {identifier} if value.startswith("SYS_")
        )
        if implicit:
            errors.append(
                f"{identifier}: текст зависит от {implicit}, но структурный depends_on отсутствует"
            )

    membership = _milestone_membership(root, records)
    for identifier, record in sorted(records.items()):
        if record.get("family") != "ADR":
            continue
        targets = _relation_values(record, "traces_to")
        declared_milestones = {value.lower() for value in targets if value.lower().startswith("m")}
        if "m01" in declared_milestones:
            continue
        scoped_targets = {target: membership[target] for target in targets if target in membership}
        if scoped_targets and not declared_milestones:
            errors.append(f"{identifier}: ADR связан с V1 требованиями, но не указывает milestone")
            continue
        for target, milestones in sorted(scoped_targets.items()):
            if declared_milestones.isdisjoint(milestones):
                errors.append(
                    f"{identifier}: {target} относится к {sorted(milestones)}, "
                    f"а ADR указывает {sorted(declared_milestones)}"
                )
        for milestone in sorted(declared_milestones):
            if milestone == "m01":
                continue
            if not any(milestone in values for values in scoped_targets.values()):
                errors.append(
                    f"{identifier}: milestone {milestone} не подтверждён ни одной связью с его составом"
                )

    return errors
