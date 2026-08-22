#!/usr/bin/env python3.12
"""Stage-aware coverage of testable milestone requirements by TEST specs."""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from operations.scripts.documents.traceability import collect_traceable_elements
from operations.scripts.status.generate_project_status import collect_milestones
from operations.scripts.traceability.full_traceability import milestone_test_coverage


def find_system_requirements(root: Path) -> set[str]:
    """Return all directly testable SYS, SEC_CTL and INF_REQ requirements."""
    return {
        identifier
        for identifier, record in collect_traceable_elements(root).items()
        if record.get("family") in {"SYS", "SEC_CTL", "INF_REQ"}
    }


def find_test_requirements(root: Path) -> dict[str, list[str]]:
    """Найти требования, на которые ссылаются тесты.

    Возвращает: {TEST_ID: [требования, на которые ссылается]}
    """
    records = collect_traceable_elements(root)
    result: dict[str, list[str]] = {}
    for identifier, record in records.items():
        if record.get("family") != "TEST":
            continue
        relations = record.get("relations", {})
        values = relations.get("verifies", []) if isinstance(relations, dict) else []
        result[identifier] = [str(value) for value in values] if isinstance(values, list) else []
    return result


def validate_test_coverage(root: Path, skip_for_m01: bool = True) -> list[str]:
    """Валидировать покрытие требований тестами.

    Аргументы:
        skip_for_m01: если True, пропустить проверку на этапе m01
               (основные тесты будут добавлены на этапе m02+)

    Возвращает список ошибок.
    """
    errors: list[str] = []

    # Если skip_for_m01 включен, пропустить проверку только пока m01 — текущий
    # этап. Подстрочный поиск "m01" в milestones.md всегда истинен (заголовок
    # m01 никуда не девается после завершения этапа), поэтому определяем
    # текущий этап тем же способом, что и остальной код (collect_milestones),
    # а не поиском по тексту.
    raw_current = collect_milestones(root).get("current")
    if not isinstance(raw_current, dict):
        return ["Не удалось определить текущий milestone для проверки TEST coverage"]
    current = raw_current
    milestone_id = str(current["id"]).lower()
    work_state = str(current.get("work_state", "planned"))
    if skip_for_m01 and milestone_id == "m01":
        return []
    if work_state == "planned":
        return []

    required, covered = milestone_test_coverage(root, milestone_id)
    for requirement in sorted(required - covered):
        errors.append(
            f"{milestone_id}: {requirement} не покрыт TEST, который accepts этот milestone"
        )

    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[3]
    errors = validate_test_coverage(root)

    if errors:
        print("❌ Ошибки покрытия тестами:")
        for error in sorted(errors):
            print(f"  {error}")
        return 1

    print("✅ Все требования покрыты тестами")
    return 0


if __name__ == "__main__":
    sys.exit(main())
