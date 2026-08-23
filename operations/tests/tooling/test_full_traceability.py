from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from operations.scripts.traceability.full_traceability import (
    milestone_test_coverage,
    validate_full_traceability,
)


class FullTraceabilityTests(unittest.TestCase):
    def test_repository_has_complete_v1_chains_and_test_evidence(self) -> None:
        root = Path(__file__).resolve().parents[3]
        self.assertEqual(validate_full_traceability(root), [])
        required, covered = milestone_test_coverage(root, "m02")
        self.assertIn("INF_REQ_006", required)
        self.assertIn("SYS_003", covered)
        self.assertIn("INF_REQ_006", covered)
        self.assertEqual(required - covered, set())

    def test_missing_decomposition_architecture_infrastructure_and_evidence_are_rejected(
        self,
    ) -> None:
        records: dict[str, dict[str, object]] = {
            "BR_001": {
                "family": "BR",
                "section": "- `priority`: `core`",
                "relations": {},
            },
            "SYS_001": {"family": "SYS", "relations": {"traces_to": ["BR_001"]}},
            "INF_REQ_001": {"family": "INF_REQ", "relations": {}},
            "TEST_001": {
                "family": "TEST",
                "relations": {"accepts": ["m02"], "verifies": ["SYS_001"]},
                "evidence": ["missing_evidence"],
            },
            "TEST_002": {
                "family": "TEST",
                "relations": {"accepts": ["m02"], "verifies": ["SYS_001"]},
                "evidence": [],
            },
            "TEST_003": {
                "family": "TEST",
                "relations": {"accepts": ["m02"], "verifies": ["SYS_001"]},
                "evidence": ["evidence_without_source"],
            },
            "m02": {
                "family": "MILESTONE",
                "relations": {"scope": ["BR_001", "SYS_001", "INF_REQ_001"]},
            },
        }
        with (
            patch(
                "operations.scripts.traceability.full_traceability.collect_traceable_elements",
                return_value=records,
            ),
            patch(
                "operations.scripts.traceability.full_traceability.v1_milestone_ids",
                return_value=["m02"],
            ),
            patch(
                "operations.scripts.traceability.full_traceability.load_quality_registry",
                return_value={"evidence_catalog": {"evidence_without_source": {"source": ""}}},
            ),
        ):
            errors = validate_full_traceability(Path("."))
        joined = "\n".join(errors)
        self.assertIn("прямого покрытия ARC_CMP/ARC_FLOW", joined)
        self.assertIn("INF_CMP/INF_FLOW", joined)
        self.assertIn("неизвестный evidence", joined)
        self.assertIn("TEST не связан с evidence", joined)
        self.assertIn("не имеет source", joined)

    def test_core_requirement_without_system_decomposition_is_rejected(self) -> None:
        records: dict[str, dict[str, object]] = {
            "BR_001": {
                "family": "BR",
                "section": "- `priority`: `core`",
                "relations": {},
            },
            "m02": {"family": "MILESTONE", "relations": {"scope": ["BR_001"]}},
        }
        with (
            patch(
                "operations.scripts.traceability.full_traceability.collect_traceable_elements",
                return_value=records,
            ),
            patch(
                "operations.scripts.traceability.full_traceability.v1_milestone_ids",
                return_value=["m02"],
            ),
            patch(
                "operations.scripts.traceability.full_traceability.load_quality_registry",
                return_value={"evidence_catalog": {}},
            ),
        ):
            errors = validate_full_traceability(Path("."))
        self.assertTrue(any("не декомпозирован" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
