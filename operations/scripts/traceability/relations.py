"""Shared accessors for normalized traceability relations."""


def relation_targets(record: dict[str, object], relation: str) -> set[str]:
    """Return string targets from one normalized relation list."""
    relations = record.get("relations", {})
    if not isinstance(relations, dict):
        return set()
    values = relations.get(relation, [])
    return {str(value) for value in values} if isinstance(values, list) else set()
