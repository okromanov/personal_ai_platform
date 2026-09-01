from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from operations.scripts.documents import diagram_lint


def _spec_text(version: str) -> str:
    return f"---\nversion: {version}\n---\n\n### ARC_CMP_001 — Test component\n\nBody text.\n"


def _svg_text(*, metadata_block: str = "", data_spec_ids: str = "") -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" '
        'viewBox="0 0 10 10" role="img" aria-labelledby="title desc">\n'
        '  <title id="title">Title</title>\n'
        '  <desc id="desc">Desc</desc>\n'
        f"{metadata_block}"
        f"  <g {data_spec_ids}></g>\n"
        "</svg>\n"
    )


def _metadata_block(*, sources: list[str], ids: list[str]) -> str:
    lines = [
        "  <!-- diagram-metadata",
        "diagram_id: test",
        "diagram_version: 1.0",
        "generated_at: 2026-09-01",
        "status: current",
        *(f"source: {value}" for value in sources),
        *(f"id: {value}" for value in ids),
        "end-diagram-metadata -->\n",
    ]
    return "\n".join(lines)


class DiagramLintTests(unittest.TestCase):
    def _write_spec(self, root: Path, version: str = "1.0") -> None:
        spec = root / "specifications" / "example.md"
        spec.parent.mkdir(parents=True, exist_ok=True)
        spec.write_text(_spec_text(version), encoding="utf-8")

    def test_lint_file_passes_on_well_formed_diagram(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_spec(root, version="1.0")
            metadata = _metadata_block(
                sources=["specifications/example.md@1.0"], ids=["ARC_CMP_001"]
            )
            svg = root / "diagram.svg"
            svg.write_text(
                _svg_text(metadata_block=metadata, data_spec_ids='data-spec-id="ARC_CMP_001"'),
                encoding="utf-8",
            )
            result = diagram_lint.lint_file(svg, root)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.warnings, [])
        self.assertTrue(result.ok)

    def test_lint_file_reports_missing_metadata_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            svg = root / "diagram.svg"
            svg.write_text(_svg_text(), encoding="utf-8")
            result = diagram_lint.lint_file(svg, root)
        self.assertFalse(result.ok)
        self.assertTrue(any("diagram-metadata" in error for error in result.errors))

    def test_lint_file_reports_structure_problems(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            svg = root / "diagram.svg"
            svg.write_text('<svg width="10" height="10"></svg>', encoding="utf-8")
            result = diagram_lint.lint_file(svg, root)
        self.assertFalse(result.ok)
        self.assertTrue(any("viewBox" in error for error in result.errors))
        self.assertTrue(any("title" in error for error in result.errors))
        self.assertTrue(any('role="img"' in error for error in result.errors))

    def test_check_sources_reports_bad_format_missing_file_and_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_spec(root, version="1.0")
            metadata = _metadata_block(
                sources=[
                    "badformat",
                    "specifications/missing.md@1.0",
                    "specifications/example.md@0.1",
                ],
                ids=["ARC_CMP_001"],
            )
            svg = root / "diagram.svg"
            svg.write_text(
                _svg_text(metadata_block=metadata, data_spec_ids='data-spec-id="ARC_CMP_001"'),
                encoding="utf-8",
            )
            result = diagram_lint.lint_file(svg, root)
        self.assertFalse(result.ok)
        self.assertTrue(any("не в формате" in error for error in result.errors))
        self.assertTrue(any("несуществующий файл" in error for error in result.errors))
        self.assertTrue(any("дрейф версии" in error for error in result.errors))

    def test_check_ids_reports_unknown_missing_and_extra(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_spec(root, version="1.0")
            metadata = _metadata_block(
                sources=["specifications/example.md@1.0"],
                ids=["ARC_CMP_001", "ARC_CMP_999"],
            )
            svg = root / "diagram.svg"
            svg.write_text(
                _svg_text(metadata_block=metadata, data_spec_ids='data-spec-id="ARC_CMP_888"'),
                encoding="utf-8",
            )
            result = diagram_lint.lint_file(svg, root)
        self.assertFalse(result.ok)
        self.assertTrue(
            any("ARC_CMP_999" in error and "не найден" in error for error in result.errors)
        )
        self.assertTrue(
            any(
                "ARC_CMP_001" in error and "не несёт data-spec-id" in error
                for error in result.errors
            )
        )
        self.assertTrue(
            any("ARC_CMP_888" in error and "не заявлен" in error for error in result.errors)
        )

    def test_check_ids_rejects_a_compressed_multi_id_attribute(self) -> None:
        """The style guide requires exactly one ID per data-spec-id-bearing
        element -- a node that visually compresses several IDs into one
        label must still tag each with its own element (see the
        INF_CMP_001..008 tspans in the real diagram), not a combined,
        space-separated attribute value."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec = root / "specifications" / "example.md"
            spec.parent.mkdir(parents=True, exist_ok=True)
            spec.write_text(
                "---\nversion: 1.0\n---\n\n"
                "### ARC_CMP_001 — First\n\nBody.\n\n"
                "### ARC_CMP_002 — Second\n\nBody.\n",
                encoding="utf-8",
            )
            metadata = _metadata_block(
                sources=["specifications/example.md@1.0"],
                ids=["ARC_CMP_001", "ARC_CMP_002"],
            )
            svg = root / "diagram.svg"
            svg.write_text(
                _svg_text(
                    metadata_block=metadata,
                    data_spec_ids='data-spec-id="ARC_CMP_001 ARC_CMP_002"',
                ),
                encoding="utf-8",
            )
            result = diagram_lint.lint_file(svg, root)
        self.assertFalse(result.ok)
        self.assertTrue(any("ARC_CMP_001 ARC_CMP_002" in error for error in result.errors))

    def test_check_ids_accepts_one_id_per_tspan_for_a_compressed_label(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec = root / "specifications" / "example.md"
            spec.parent.mkdir(parents=True, exist_ok=True)
            spec.write_text(
                "---\nversion: 1.0\n---\n\n"
                "### ARC_CMP_001 — First\n\nBody.\n\n"
                "### ARC_CMP_002 — Second\n\nBody.\n",
                encoding="utf-8",
            )
            metadata = _metadata_block(
                sources=["specifications/example.md@1.0"],
                ids=["ARC_CMP_001", "ARC_CMP_002"],
            )
            svg = root / "diagram.svg"
            svg.write_text(
                _svg_text(
                    metadata_block=metadata,
                    data_spec_ids="",
                ).replace(
                    "<g ></g>",
                    '<text><tspan data-spec-id="ARC_CMP_001">First</tspan> · '
                    '<tspan data-spec-id="ARC_CMP_002">Second</tspan></text>',
                ),
                encoding="utf-8",
            )
            result = diagram_lint.lint_file(svg, root)
        self.assertEqual(result.errors, [])

    def test_default_targets_empty_without_artefacts_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(diagram_lint.default_targets(root), [])

    def test_default_targets_lists_svgs_under_work_artefacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / "work" / "artefacts" / "architecture"
            nested.mkdir(parents=True)
            svg_b = nested / "b.svg"
            svg_a = nested / "a.svg"
            svg_b.write_text("<svg></svg>", encoding="utf-8")
            svg_a.write_text("<svg></svg>", encoding="utf-8")
            self.assertEqual(diagram_lint.default_targets(root), [svg_a, svg_b])

    def test_main_reports_no_targets_when_artefacts_directory_is_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with (
                patch.object(diagram_lint, "find_project_root", return_value=root),
                patch.object(diagram_lint, "require_supported_python"),
                patch("sys.argv", ["diagram_lint"]),
            ):
                self.assertEqual(diagram_lint.main(), 0)

    def test_main_passes_explicit_valid_file_and_fails_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_spec(root, version="1.0")
            metadata = _metadata_block(
                sources=["specifications/example.md@1.0"], ids=["ARC_CMP_001"]
            )
            svg = root / "diagram.svg"
            svg.write_text(
                _svg_text(metadata_block=metadata, data_spec_ids='data-spec-id="ARC_CMP_001"'),
                encoding="utf-8",
            )
            with (
                patch.object(diagram_lint, "find_project_root", return_value=root),
                patch.object(diagram_lint, "require_supported_python"),
                patch("sys.argv", ["diagram_lint", str(svg)]),
            ):
                self.assertEqual(diagram_lint.main(), 0)

            with (
                patch.object(diagram_lint, "find_project_root", return_value=root),
                patch.object(diagram_lint, "require_supported_python"),
                patch("sys.argv", ["diagram_lint", str(root / "missing.svg")]),
            ):
                self.assertEqual(diagram_lint.main(), 1)


if __name__ == "__main__":
    unittest.main()
