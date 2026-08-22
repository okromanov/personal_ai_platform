"""End-to-end traceability invariants that complement structural edge checks."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from operations.scripts.documents.traceability import collect_traceable_elements
from operations.scripts.quality.registry import load_quality_registry
from operations.scripts.status.generate_project_status import v1_milestone_ids

ARCHITECTURE_FAMILIES = {"ARC_CMP", "ARC_FLOW"}
INFRASTRUCTURE_FAMILIES = {"INF_CMP", "INF_FLOW"}
TESTABLE_FAMILIES = {"SYS", "SEC_CTL", "INF_REQ"}


def _targets(record: dict[str, object], relation: str) -> set[str]:
    relations = record.get("relations", {})
    if not isinstance(relations, dict):
        return set()
    values = relations.get(relation, [])
    return {str(value) for value in values} if isinstance(values, list) else set()


def _incoming(
    records: dict[str, dict[str, object]],
    target: str,
    *,
    families: set[str],
    relations: Iterable[str],
) -> set[str]:
    return {
        identifier
        for identifier, record in records.items()
        if str(record.get("family")) in families
        and any(target in _targets(record, relation) for relation in relations)
    }


def _v1_scope(root: Path, records: dict[str, dict[str, object]]) -> set[str]:
    scope: set[str] = set()
    for milestone in v1_milestone_ids(root):
        record = records.get(milestone.lower())
        if record:
            scope.update(_targets(record, "scope"))
    return scope


def _core_business_requirements(records: dict[str, dict[str, object]]) -> set[str]:
    result: set[str] = set()
    for identifier, record in records.items():
        if record.get("family") != "BR":
            continue
        section = str(record.get("section", ""))
        if "- `priority`: `core`" in section:
            result.add(identifier)
    return result


def validate_full_traceability(root: Path) -> list[str]:
    """Validate complete V1 decomposition and the TEST-to-evidence tail."""
    errors: list[str] = []
    records = collect_traceable_elements(root)
    v1_scope = _v1_scope(root, records)

    core = _core_business_requirements(records)
    for requirement in sorted(core):
        if requirement not in v1_scope:
            errors.append(f"{requirement}: core BR отсутствует в составе V1")
            continue
        if not _incoming(records, requirement, families={"SYS"}, relations=("traces_to",)):
            errors.append(f"{requirement}: core BR не декомпозирован ни одним SYS")

    for requirement in sorted(value for value in v1_scope if value.startswith("SYS_")):
        if not _incoming(
            records,
            requirement,
            families=ARCHITECTURE_FAMILIES,
            relations=("traces_to",),
        ):
            errors.append(
                f"{requirement}: требование V1 не имеет прямого покрытия ARC_CMP/ARC_FLOW"
            )

    for requirement in sorted(value for value in v1_scope if value.startswith("INF_REQ_")):
        if not _incoming(
            records,
            requirement,
            families=INFRASTRUCTURE_FAMILIES,
            relations=("implements",),
        ):
            errors.append(f"{requirement}: требование V1 не реализуется ни одним INF_CMP/INF_FLOW")

    registry = load_quality_registry(root)
    raw_catalog = registry.get("evidence_catalog", {})
    catalog = raw_catalog if isinstance(raw_catalog, dict) else {}
    for identifier, record in sorted(records.items()):
        if record.get("family") != "TEST":
            continue
        evidence = record.get("evidence", [])
        evidence_ids = [str(value) for value in evidence] if isinstance(evidence, list) else []
        if not evidence_ids:
            errors.append(f"{identifier}: TEST не связан с evidence")
            continue
        for evidence_id in evidence_ids:
            raw = catalog.get(evidence_id)
            if not isinstance(raw, dict):
                errors.append(f"{identifier}: неизвестный evidence '{evidence_id}'")
            elif not str(raw.get("source", "")).strip():
                errors.append(f"{identifier}: evidence '{evidence_id}' не имеет source")

    return errors


def milestone_test_coverage(root: Path, milestone_id: str) -> tuple[set[str], set[str]]:
    """Return required and directly verified requirement IDs for one milestone."""
    records = collect_traceable_elements(root)
    milestone = records.get(milestone_id.lower(), {})
    required = {
        target
        for target in _targets(milestone, "scope")
        if str(records.get(target, {}).get("family")) in TESTABLE_FAMILIES
    }
    covered: set[str] = set()
    for record in records.values():
        if record.get("family") != "TEST":
            continue
        if milestone_id.lower() not in {value.lower() for value in _targets(record, "accepts")}:
            continue
        covered.update(_targets(record, "verifies"))
    return required, covered
