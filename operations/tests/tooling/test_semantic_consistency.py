from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from operations.scripts.traceability.semantic_consistency import validate_semantic_consistency


class SemanticConsistencyTests(unittest.TestCase):
    def test_repository_semantics_are_consistent(self) -> None:
        root = Path(__file__).resolve().parents[3]
        self.assertEqual(validate_semantic_consistency(root), [])

    def test_implicit_system_dependency_is_rejected(self) -> None:
        records: dict[str, dict[str, object]] = {
            "SYS_014": {"family": "SYS", "relations": {}, "section": ""},
            "SYS_015": {
                "family": "SYS",
                "relations": {"traces_to": ["BR_001"]},
                "section": "Результат строится из SYS_014.",
            },
        }
        with (
            patch(
                "operations.scripts.traceability.semantic_consistency.collect_traceable_elements",
                return_value=records,
            ),
            patch(
                "operations.scripts.traceability.semantic_consistency.v1_milestone_ids",
                return_value=[],
            ),
        ):
            errors = validate_semantic_consistency(Path("."))
        self.assertIn("структурный depends_on отсутствует", "\n".join(errors))

    def test_adr_target_from_another_stage_is_rejected(self) -> None:
        records: dict[str, dict[str, object]] = {
            "SYS_030": {"family": "SYS", "relations": {}, "section": ""},
            "ADR_007": {
                "family": "ADR",
                "relations": {"traces_to": ["m02", "SYS_030"]},
                "section": "",
            },
            "m02": {"family": "MILESTONE", "relations": {"scope": []}},
            "m05": {"family": "MILESTONE", "relations": {"scope": ["SYS_030"]}},
        }
        with (
            patch(
                "operations.scripts.traceability.semantic_consistency.collect_traceable_elements",
                return_value=records,
            ),
            patch(
                "operations.scripts.traceability.semantic_consistency.v1_milestone_ids",
                return_value=["m02", "m05"],
            ),
        ):
            errors = validate_semantic_consistency(Path("."))
        joined = "\n".join(errors)
        self.assertIn("SYS_030 относится к ['m05']", joined)
        self.assertIn("milestone m02 не подтверждён", joined)


if __name__ == "__main__":
    unittest.main()
