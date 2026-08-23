from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import cast

from operations.scripts.documents.traceability import (
    collect_traceable_elements,
    parse_scope_references,
    render_traceability,
)


def _relations(record: dict[str, object]) -> dict[str, list[str]]:
    """`relations` is always dict[str, list[str]] by construction — see
    collect_traceable_elements() in traceability.py."""
    return cast(dict[str, list[str]], record["relations"])


class TraceabilityTests(unittest.TestCase):
    def test_repository_contains_all_traceable_families_and_relations(self) -> None:
        root = Path(__file__).resolve().parents[3]
        records = collect_traceable_elements(root)
        families = {str(record["family"]) for record in records.values()}
        for family in {
            "BR",
            "SYS",
            "THR",
            "SEC_CTL",
            "ARC_CMP",
            "ARC_FLOW",
            "INF_REQ",
            "INF_CMP",
            "INF_FLOW",
            "ADR",
            "TEST",
            "MILESTONE",
        }:
            self.assertIn(family, families)
        task_files = list((root / "work/tasks").glob("task_*.md"))
        self.assertEqual("TASK" in families, bool(task_files))

        self.assertEqual(records["THR_001"]["relations"], {"mitigated_by": ["SEC_CTL_001"]})
        self.assertEqual(records["SEC_CTL_001"]["relations"], {"traces_to": ["SYS_002"]})
        self.assertEqual(records["SYS_013"]["relations"], {"traces_to": ["BR_013"]})
        self.assertEqual(records["SYS_030"]["relations"], {"traces_to": ["BR_013", "BR_028"]})
        self.assertEqual(
            records["SYS_036"]["relations"],
            {"traces_to": ["BR_001", "BR_006", "BR_007", "BR_008", "BR_009"]},
        )
        self.assertEqual(
            len([record for record in records.values() if record["family"] == "SYS"]),
            36,
        )

        matrix = render_traceability(root)
        self.assertIn("| `THR_001` | `THR` | `mitigated_by`: `SEC_CTL_001` | — |", matrix)
        self.assertIn("| `SYS_030` | `SYS` | `traces_to`: `BR_013`, `BR_028` | — |", matrix)
        self.assertIn("| `TEST_0003` | `TEST` |", matrix)
        self.assertIn("`m02_contract_tests` |", matrix)
        self.assertNotIn("Входящие ссылки", matrix)

        for record in records.values():
            if record["family"] == "SEC_CTL":
                self.assertNotIn("mitigates", _relations(record))
                self.assertNotIn("implemented_by", _relations(record))

    def test_lower_layers_never_duplicate_the_threat_to_control_edge(self) -> None:
        """Связь «угроза — мера» хранится один раз, как THR.mitigated_by.
        Ссылка нижнего слоя на THR повторяла бы её в обход канонического направления."""
        root = Path(__file__).resolve().parents[3]
        records = collect_traceable_elements(root)
        offenders = {
            identifier: sorted(
                target
                for key in ("traces_to", "implements")
                for target in _relations(record).get(key, [])
                if target.startswith("THR_")
            )
            for identifier, record in records.items()
            if record["family"] != "THR"
        }
        self.assertEqual({k: v for k, v in offenders.items() if v}, {})

    def test_threat_reference_from_lower_layer_is_rejected(self) -> None:
        from operations.scripts.documents.check import check_traceability

        root = Path(__file__).resolve().parents[3]
        self.assertEqual(check_traceability(root).errors, [])
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp)
            (fake / "spec.md").write_text(
                "### THR_001 — Угроза\n\n- `mitigated_by`: `SEC_CTL_001`\n\n"
                "### INF_REQ_001 — Требование\n\n- `traces_to`: `SEC_CTL_001`, `THR_001`\n",
                encoding="utf-8",
            )
            records = collect_traceable_elements(fake)
            leaked = [
                target
                for target in _relations(records["INF_REQ_001"])["traces_to"]
                if target.startswith("THR_")
            ]
            self.assertEqual(leaked, ["THR_001"])

    def test_duplicate_traceable_id_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.md").write_text("### BR_001 — A\n", encoding="utf-8")
            (root / "b.md").write_text("### BR_001 — B\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Дублирующий"):
                collect_traceable_elements(root)

    def test_milestone_scope_uses_only_composition_line_and_expands_ranges(self) -> None:
        section = """
- work_state: `planned`
- состав: `BR_001`–`BR_003`, `SYS_002`, `SEC_CTL_001`–`SEC_CTL_002`

Подэтап упоминает `SYS_099`, но это не состав.
"""
        self.assertEqual(
            parse_scope_references(section),
            ["BR_001", "BR_002", "BR_003", "SEC_CTL_001", "SEC_CTL_002", "SYS_002"],
        )

    def test_repository_milestone_composition_is_not_silently_empty(self) -> None:
        root = Path(__file__).resolve().parents[3]
        records = collect_traceable_elements(root)
        self.assertEqual(
            _relations(records["m02"])["scope"][:6],
            ["BR_001", "BR_004", "BR_005", "BR_006", "BR_033", "BR_036"],
        )
        self.assertIn("SYS_027", _relations(records["m02"])["scope"])


if __name__ == "__main__":
    unittest.main()
