from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from operations.scripts.evidence.record import _evidence_targets
from operations.scripts.quality.registry import (
    evaluate_milestone_quality,
    validate_quality_registry,
)


class AcceptanceTests(unittest.TestCase):
    def _checks(self, ok: bool = True) -> dict[str, object]:
        return {
            "ok": ok,
            "checks": [{"name": "project", "ok": ok, "errors": [], "warnings": []}],
        }

    def _registry(self) -> dict[str, object]:
        return {
            "version": 2,
            "evidence_catalog": {
                "project_checks": {"class": "hard", "source": "checker"},
                "unit_tests": {"class": "hard", "source": "unit_tests"},
            },
            "profiles": {
                "foundation": {
                    "milestones": ["m01"],
                    "paths": ["*.md"],
                    "scope_coverage": "global_evidence",
                    "scope_evidence": ["project_checks"],
                    "required_evidence": ["project_checks", "unit_tests"],
                }
            },
        }

    def test_foundation_profile_passes_only_with_required_evidence_and_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "operations").mkdir()
            (root / "operations/quality_registry.json").write_text(
                json.dumps(self._registry()), encoding="utf-8"
            )
            context = {
                "git_sha": "a" * 40,
                "timestamp": "2026-08-13T10:00:00+03:00",
                "environment": {"os": "Windows", "python": "3.12"},
            }
            m01 = evaluate_milestone_quality(
                root,
                "m01",
                check_summary=self._checks(),
                unit_summary={"ok": True},
                context=context,
            )
            self.assertTrue(m01["ready"], m01)
            self.assertEqual({row["git_sha"] for row in m01["evidence"]}, {"a" * 40})
            self.assertTrue(all(row["environment"] for row in m01["evidence"]))

            m02 = evaluate_milestone_quality(
                root,
                "m02",
                check_summary=self._checks(),
                unit_summary={"ok": True},
                context=context,
            )
            self.assertFalse(m02["ready"])
            self.assertIn("quality profile missing for m02", "\n".join(m02["blockers"]))
            self.assertEqual(validate_quality_registry(root, {"m01", "m02"}), [])

    def test_foundation_evidence_targets_machine_path_scope_when_product_scope_is_empty(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "operations").mkdir()
            registry = self._registry()
            registry["profiles"]["foundation"]["paths"] = ["*.md", "operations/**"]
            (root / "operations/quality_registry.json").write_text(
                json.dumps(registry), encoding="utf-8"
            )
            snapshot = {
                "current": {"id": "m01"},
                "acceptance": {
                    "coverage": {
                        "scope": [],
                        "tracked_targets": ["path:*.md", "path:operations/**"],
                    },
                    "tests": [],
                },
            }
            targets = _evidence_targets(root, snapshot)
            self.assertEqual(targets["project_checks"], ["path:*.md", "path:operations/**"])
            self.assertTrue(
                all(
                    targets[evidence_id]
                    for evidence_id in registry["profiles"]["foundation"]["required_evidence"]
                )
            )

    def test_invalid_global_coverage_profile_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "operations").mkdir()
            registry = self._registry()
            registry["profiles"]["foundation"]["scope_evidence"] = []
            (root / "operations/quality_registry.json").write_text(
                json.dumps(registry), encoding="utf-8"
            )
            errors = validate_quality_registry(root, {"m01"})
            self.assertTrue(any("scope_evidence" in item for item in errors), errors)


if __name__ == "__main__":
    unittest.main()
