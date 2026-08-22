"""Semantic TASK-to-component-to-requirement traceability checks."""

from __future__ import annotations

from pathlib import Path

from operations.scripts.documents.traceability import collect_traceable_elements
from operations.scripts.tasks.generate import collect_tasks

COMPONENT_FAMILIES = {"ARC_CMP", "ARC_FLOW", "INF_CMP", "INF_FLOW"}
DELIVERY_RELATIONS = {"traces_to", "implements", "mitigates"}


def _targets(record: dict[str, object], relation: str) -> set[str]:
    relations = record.get("relations", {})
    if not isinstance(relations, dict):
        return set()
    values = relations.get(relation, [])
    return {str(value) for value in values} if isinstance(values, list) else set()


def delivery_closure(records: dict[str, dict[str, object]], identifiers: set[str]) -> set[str]:
    """Expand components/requirements through their declared delivery relations."""
    result = set(identifiers)
    queue = list(identifiers)
    while queue:
        current = queue.pop()
        record = records.get(current)
        if not record:
            continue
        for relation in DELIVERY_RELATIONS:
            for target in _targets(record, relation):
                if target not in result:
                    result.add(target)
                    queue.append(target)
    return result


def milestone_test_coverage_semantic(root: Path, milestone_id: str) -> tuple[set[str], set[str]]:
    """Return milestone scope and the scope semantically covered by accepting TESTs."""
    records = collect_traceable_elements(root)
    milestone = records.get(milestone_id.lower(), {})
    required = _targets(milestone, "scope")
    verified: set[str] = set()
    for record in records.values():
        if record.get("family") != "TEST":
            continue
        if milestone_id.lower() not in {value.lower() for value in _targets(record, "accepts")}:
            continue
        verified.update(_targets(record, "verifies"))
    return required, required & delivery_closure(records, verified)


def validate_task_semantics(root: Path, milestone_id: str) -> list[str]:
    """Reject TASK declarations that claim requirements outside their component closure."""
    records = collect_traceable_elements(root)
    milestone = records.get(milestone_id.lower(), {})
    milestone_scope = _targets(milestone, "scope")
    raw_tasks = collect_tasks(root)["tasks"]
    task_rows = raw_tasks if isinstance(raw_tasks, list) else []
    tasks = [
        task
        for task in task_rows
        if isinstance(task, dict)
        if milestone_id.lower() in {str(value).lower() for value in task.get("traces_to", [])}
    ]
    errors: list[str] = []
    delivered: set[str] = set()
    for task in tasks:
        task_id = str(task["id"])
        component = str(task.get("component", "")).strip().upper()
        record = records.get(component)
        if not component:
            errors.append(f"{task_id}: отсутствует обязательное поле component")
            continue
        if not record or str(record.get("family")) not in COMPONENT_FAMILIES:
            errors.append(f"{task_id}: component {component} не является известным компонентом")
            continue
        closure = delivery_closure(records, {component})
        implements = {str(value).upper() for value in task.get("implements", [])}
        if component not in implements:
            errors.append(
                f"{task_id}: implements обязан включать собственный component {component}"
            )
        unrelated = sorted(implements - closure)
        if unrelated:
            errors.append(
                f"{task_id}: implements вне семантики {component}: {', '.join(unrelated)}"
            )
        tests = task.get("tests", [])
        linked_tests = tests if isinstance(tests, list) else []
        if not linked_tests:
            errors.append(f"{task_id}: component {component} не связан ни с одним TEST")
        for test in linked_tests:
            if not isinstance(test, dict):
                continue
            test_record = records.get(str(test.get("id", "")), {})
            verified = _targets(test_record, "verifies")
            unrelated_verified = sorted(verified - closure)
            if unrelated_verified:
                errors.append(
                    f"{task_id}: TEST {test.get('id')} проверяет требования вне {component}: "
                    + ", ".join(unrelated_verified)
                )
            delivered.update(delivery_closure(records, verified))
        delivered.update(closure if linked_tests else set())
    missing = sorted(milestone_scope - delivered)
    if missing:
        errors.append(
            f"{milestone_id.lower()}: scope не покрыт TASK→component→TEST: {', '.join(missing)}"
        )
    return errors
