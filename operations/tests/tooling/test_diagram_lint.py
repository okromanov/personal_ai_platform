from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from operations.scripts.documents import diagram_geometry_lint, diagram_lint


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
        "end-diagram-metadata -->",
        # A compliant header caption matching diagram_version/generated_at
        # above (diagram_geometry_foundations.md §13.1) -- present here so
        # every other test in this file, unrelated to that check, does not
        # also have to know about it. See CheckVisibleMetaTests for the
        # dedicated coverage of _check_visible_meta itself.
        '  <text data-diagram-meta="version">Версия 1.0 · Обновлено 2026-09-01</text>\n',
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

    def test_lint_file_rejects_xml_entities_without_expansion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sentinel = "ENTITY_CONTENT_MUST_NOT_BE_EXPANDED"
            svg = root / "diagram.svg"
            svg.write_text(
                "<!DOCTYPE svg [<!ENTITY payload '" + sentinel + "'>]>\n"
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10" '
                'role="img" aria-labelledby="title desc">\n'
                '<title id="title">&payload;</title><desc id="desc">Desc</desc>\n'
                "</svg>\n",
                encoding="utf-8",
            )

            result = diagram_lint.lint_file(svg, root)

        self.assertFalse(result.ok)
        self.assertTrue(any("корректным XML/SVG" in error for error in result.errors))
        self.assertNotIn(sentinel, " ".join(result.errors))

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

    def test_lint_file_accepts_empty_id_list_with_no_data_spec_id(self) -> None:
        """process_diagram_style_guide.md §2.1 / diagram_geometry_foundations.md
        §13: a diagram tracing no registry element may omit `id` lines
        entirely while still carrying `source` lines."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_spec(root, version="1.0")
            metadata = _metadata_block(sources=["specifications/example.md@1.0"], ids=[])
            svg = root / "diagram.svg"
            svg.write_text(_svg_text(metadata_block=metadata), encoding="utf-8")
            result = diagram_lint.lint_file(svg, root)
        self.assertEqual(result.errors, [])

    def test_lint_file_rejects_untracked_data_spec_id_with_empty_id_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_spec(root, version="1.0")
            metadata = _metadata_block(sources=["specifications/example.md@1.0"], ids=[])
            svg = root / "diagram.svg"
            svg.write_text(
                _svg_text(metadata_block=metadata, data_spec_ids='data-spec-id="ARC_CMP_001"'),
                encoding="utf-8",
            )
            result = diagram_lint.lint_file(svg, root)
        self.assertFalse(result.ok)
        self.assertTrue(
            any("ARC_CMP_001" in error and "не заявлен" in error for error in result.errors)
        )

    def _svg_with_caption(self, *, diagram_version: str, generated_at: str, caption: str) -> str:
        lines = [
            "  <!-- diagram-metadata",
            "diagram_id: test",
            f"diagram_version: {diagram_version}",
            f"generated_at: {generated_at}",
            "status: current",
            "source: specifications/example.md@1.0",
            "id: ARC_CMP_001",
            "end-diagram-metadata -->",
            f'  <text data-diagram-meta="version">{caption}</text>\n',
        ]
        metadata = "\n".join(lines)
        return _svg_text(metadata_block=metadata, data_spec_ids='data-spec-id="ARC_CMP_001"')

    def test_check_visible_meta_reports_a_missing_caption(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_spec(root, version="1.0")
            metadata = _metadata_block(
                sources=["specifications/example.md@1.0"], ids=["ARC_CMP_001"]
            )
            # Strip the auto-injected caption _metadata_block() normally adds,
            # to exercise the "absent entirely" case on its own.
            metadata = metadata.split("  <text data-diagram-meta")[0]
            svg = root / "diagram.svg"
            svg.write_text(
                _svg_text(metadata_block=metadata, data_spec_ids='data-spec-id="ARC_CMP_001"'),
                encoding="utf-8",
            )
            result = diagram_lint.lint_file(svg, root)
        self.assertFalse(result.ok)
        self.assertTrue(
            any(
                "отсутствует видимая строка версии" in error and "data-diagram-meta" in error
                for error in result.errors
            )
        )

    def test_check_visible_meta_accepts_a_matching_caption(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_spec(root, version="1.0")
            svg = root / "diagram.svg"
            svg.write_text(
                self._svg_with_caption(
                    diagram_version="1.4",
                    generated_at="2026-09-02T17:20:00+00:00",
                    caption="Версия 1.4 · Обновлено 2026-09-02 17:20 UTC",
                ),
                encoding="utf-8",
            )
            result = diagram_lint.lint_file(svg, root)
        self.assertEqual(result.errors, [])

    def test_check_visible_meta_reports_version_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_spec(root, version="1.0")
            svg = root / "diagram.svg"
            svg.write_text(
                self._svg_with_caption(
                    diagram_version="1.4",
                    generated_at="2026-09-02T17:20:00+00:00",
                    caption="Версия 1.9 · Обновлено 2026-09-02 17:20 UTC",
                ),
                encoding="utf-8",
            )
            result = diagram_lint.lint_file(svg, root)
        self.assertFalse(result.ok)
        self.assertTrue(
            any(
                "'1.9'" in error and "diagram_version" in error and "'1.4'" in error
                for error in result.errors
            )
        )

    def test_check_visible_meta_reports_date_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_spec(root, version="1.0")
            svg = root / "diagram.svg"
            svg.write_text(
                self._svg_with_caption(
                    diagram_version="1.4",
                    generated_at="2026-09-02T17:20:00+00:00",
                    caption="Версия 1.4 · Обновлено 2026-09-03 17:20 UTC",
                ),
                encoding="utf-8",
            )
            result = diagram_lint.lint_file(svg, root)
        self.assertFalse(result.ok)
        self.assertTrue(
            any(
                "'2026-09-03'" in error and "Даты обязаны совпадать" in error
                for error in result.errors
            )
        )

    def test_check_visible_meta_reports_time_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_spec(root, version="1.0")
            svg = root / "diagram.svg"
            svg.write_text(
                self._svg_with_caption(
                    diagram_version="1.4",
                    generated_at="2026-09-02T17:20:00+00:00",
                    caption="Версия 1.4 · Обновлено 2026-09-02 18:45 UTC",
                ),
                encoding="utf-8",
            )
            result = diagram_lint.lint_file(svg, root)
        self.assertFalse(result.ok)
        self.assertTrue(any("'18:45'" in error and "время" in error for error in result.errors))

    def test_check_visible_meta_reports_time_missing_from_metadata(self) -> None:
        """generated_at with a date but no time, alongside a caption that
        does show a time: the caption is claiming a fact the metadata does
        not actually carry, which is exactly the drift this check exists
        to catch (diagram_geometry_foundations.md §13.1)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_spec(root, version="1.0")
            svg = root / "diagram.svg"
            svg.write_text(
                self._svg_with_caption(
                    diagram_version="1.4",
                    generated_at="2026-09-02",
                    caption="Версия 1.4 · Обновлено 2026-09-02 17:20 UTC",
                ),
                encoding="utf-8",
            )
            result = diagram_lint.lint_file(svg, root)
        self.assertFalse(result.ok)
        self.assertTrue(
            any(
                "'17:20'" in error and "не содержит совпадающего времени" in error
                for error in result.errors
            )
        )

    def test_check_visible_meta_skips_a_non_numeric_placeholder_caption(self) -> None:
        """Template skeletons (operations/architecture/templates/) carry a
        literal, non-numeric placeholder caption on purpose -- it has
        nothing real to compare against its own diagram_version/generated_at
        (which describe the skeleton's own revision, not the eventual
        filled-in diagram's), so no drift error is expected here."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_spec(root, version="1.0")
            svg = root / "diagram.svg"
            svg.write_text(
                self._svg_with_caption(
                    diagram_version="1.1",
                    generated_at="2026-09-02",
                    caption="Версия X.Y · Обновлено ГГГГ-ММ-ДД ЧЧ:ММ",
                ),
                encoding="utf-8",
            )
            result = diagram_lint.lint_file(svg, root)
        self.assertEqual(result.errors, [])

    def test_geometry_check_passes_grid_aligned_svg(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_spec(root, version="1.0")
            metadata = _metadata_block(
                sources=["specifications/example.md@1.0"], ids=["ARC_CMP_001"]
            )
            svg = root / "diagram.svg"
            svg.write_text(
                _svg_text(
                    metadata_block=metadata, data_spec_ids='data-spec-id="ARC_CMP_001"'
                ).replace(
                    '<g data-spec-id="ARC_CMP_001"></g>',
                    '<g data-spec-id="ARC_CMP_001">'
                    '<rect x="8" y="8.5" width="20" height="16" rx="4"/>'
                    '<line x1="4" y1="4" x2="8" y2="8"/>'
                    '<path d="M0 0L10 5.5L0 10Z"/>'
                    "</g>",
                ),
                encoding="utf-8",
            )
            result = diagram_lint.lint_file(svg, root)
        self.assertEqual(result.errors, [])

    def test_geometry_check_reports_off_grid_fractional_coordinate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_spec(root, version="1.0")
            metadata = _metadata_block(
                sources=["specifications/example.md@1.0"], ids=["ARC_CMP_001"]
            )
            svg = root / "diagram.svg"
            svg.write_text(
                _svg_text(
                    metadata_block=metadata, data_spec_ids='data-spec-id="ARC_CMP_001"'
                ).replace(
                    '<g data-spec-id="ARC_CMP_001"></g>',
                    '<g data-spec-id="ARC_CMP_001">'
                    '<rect x="8.33" y="8" width="20" height="16"/>'
                    "</g>",
                ),
                encoding="utf-8",
            )
            result = diagram_lint.lint_file(svg, root)
        self.assertFalse(result.ok)
        self.assertTrue(
            any("8.33" in error and "дробная координата" in error for error in result.errors)
        )

    def test_geometry_check_passes_consistent_marker_sizes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_spec(root, version="1.0")
            metadata = _metadata_block(
                sources=["specifications/example.md@1.0"], ids=["ARC_CMP_001"]
            )
            svg = root / "diagram.svg"
            svg.write_text(
                _svg_text(metadata_block=metadata, data_spec_ids='data-spec-id="ARC_CMP_001"')
                .replace(
                    "<title",
                    '<marker id="a" markerWidth="6" markerHeight="6"></marker>'
                    '<marker id="b" markerWidth="6" markerHeight="6"></marker><title',
                    1,
                )
                .replace(
                    "</svg>",
                    '  <path marker-end="url(#a)"/>\n  <path marker-end="url(#b)"/>\n</svg>',
                    1,
                ),
                encoding="utf-8",
            )
            result = diagram_lint.lint_file(svg, root)
        self.assertEqual(result.errors, [])

    def test_geometry_check_reports_inconsistent_marker_sizes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_spec(root, version="1.0")
            metadata = _metadata_block(
                sources=["specifications/example.md@1.0"], ids=["ARC_CMP_001"]
            )
            svg = root / "diagram.svg"
            svg.write_text(
                _svg_text(
                    metadata_block=metadata, data_spec_ids='data-spec-id="ARC_CMP_001"'
                ).replace(
                    "<title",
                    '<marker id="a" markerWidth="6" markerHeight="6"></marker>'
                    '<marker id="b" markerWidth="8" markerHeight="6"></marker><title',
                ),
                encoding="utf-8",
            )
            result = diagram_lint.lint_file(svg, root)
        self.assertFalse(result.ok)
        self.assertTrue(
            any("markerWidth" in error and "не единообразен" in error for error in result.errors)
        )

    def test_section_divider_is_checked_from_surrounding_geometry(self) -> None:
        valid = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg"><g>'
            '<rect y="10" height="20"/>'
            '<line x1="0" y1="40" x2="100" y2="40" class="section-divider"/>'
            '<rect y="50" height="20"/>'
            "</g></svg>"
        )
        invalid = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg"><g>'
            '<rect y="10" height="20"/>'
            '<line x1="0" y1="41" x2="100" y2="41" class="section-divider"/>'
            '<rect y="50" height="20"/>'
            "</g></svg>"
        )

        self.assertEqual(valid.errors, [])
        self.assertTrue(
            any("сверху 11 px, снизу 9 px" in error for error in invalid.errors),
            invalid.errors,
        )

    def test_section_divider_rejects_an_invalid_contract(self) -> None:
        wrong_element = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<path class="section-divider" d="M0 0H10"/>'
            "</svg>"
        )
        non_horizontal = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<line class="section-divider" x1="0" y1="0" x2="10" y2="10"/>'
            "</svg>"
        )
        no_rows = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<line class="section-divider" x1="0" y1="10" x2="10" y2="10"/>'
            "</svg>"
        )

        self.assertTrue(any("элементом <line>" in error for error in wrong_element.errors))
        self.assertTrue(any("горизонтальным" in error for error in non_horizontal.errors))
        self.assertTrue(any("между рядами" in error for error in no_rows.errors))

    def test_declared_direct_route_is_checked_from_path_geometry(self) -> None:
        valid = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<path d="M0 0V10" data-route="direct"/>'
            '<path d="M0 0L10 0" data-route="direct"/>'
            "</svg>"
        )
        bent = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<path d="M0 0V10H20" data-route="direct"/>'
            "</svg>"
        )
        diagonal = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<path d="M0 0L10 10" data-route="direct"/>'
            "</svg>"
        )

        self.assertEqual(valid.errors, [])
        self.assertTrue(any("ровно из одного" in error for error in bent.errors))
        self.assertTrue(
            any("горизонтальным или вертикальным" in error for error in diagonal.errors)
        )

    def test_declared_bottom_alignment_is_calculated_after_translation(self) -> None:
        matching = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<rect id="anchor" x="0" y="10" width="100" height="40"/>'
            '<g transform="translate(0 20)">'
            '<rect id="label" x="0" y="0" width="40" height="30" '
            'data-align-bottom-with="anchor"/></g></svg>'
        )
        drifted = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<rect id="anchor" x="0" y="10" width="100" height="40"/>'
            '<rect id="label" x="0" y="0" width="40" height="44" '
            'data-align-bottom-with="anchor"/></svg>'
        )
        self.assertEqual(matching.errors, [])
        self.assertTrue(any("нижняя граница" in error for error in drifted.errors))

    def test_declared_bottom_alignment_rejects_invalid_references(self) -> None:
        wrong_element = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<rect id="anchor" x="0" y="0" width="10" height="10"/>'
            '<g data-align-bottom-with="anchor"/></svg>'
        )
        missing_target = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<rect id="label" x="0" y="0" width="10" height="10" '
            'data-align-bottom-with="missing"/></svg>'
        )
        non_rect_target = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<text id="anchor" x="0" y="10">anchor</text>'
            '<rect id="label" x="0" y="0" width="10" height="10" '
            'data-align-bottom-with="anchor"/></svg>'
        )
        invalid_geometry = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<rect id="anchor" x="0" y="0" width="10" height="10"/>'
            '<rect id="label" x="0" y="bad" width="10" height="10" '
            'data-align-bottom-with="anchor"/></svg>'
        )

        self.assertTrue(any("только для <rect>" in error for error in wrong_element.errors))
        self.assertTrue(any("отсутствующий элемент" in error for error in missing_target.errors))
        self.assertTrue(any("указывать на <rect>" in error for error in non_rect_target.errors))
        self.assertTrue(
            any("выравнивание нижних границ" in error for error in invalid_geometry.errors)
        )

    def test_declared_direct_route_rejects_invalid_metadata(self) -> None:
        result = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<path d="M0 0V10" data-route="curved"/>'
            '<line x1="0" y1="0" x2="0" y2="10" data-route="direct"/>'
            "</svg>"
        )

        self.assertTrue(any("неподдерживаемое" in error for error in result.errors))
        self.assertTrue(any("только для <path>" in error for error in result.errors))

    def test_shared_route_may_touch_but_not_cross_a_card(self) -> None:
        valid = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<g transform="translate(10 20)">'
            '<path d="M50 -10V0" data-shared-route="true"/>'
            '<rect id="gate" x="0" y="0" width="100" height="100" '
            'class="control-card"/>'
            "</g></svg>"
        )
        crossing = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<g transform="translate(10 20)">'
            '<path d="M50 -10V110" data-shared-route="true"/>'
            '<rect id="gate" x="0" y="0" width="100" height="100" '
            'class="control-card"/>'
            "</g></svg>"
        )

        self.assertEqual(valid.errors, [])
        self.assertTrue(
            any(
                "внутреннюю область карточки 'gate'" in error and "data-source-ref" in error
                for error in crossing.errors
            ),
            crossing.errors,
        )

    def test_shared_route_must_be_one_direct_segment(self) -> None:
        result = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<path d="M0 0V10H20" data-shared-route="true"/>'
            "</svg>"
        )

        self.assertTrue(
            any("shared-route" in error and "одного" in error for error in result.errors),
            result.errors,
        )

    def test_shared_route_rejects_invalid_elements_and_transforms(self) -> None:
        result = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<rect x="0" width="10" height="10" class="control-card"/>'
            '<g transform="scale(2)">'
            '<rect x="0" y="0" width="10" height="10" class="control-card"/>'
            '<path d="M20 0V10" data-shared-route="true"/>'
            "</g>"
            '<line x1="0" y1="0" x2="0" y2="10" data-shared-route="true"/>'
            "</svg>"
        )

        self.assertTrue(any("числовые x, y, width и height" in e for e in result.errors))
        self.assertTrue(any("отличный от translate" in e for e in result.errors))
        self.assertTrue(
            any('data-shared-route="true" разрешён только для <path>' in e for e in result.errors)
        )

    def test_connector_source_attachment_resolves_transforms(self) -> None:
        result = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<g transform="translate(10 20)">'
            '<rect id="source" x="0" y="0" width="100" height="60"/>'
            '<path d="M50 60V80" data-source-ref="source" data-route="direct"/>'
            "</g></svg>"
        )

        self.assertEqual(result.errors, [])

    def test_connector_source_attachment_rejects_a_hanging_start(self) -> None:
        result = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<rect id="source" x="10" y="20" width="100" height="60"/>'
            '<path d="M60 84V100" data-source-ref="source" data-route="direct"/>'
            "</svg>"
        )

        self.assertTrue(
            any("не на границе источника" in error for error in result.errors),
            result.errors,
        )

    def test_connector_source_attachment_skips_unresolvable_contracts(self) -> None:
        result = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<text id="not-a-rect" x="0" y="0">source</text>'
            '<path d="bad" data-source-ref="not-a-rect"/>'
            '<g transform="scale(2)">'
            '<rect id="scaled-source" x="0" y="0" width="100" height="60"/>'
            '<path d="M50 60V80" data-source-ref="scaled-source"/>'
            "</g></svg>"
        )

        self.assertTrue(any("отличный от translate" in error for error in result.errors))

    def test_control_transition_cards_share_calculated_layout(self) -> None:
        matching = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<rect id="first-anchor" x="10" y="0" width="200" height="10"/>'
            '<g><rect id="first" x="60" y="20" width="100" height="60" rx="5" '
            'class="control-card" data-layout="control-transition" '
            'data-center-with="first-anchor"/>'
            '<text x="110" y="35" class="eyebrow" text-anchor="middle" '
            'data-layout-slot="identity">A</text>'
            '<text x="110" y="55" class="title" text-anchor="middle" '
            'data-layout-slot="title">B</text></g>'
            '<g transform="translate(20 100)">'
            '<rect id="second-anchor" x="10" y="0" width="200" height="10"/>'
            '<rect id="second" x="60" y="20" width="100" height="60" rx="5" '
            'class="control-card" data-layout="control-transition" '
            'data-center-with="second-anchor"/>'
            '<text x="110" y="35" class="eyebrow" text-anchor="middle" '
            'data-layout-slot="identity">C</text>'
            '<text x="110" y="55" class="title" text-anchor="middle" '
            'data-layout-slot="title">D</text></g>'
            "</svg>"
        )

        self.assertEqual(matching.errors, [])

    def test_control_transition_layout_rejects_drift(self) -> None:
        result = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<rect id="anchor" x="10" y="0" width="200" height="10"/>'
            '<g><rect id="first" x="60" y="20" width="100" height="60" rx="5" '
            'class="control-card" data-layout="control-transition" '
            'data-center-with="anchor"/>'
            '<text x="110" y="35" class="eyebrow" text-anchor="middle" '
            'data-layout-slot="identity">A</text></g>'
            '<g><rect id="second" x="58" y="100" width="104" height="60" rx="5" '
            'class="control-card" data-layout="control-transition" '
            'data-center-with="anchor"/>'
            '<text x="110" y="116" class="eyebrow" text-anchor="middle" '
            'data-layout-slot="identity">B</text></g>'
            "</svg>"
        )

        self.assertTrue(
            any("геометрия переходной карточки" in error for error in result.errors),
            result.errors,
        )

    def test_control_transition_layout_rejects_invalid_contracts(self) -> None:
        result = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<g data-layout="control-transition"/>'
            '<g><rect id="wrong-class" x="0" y="0" width="100" height="60" rx="5" '
            'class="execution-card" data-layout="control-transition"/></g>'
            '<g><rect id="missing-box" x="0" y="0" height="60" rx="5" '
            'class="control-card" data-layout="control-transition"/></g>'
            '<g><rect id="missing-radius" x="0" y="0" width="100" height="60" '
            'class="control-card" data-layout="control-transition"/></g>'
            '<g><rect id="non-text-slot" x="0" y="0" width="100" height="60" rx="5" '
            'class="control-card" data-layout="control-transition"/>'
            '<rect data-layout-slot="identity"/></g>'
            '<g><rect id="duplicate-slot" x="0" y="0" width="100" height="60" rx="5" '
            'class="control-card" data-layout="control-transition"/>'
            '<text x="50" y="15" text-anchor="middle" data-layout-slot="identity">A</text>'
            '<text x="50" y="15" text-anchor="middle" data-layout-slot="identity">B</text>'
            "</g>"
            '<g><rect id="missing-text-position" x="0" y="0" width="100" height="60" '
            'rx="5" class="control-card" data-layout="control-transition"/>'
            '<text data-layout-slot="identity">A</text></g>'
            '<g transform="rotate(90)">'
            '<rect id="rotated" x="0" y="0" width="100" height="60" rx="5" '
            'class="control-card" data-layout="control-transition"/>'
            '<text x="50" y="15" text-anchor="middle" data-layout-slot="identity">A</text>'
            "</g>"
            '<g><rect id="off-centre" x="0" y="0" width="100" height="60" rx="5" '
            'class="control-card" data-layout="control-transition"/>'
            '<text x="48" y="15" data-layout-slot="identity">A</text></g>'
            '<g><rect id="no-slots" x="0" y="0" width="100" height="60" rx="5" '
            'class="control-card" data-layout="control-transition"/></g>'
            "</svg>"
        )

        expected_fragments = (
            'data-layout="control-transition" разрешён только для <rect>',
            "обязана использовать класс control-card",
            "требует числовые x, y, width и height",
            "обязана иметь числовой rx",
            "data-layout-slot разрешён только для <text>",
            "повторяет слот 'identity'",
            "обязан иметь числовые x и y",
            "отличный от translate",
            "обязана задать data-center-with",
            "не содержит ни одного data-layout-slot",
        )
        for fragment in expected_fragments:
            with self.subTest(fragment=fragment):
                self.assertTrue(any(fragment in error for error in result.errors), result.errors)

    def test_control_transition_requires_a_real_centering_anchor(self) -> None:
        result = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<text id="not-a-rect" x="0" y="0">anchor</text>'
            '<rect id="misaligned-anchor" x="20" y="0" width="100" height="10"/>'
            '<g><rect id="missing-target" x="10" y="20" width="100" height="60" rx="5" '
            'class="control-card" data-layout="control-transition" '
            'data-center-with="missing"/>'
            '<text x="60" y="35" text-anchor="middle" data-layout-slot="identity">A</text></g>'
            '<g><rect id="wrong-target" x="10" y="100" width="100" height="60" rx="5" '
            'class="control-card" data-layout="control-transition" '
            'data-center-with="not-a-rect"/>'
            '<text x="60" y="115" text-anchor="middle" data-layout-slot="identity">B</text></g>'
            '<g><rect id="misaligned" x="10" y="180" width="100" height="60" rx="5" '
            'class="control-card" data-layout="control-transition" '
            'data-center-with="misaligned-anchor"/>'
            '<text x="60" y="195" text-anchor="middle" data-layout-slot="identity">C</text></g>'
            "</svg>"
        )

        self.assertTrue(any("указывает на отсутствующий" in error for error in result.errors))
        self.assertTrue(any("обязан указывать на <rect>" in error for error in result.errors))
        self.assertTrue(any("не центрирована" in error for error in result.errors))

    def test_control_transition_skips_unresolvable_anchor_and_slot_transforms(self) -> None:
        result = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<rect id="scaled-anchor" x="0" y="0" width="200" height="10" '
            'transform="scale(2)"/>'
            '<g><rect id="transition" x="50" y="20" width="100" height="60" rx="5" '
            'class="control-card" data-layout="control-transition" '
            'data-center-with="scaled-anchor"/>'
            '<text x="100" y="35" text-anchor="middle" transform="rotate(90)" '
            'data-layout-slot="identity">A</text></g>'
            "</svg>"
        )

        self.assertTrue(any("отличный от translate" in error for error in result.errors))

    def test_control_transition_compares_internal_rhythm_with_template_layout(self) -> None:
        template_result = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<rect id="anchor" x="0" y="0" width="200" height="10"/>'
            '<g><rect id="template" x="50" y="20" width="100" height="60" rx="5" '
            'class="control-card" data-layout="control-transition" '
            'data-center-with="anchor"/>'
            '<text x="100" y="35" class="component-id" text-anchor="middle" '
            'data-layout-slot="identity">A</text></g>'
            "</svg>"
        )
        reference = template_result.control_transition_layouts[0]
        matching = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<rect id="anchor" x="20" y="0" width="200" height="10"/>'
            '<g><rect id="actual" x="70" y="20" width="100" height="60" rx="5" '
            'class="control-card" data-layout="control-transition" '
            'data-center-with="anchor"/>'
            '<text x="120" y="35" class="component-id" text-anchor="middle" '
            'data-layout-slot="identity">B</text></g>'
            "</svg>",
            reference_transition_layout=reference,
        )
        drifted = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<rect id="anchor" x="20" y="0" width="200" height="10"/>'
            '<g><rect id="actual" x="70" y="20" width="100" height="64" rx="5" '
            'class="control-card" data-layout="control-transition" '
            'data-center-with="anchor"/>'
            '<text x="120" y="36" class="component-id" text-anchor="middle" '
            'data-layout-slot="identity">B</text></g>'
            "</svg>",
            reference_transition_layout=reference,
        )

        self.assertEqual(matching.errors, [])
        self.assertTrue(
            any("эталона architecture_diagram_template.svg" in e for e in drifted.errors)
        )

    def test_control_transition_single_detail_uses_template_geometry(self) -> None:
        template = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<rect id="anchor" x="0" y="0" width="200" height="10"/>'
            '<g><rect id="reference" x="50" y="20" width="100" height="80" rx="5" '
            'class="control-card" data-layout="control-transition" '
            'data-center-with="anchor"/>'
            '<text x="100" y="35" class="component-id" text-anchor="middle" '
            'data-layout-slot="identity">A</text>'
            '<text x="100" y="55" class="component-title" text-anchor="middle" '
            'data-layout-slot="title">B</text>'
            '<text x="100" y="75" class="component-text" text-anchor="middle" '
            'data-layout-slot="detail-1">C</text>'
            '<text x="100" y="91" class="component-text" text-anchor="middle" '
            'data-layout-slot="detail-2">D</text></g></svg>'
        )
        self.assertEqual(template.errors, [])
        reference = template.control_transition_layouts[0]
        prefix = (
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<rect id="anchor" x="0" y="0" width="200" height="10"/>'
            '<g><rect id="compact" x="50" y="20" width="100" height="64" rx="5" '
            'class="control-card" data-layout="control-transition" '
            'data-layout-variant="single-detail" data-center-with="anchor"/>'
            '<text x="100" y="35" class="component-id" text-anchor="middle" '
            'data-layout-slot="identity">A</text>'
            '<text x="100" y="55" class="component-title" text-anchor="middle" '
            'data-layout-slot="title">B</text>'
        )
        detail = (
            '<text x="100" y="75" class="component-text" text-anchor="middle" '
            'data-layout-slot="detail-1">C</text>'
        )
        matching = diagram_geometry_lint.check_geometry(
            prefix + detail + "</g></svg>", reference_transition_layout=reference
        )
        shifted = diagram_geometry_lint.check_geometry(
            prefix + detail.replace('y="75"', 'y="76"') + "</g></svg>",
            reference_transition_layout=reference,
        )
        too_tall = diagram_geometry_lint.check_geometry(
            prefix.replace('height="64"', 'height="68"') + detail + "</g></svg>",
            reference_transition_layout=reference,
        )
        missing = diagram_geometry_lint.check_geometry(
            prefix + "</g></svg>", reference_transition_layout=reference
        )
        unknown_variant = diagram_geometry_lint.check_geometry(
            prefix.replace("single-detail", "unknown") + detail + "</g></svg>",
            reference_transition_layout=reference,
        )
        incomplete_reference = diagram_geometry_lint.ControlTransitionLayout(
            card_id=reference.card_id,
            width=reference.width,
            height=reference.height,
            radius=reference.radius,
            slots=tuple(slot for slot in reference.slots if slot.name != "detail-2"),
        )
        invalid_template = diagram_geometry_lint.check_geometry(
            prefix + detail + "</g></svg>",
            reference_transition_layout=incomplete_reference,
        )
        detail_2 = next(slot for slot in reference.slots if slot.name == "detail-2")
        missing_bottom_inset = diagram_geometry_lint.ControlTransitionLayout(
            card_id=reference.card_id,
            width=reference.width,
            height=detail_2.y_offset,
            radius=reference.radius,
            slots=reference.slots,
        )
        invalid_inset = diagram_geometry_lint.check_geometry(
            prefix + detail + "</g></svg>",
            reference_transition_layout=missing_bottom_inset,
        )
        self.assertEqual(matching.errors, [])
        self.assertTrue(
            any("эталона architecture_diagram_template.svg" in e for e in shifted.errors)
        )
        self.assertTrue(
            any("эталона architecture_diagram_template.svg" in e for e in too_tall.errors)
        )
        self.assertTrue(any("ровно слоты identity, title и detail-1" in e for e in missing.errors))
        self.assertTrue(any("неизвестный data-layout-variant" in e for e in unknown_variant.errors))
        self.assertTrue(
            any(
                "эталон переходной карточки не содержит обязательные слоты" in e
                for e in invalid_template.errors
            )
        )
        self.assertTrue(
            any(
                "эталон переходной карточки задаёт неверный нижний отступ" in e
                for e in invalid_inset.errors
            )
        )

    def test_legend_must_list_every_declared_identifier_family(self) -> None:
        root_el = diagram_lint.ElementTree.fromstring(
            '<svg xmlns="http://www.w3.org/2000/svg"><text class="legend-id">ARC_CMP_*</text></svg>'
        )
        result = diagram_lint.LintResult(file="diagram.svg")

        diagram_lint._check_legend_id_families(
            root_el,
            ["ARC_CMP_001", "SEC_CTL_001"],
            result,
        )

        self.assertTrue(
            any("SEC_CTL_*" in error and "отсутствуют" in error for error in result.errors),
            result.errors,
        )

    def test_legend_accepts_exactly_the_declared_identifier_families(self) -> None:
        root_el = diagram_lint.ElementTree.fromstring(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<text class="legend-id">ARC_CMP_*</text>'
            '<text class="legend-id">SEC_CTL_*</text>'
            "</svg>"
        )
        result = diagram_lint.LintResult(file="diagram.svg")

        diagram_lint._check_legend_id_families(
            root_el,
            ["ARC_CMP_001", "SEC_CTL_001"],
            result,
        )

        self.assertEqual(result.errors, [])

    def test_legend_rejects_missing_section_and_unused_family(self) -> None:
        no_legend = diagram_lint.ElementTree.fromstring('<svg xmlns="http://www.w3.org/2000/svg"/>')
        missing_result = diagram_lint.LintResult(file="diagram.svg")
        diagram_lint._check_legend_id_families(
            no_legend,
            ["ARC_CMP_001", "SEC_CTL_001"],
            missing_result,
        )

        extra_legend = diagram_lint.ElementTree.fromstring(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<text class="legend-id">ARC_CMP_*</text>'
            '<text class="legend-id">SEC_CTL_*</text>'
            "</svg>"
        )
        extra_result = diagram_lint.LintResult(file="diagram.svg")
        diagram_lint._check_legend_id_families(
            extra_legend,
            ["ARC_CMP_001"],
            extra_result,
        )

        self.assertTrue(
            any("не перечисляет" in error for error in missing_result.errors),
            missing_result.errors,
        )
        self.assertTrue(
            any(
                "неиспользуемые" in error and "SEC_CTL_*" in error for error in extra_result.errors
            ),
            extra_result.errors,
        )

    def test_external_flow_label_requires_a_traceability_binding(self) -> None:
        root_el = diagram_lint.ElementTree.fromstring(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<text class="flow-text">Пересмотр · Новый Run</text>'
            "</svg>"
        )
        result = diagram_lint.LintResult(file="diagram.svg")

        diagram_lint._check_flow_label_bindings(root_el, result)

        self.assertTrue(
            any("не имеет data-spec-id" in error for error in result.errors),
            result.errors,
        )

    def test_external_flow_label_accepts_an_existing_flow_binding(self) -> None:
        root_el = diagram_lint.ElementTree.fromstring(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<g data-spec-id="ARC_FLOW_001">'
            '<text class="flow-text">ARC_FLOW_001 · Коррекция · Новый Run</text>'
            "</g>"
            "</svg>"
        )
        result = diagram_lint.LintResult(file="diagram.svg")

        diagram_lint._check_flow_label_bindings(root_el, result)

        self.assertEqual(result.errors, [])

    def test_visible_flow_id_must_match_its_binding_and_template_id_is_skipped(self) -> None:
        mismatched = diagram_lint.ElementTree.fromstring(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<g data-spec-id="ARC_FLOW_002">'
            '<text class="flow-text">ARC_FLOW_001 · Новый Run</text>'
            "</g>"
            "</svg>"
        )
        mismatch_result = diagram_lint.LintResult(file="diagram.svg")
        diagram_lint._check_flow_label_bindings(mismatched, mismatch_result)

        template = diagram_lint.ElementTree.fromstring(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<text class="flow-text">ARC_FLOW_XXX · Переход</text>'
            "</svg>"
        )
        template_result = diagram_lint.LintResult(file="template.svg")
        diagram_lint._check_flow_label_bindings(template, template_result)

        self.assertTrue(
            any(
                "ARC_FLOW_001" in error and "не связана" in error
                for error in mismatch_result.errors
            ),
            mismatch_result.errors,
        )
        self.assertEqual(template_result.errors, [])

    def test_visible_arc_flow_labels_require_semantic_fill(self) -> None:
        compliant = diagram_lint.ElementTree.fromstring(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<path id="blue-flow" class="main-line"/>'
            '<path id="red-flow" class="failure-line"/>'
            '<g><rect x="0" y="0" width="100" height="28" class="flow-label-blue" '
            'data-connector-ref="blue-flow"/>'
            '<text x="50" y="18">ARC_FLOW_001 · Поток</text></g>'
            '<g transform="rotate(90)">'
            '<rect x="-50" y="-14" width="100" height="28" class="flow-label-red" '
            'data-connector-ref="red-flow"/>'
            '<text x="0" y="1">ARC_FLOW_XXX · Шаблон</text></g>'
            '<text x="0" y="0" class="legend-id">ARC_FLOW_*</text>'
            "</svg>"
        )
        compliant_result = diagram_lint.LintResult(file="diagram.svg")
        diagram_lint._check_arc_flow_label_fills(compliant, compliant_result)

        invalid = diagram_lint.ElementTree.fromstring(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<text x="10" y="10">ARC_FLOW_001 · Без плашки</text>'
            '<g><rect x="0" y="20" width="100" height="28"/>'
            '<text x="50" y="38">ARC_FLOW_002 · Без класса заливки</text></g>'
            '<g><rect width="bad" height="28" class="flow-label-blue"/>'
            '<text x="50" y="18">ARC_FLOW_003 · Некорректный контейнер</text></g>'
            "<text>ARC_FLOW_004 · Нет координат</text>"
            "</svg>"
        )
        invalid_result = diagram_lint.LintResult(file="diagram.svg")
        diagram_lint._check_arc_flow_label_fills(invalid, invalid_result)

        self.assertEqual(compliant_result.errors, [])
        self.assertTrue(any("не помещена" in error for error in invalid_result.errors))
        self.assertTrue(
            any("без семантической заливки" in error for error in invalid_result.errors)
        )
        self.assertTrue(any("числовые x и y" in error for error in invalid_result.errors))

    def test_arc_flow_label_fill_must_match_its_connector_palette(self) -> None:
        root_el = diagram_lint.ElementTree.fromstring(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<path id="red-flow" class="failure-line"/>'
            '<g><rect x="0" y="0" width="160" height="28" '
            'class="flow-label-blue" data-connector-ref="red-flow"/>'
            '<text x="80" y="18">ARC_FLOW_001 · Поток</text></g>'
            "</svg>"
        )
        result = diagram_lint.LintResult(file="diagram.svg")

        diagram_lint._check_arc_flow_label_fills(root_el, result)

        self.assertTrue(
            any("не совпадает с цветом стрелки" in error for error in result.errors),
            result.errors,
        )

    def test_arc_flow_label_connector_contract_rejects_incomplete_bindings(self) -> None:
        root_el = diagram_lint.ElementTree.fromstring(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<path id="uncoloured-flow" class="custom-line"/>'
            '<g><rect x="0" y="0" width="160" height="28" class="control-card"/>'
            '<text x="80" y="18">ARC_FLOW_001 · Внутри карточки</text></g>'
            '<g><rect x="200" y="0" width="160" height="28" class="flow-label-blue"/>'
            '<text x="280" y="18">ARC_FLOW_002 · Без ссылки</text></g>'
            '<g><rect x="400" y="0" width="160" height="28" class="flow-label-red" '
            'data-connector-ref="missing"/>'
            '<text x="480" y="18">ARC_FLOW_003 · Нет пути</text></g>'
            '<g><rect x="600" y="0" width="160" height="28" class="flow-label-green" '
            'data-connector-ref="uncoloured-flow"/>'
            '<text x="680" y="18">ARC_FLOW_004 · Нет палитры</text></g>'
            "</svg>"
        )
        result = diagram_lint.LintResult(file="diagram.svg")

        diagram_lint._check_arc_flow_label_fills(root_el, result)

        self.assertTrue(any("обязана задать data-connector-ref" in e for e in result.errors))
        self.assertTrue(any("не указывает на существующий <path>" in e for e in result.errors))
        self.assertTrue(any("не имеет ровно одной" in e for e in result.errors))

    def test_every_flow_plaque_requires_a_palette_matched_connector(self) -> None:
        root_el = diagram_lint.ElementTree.fromstring(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<path id="blue-flow" class="main-line"/>'
            '<path id="red-flow" class="control-line"/>'
            '<rect id="valid" class="flow-label-blue" data-connector-ref="blue-flow"/>'
            '<rect id="valid-process" class="flow-label" data-connector-ref="blue-flow"/>'
            '<rect id="missing-ref" class="flow-label-blue"/>'
            '<rect id="missing-path" class="flow-label-red" '
            'data-connector-ref="unknown"/>'
            '<rect id="wrong-palette" class="flow-label-green" '
            'data-connector-ref="red-flow"/>'
            "</svg>"
        )
        result = diagram_lint.LintResult(file="diagram.svg")

        diagram_lint._check_all_flow_label_connectors(root_el, result)

        self.assertEqual(len(result.errors), 3)
        self.assertTrue(any("missing-ref" in error for error in result.errors))
        self.assertTrue(any("missing-path" in error for error in result.errors))
        self.assertTrue(any("wrong-palette" in error for error in result.errors))

    def test_direct_connector_color_must_match_its_source_card(self) -> None:
        root_el = diagram_lint.ElementTree.fromstring(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<rect id="owner-choice" class="control-card"/>'
            '<path class="main-line" data-source-ref="owner-choice"/>'
            "</svg>"
        )
        result = diagram_lint.LintResult(file="diagram.svg")

        diagram_lint._check_connector_source_colors(root_el, result)

        self.assertTrue(
            any("не совпадает с цветом источника" in error for error in result.errors),
            result.errors,
        )

    def test_direct_connector_accepts_the_source_card_palette(self) -> None:
        root_el = diagram_lint.ElementTree.fromstring(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<rect id="owner-choice" class="control-card"/>'
            '<path class="control-main-line" data-source-ref="owner-choice"/>'
            "</svg>"
        )
        result = diagram_lint.LintResult(file="diagram.svg")

        diagram_lint._check_connector_source_colors(root_el, result)

        self.assertEqual(result.errors, [])

    def test_markerless_merge_legs_keep_the_source_palette(self) -> None:
        root_el = diagram_lint.ElementTree.fromstring(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<rect id="blue-source" class="execution-card"/>'
            '<rect id="green-source" class="data-card"/>'
            '<path class="merge-line" data-source-ref="blue-source"/>'
            '<path class="data-merge-line" data-source-ref="green-source"/>'
            "</svg>"
        )
        result = diagram_lint.LintResult(file="diagram.svg")

        diagram_lint._check_connector_source_colors(root_el, result)

        self.assertEqual(result.errors, [])

    def test_direct_connector_requires_a_source_or_shared_route_marker(self) -> None:
        root_el = diagram_lint.ElementTree.fromstring(
            '<svg xmlns="http://www.w3.org/2000/svg"><path class="main-line"/></svg>'
        )
        result = diagram_lint.LintResult(file="diagram.svg")

        diagram_lint._check_connector_source_colors(root_el, result)

        self.assertTrue(
            any("ровно одно из data-source-ref" in error for error in result.errors),
            result.errors,
        )

    def test_bus_line_must_be_declared_as_a_shared_route(self) -> None:
        root_el = diagram_lint.ElementTree.fromstring(
            '<svg xmlns="http://www.w3.org/2000/svg"><path class="bus-line"/></svg>'
        )
        result = diagram_lint.LintResult(file="diagram.svg")

        diagram_lint._check_connector_source_colors(root_el, result)

        self.assertTrue(
            any(
                "ровно одно из data-source-ref" in error and 'data-shared-route="true"' in error
                for error in result.errors
            ),
            result.errors,
        )

    def test_connector_source_contract_reports_invalid_references_and_palettes(self) -> None:
        root_el = diagram_lint.ElementTree.fromstring(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<rect id="unknown-palette" class="ghost-card"/>'
            '<rect id="valid-source" class="control-card"/>'
            '<path class="main-line" data-source-ref="missing"/>'
            '<path class="main-line" data-source-ref="unknown-palette"/>'
            '<path class="ghost-line" data-source-ref="valid-source"/>'
            '<path class="main-line" data-shared-route="true"/>'
            '<path class="control-rail" data-source-ref="valid-source" '
            'data-shared-route="true"/>'
            "</svg>"
        )
        result = diagram_lint.LintResult(file="diagram.svg")

        diagram_lint._check_connector_source_colors(root_el, result)

        self.assertTrue(
            any("missing" in error and "отсутствующий" in error for error in result.errors)
        )
        self.assertTrue(
            any("unknown-palette" in error and "категории" in error for error in result.errors)
        )
        self.assertTrue(
            any("valid-source" in error and "класса цвета" in error for error in result.errors)
        )
        self.assertTrue(any("одновременно" in error for error in result.errors))

    def test_architecture_semantics_do_not_reclassify_process_branches(self) -> None:
        root_el = diagram_lint.ElementTree.fromstring(
            '<svg xmlns="http://www.w3.org/2000/svg" data-diagram-kind="process">'
            '<text class="flow-text">Да</text>'
            '<path class="main-line"/>'
            "</svg>"
        )
        result = diagram_lint.LintResult(file="process.svg")

        diagram_lint._check_architecture_semantics(root_el, [], result)

        self.assertEqual(result.errors, [])

    def test_architecture_kind_enables_flow_and_source_contracts_for_templates(self) -> None:
        root_el = diagram_lint.ElementTree.fromstring(
            '<svg xmlns="http://www.w3.org/2000/svg" data-diagram-kind="architecture">'
            '<text class="flow-text">Пересмотр · Новый Run</text>'
            '<path class="main-line"/>'
            "</svg>"
        )
        result = diagram_lint.LintResult(file="architecture-template.svg")

        diagram_lint._check_architecture_semantics(root_el, [], result)

        self.assertTrue(
            any("не имеет data-spec-id" in error for error in result.errors),
            result.errors,
        )
        self.assertTrue(
            any("ровно одно из data-source-ref" in error for error in result.errors),
            result.errors,
        )

    def test_referenced_vertical_gap_is_checked_against_reference_geometry(self) -> None:
        valid = (
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<g transform="translate(0 5)">'
            '<rect id="quality" x="0" y="10" width="20" height="20"/>'
            "</g>"
            '<g transform="translate(0 100)">'
            '<rect id="owner-choice" x="0" y="3" width="20" height="10" '
            'data-gap-from="quality"/>'
            "</g>"
            "</svg>"
        )
        invalid = valid.replace("translate(0 100)", "translate(0 99)")

        measured = diagram_geometry_lint.check_geometry(valid)
        reference_gap = measured.vertical_gaps[0].value
        valid_result = diagram_geometry_lint.check_geometry(
            valid, reference_gaps={"layer": reference_gap}
        )
        invalid_result = diagram_geometry_lint.check_geometry(
            invalid, reference_gaps={"layer": reference_gap}
        )

        self.assertEqual(valid_result.errors, [])
        self.assertEqual(measured.vertical_gaps[0].kind, "layer")
        self.assertTrue(
            any(
                "эталон шаблона 68 px" in error and "фактически 67 px" in error
                for error in invalid_result.errors
            ),
            invalid_result.errors,
        )

    def test_referenced_vertical_gap_reports_an_invalid_contract(self) -> None:
        missing_source = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<rect y="0" height="10" data-gap-from="missing"/>'
            "</svg>"
        )
        duplicated_value = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<rect id="source" y="0" height="10"/>'
            '<rect y="78" height="10" data-gap-from="source" data-gap="68"/>'
            "</svg>"
        )
        invalid_box = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<rect id="source" height="10"/>'
            '<rect y="78" height="10" data-gap-from="source"/>'
            "</svg>"
        )
        unsupported_transform = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<g transform="scale(2)"><rect id="source" y="0" height="10"/></g>'
            '<rect y="78" height="10" data-gap-from="source"/>'
            "</svg>"
        )
        orphan_kind = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<rect y="0" height="10" data-gap-kind="transition"/>'
            "</svg>"
        )
        unsupported_kind = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<rect id="source" y="0" height="10"/>'
            '<rect y="20" height="10" data-gap-from="source" data-gap-kind="compact"/>'
            "</svg>"
        )

        self.assertTrue(any("missing" in error for error in missing_source.errors))
        self.assertTrue(any("data-gap запрещён" in error for error in duplicated_value.errors))
        self.assertTrue(any("числовые y и height" in error for error in invalid_box.errors))
        self.assertTrue(
            any("отличный от translate" in error for error in unsupported_transform.errors)
        )
        self.assertTrue(any("только вместе" in error for error in orphan_kind.errors))
        self.assertTrue(any("неподдерживаемое" in error for error in unsupported_kind.errors))

    def test_architecture_reference_gaps_are_calculated_from_template_geometry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            template = (
                root
                / "operations"
                / "architecture"
                / "templates"
                / "architecture_diagram_template.svg"
            )
            template.parent.mkdir(parents=True)
            template.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg">'
                '<rect id="component" y="10" height="20"/>'
                '<rect id="transition" y="50" height="10" data-gap-from="component" '
                'data-gap-kind="transition"/>'
                '<rect id="result" y="98" height="10" data-gap-from="component"/>'
                "</svg>",
                encoding="utf-8",
            )
            result = diagram_lint.LintResult(file="diagram.svg")

            gaps = diagram_lint._architecture_reference_gaps(root, {"layer", "transition"}, result)

        self.assertEqual(result.errors, [])
        self.assertEqual(gaps, {"layer": 68, "transition": 20})

    def test_architecture_reference_gap_reports_missing_or_ambiguous_geometry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing_result = diagram_lint.LintResult(file="diagram.svg")
            missing_gap = diagram_lint._architecture_reference_gaps(root, {"layer"}, missing_result)

            template = (
                root
                / "operations"
                / "architecture"
                / "templates"
                / "architecture_diagram_template.svg"
            )
            template.parent.mkdir(parents=True)
            template.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg">'
                '<rect id="source" y="0" height="10"/>'
                '<rect y="78" height="10" data-gap-from="source" data-gap="68"/>'
                "</svg>",
                encoding="utf-8",
            )
            invalid_result = diagram_lint.LintResult(file="diagram.svg")
            invalid_gap = diagram_lint._architecture_reference_gaps(root, {"layer"}, invalid_result)

            template.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg">'
                '<rect id="first" y="0" height="10"/>'
                '<rect id="second" y="78" height="10" data-gap-from="first"/>'
                '<rect y="152" height="10" data-gap-from="second"/>'
                "</svg>",
                encoding="utf-8",
            )
            ambiguous_result = diagram_lint.LintResult(file="diagram.svg")
            ambiguous_gap = diagram_lint._architecture_reference_gaps(
                root, {"layer"}, ambiguous_result
            )

        self.assertIsNone(missing_gap)
        self.assertTrue(any("не найден" in error for error in missing_result.errors))
        self.assertIsNone(invalid_gap)
        self.assertTrue(any("не позволяет" in error for error in invalid_result.errors))
        self.assertIsNone(ambiguous_gap)
        self.assertTrue(any("ровно одно" in error for error in ambiguous_result.errors))

    def test_architecture_reference_transition_layout_is_calculated_from_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            template = (
                root
                / "operations"
                / "architecture"
                / "templates"
                / "architecture_diagram_template.svg"
            )
            template.parent.mkdir(parents=True)
            template.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg">'
                '<rect id="anchor" x="0" y="0" width="200" height="10"/>'
                '<g><rect id="transition" x="50" y="20" width="100" height="60" rx="5" '
                'class="control-card" data-layout="control-transition" '
                'data-center-with="anchor"/>'
                '<text x="100" y="35" class="component-id" text-anchor="middle" '
                'data-layout-slot="identity">A</text></g>'
                "</svg>",
                encoding="utf-8",
            )
            result = diagram_lint.LintResult(file="diagram.svg")

            layout = diagram_lint._architecture_reference_transition_layout(root, result)

        self.assertEqual(result.errors, [])
        self.assertIsNotNone(layout)
        assert layout is not None
        self.assertEqual(layout.signature(), (100, 60, 5, layout.slots))

    def test_architecture_reference_transition_layout_reports_invalid_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing_result = diagram_lint.LintResult(file="diagram.svg")
            missing = diagram_lint._architecture_reference_transition_layout(root, missing_result)

            template = (
                root
                / "operations"
                / "architecture"
                / "templates"
                / "architecture_diagram_template.svg"
            )
            template.parent.mkdir(parents=True)
            template.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg">'
                '<rect id="anchor" x="0" y="0" width="10" height="10"/>'
                '<rect id="bad" x="1.25" y="20" width="10" height="10" rx="2" '
                'class="control-card" data-layout="control-transition" '
                'data-center-with="anchor"/>'
                "</svg>",
                encoding="utf-8",
            )
            invalid_result = diagram_lint.LintResult(file="diagram.svg")
            invalid = diagram_lint._architecture_reference_transition_layout(root, invalid_result)

            template.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")
            absent_result = diagram_lint.LintResult(file="diagram.svg")
            absent = diagram_lint._architecture_reference_transition_layout(root, absent_result)

        self.assertIsNone(missing)
        self.assertTrue(any("не найден" in error for error in missing_result.errors))
        self.assertIsNone(invalid)
        self.assertTrue(any("не позволяет" in error for error in invalid_result.errors))
        self.assertIsNone(absent)
        self.assertTrue(any("ровно один" in error for error in absent_result.errors))

    def test_lint_file_compares_referenced_gap_with_template_geometry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_spec(root, version="1.0")
            template = (
                root
                / "operations"
                / "architecture"
                / "templates"
                / "architecture_diagram_template.svg"
            )
            template.parent.mkdir(parents=True)
            template.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg">'
                '<rect id="template-source" y="0" height="10"/>'
                '<rect y="78" height="10" data-gap-from="template-source"/>'
                "</svg>",
                encoding="utf-8",
            )
            metadata = _metadata_block(
                sources=["specifications/example.md@1.0"], ids=["ARC_CMP_001"]
            )
            svg = root / "diagram.svg"
            body = (
                '<g data-spec-id="ARC_CMP_001">'
                '<rect id="source" y="0" height="10"/>'
                '<rect y="77" height="10" data-gap-from="source"/>'
                "</g>"
            )
            svg.write_text(
                _svg_text(metadata_block=metadata).replace("<g ></g>", body),
                encoding="utf-8",
            )

            result = diagram_lint.lint_file(svg, root)

        self.assertTrue(
            any(
                "эталон шаблона 68 px" in error and "фактически 67 px" in error
                for error in result.errors
            ),
            result.errors,
        )

    def test_lint_file_compares_transition_gap_with_template_geometry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_spec(root, version="1.0")
            template = (
                root
                / "operations"
                / "architecture"
                / "templates"
                / "architecture_diagram_template.svg"
            )
            template.parent.mkdir(parents=True)
            template.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg">'
                '<rect id="template-source" y="0" height="10"/>'
                '<rect y="30" height="10" data-gap-from="template-source" '
                'data-gap-kind="transition"/>'
                "</svg>",
                encoding="utf-8",
            )
            metadata = _metadata_block(
                sources=["specifications/example.md@1.0"], ids=["ARC_CMP_001"]
            )
            body = (
                '<g data-spec-id="ARC_CMP_001">'
                '<rect id="source" y="0" height="10"/>'
                '<rect y="31" height="10" data-gap-from="source" '
                'data-gap-kind="transition"/>'
                "</g>"
            )
            svg = root / "diagram.svg"
            svg.write_text(
                _svg_text(metadata_block=metadata).replace("<g ></g>", body),
                encoding="utf-8",
            )

            result = diagram_lint.lint_file(svg, root)

        self.assertTrue(
            any(
                "эталон шаблона transition-gap 20 px" in error and "фактически 21 px" in error
                for error in result.errors
            ),
            result.errors,
        )

    def test_lint_file_uses_template_transition_layout_for_architecture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_spec(root, version="1.0")
            template = (
                root
                / "operations"
                / "architecture"
                / "templates"
                / "architecture_diagram_template.svg"
            )
            template.parent.mkdir(parents=True)
            template.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg">'
                '<rect id="template-anchor" x="10" y="0" width="200" height="10"/>'
                '<g><rect id="template-transition" x="60" y="20" width="100" height="60" '
                'rx="5" class="control-card" data-layout="control-transition" '
                'data-center-with="template-anchor"/>'
                '<text x="110" y="35" class="component-id" text-anchor="middle" '
                'data-layout-slot="identity">A</text></g>'
                "</svg>",
                encoding="utf-8",
            )
            metadata = _metadata_block(
                sources=["specifications/example.md@1.0"], ids=["ARC_CMP_001"]
            )
            body = (
                "<style>.control-card { fill: red; } .component-id { fill: black; }</style>"
                '<rect id="anchor" x="10" y="0" width="200" height="10"/>'
                '<g data-spec-id="ARC_CMP_001">'
                '<rect id="transition" x="60" y="20" width="100" height="60" rx="5" '
                'class="control-card" data-layout="control-transition" '
                'data-center-with="anchor"/>'
                '<text x="110" y="35" class="component-id" text-anchor="middle" '
                'data-layout-slot="identity">A</text></g>'
            )
            svg = root / "diagram.svg"
            svg.write_text(
                _svg_text(metadata_block=metadata)
                .replace("<svg ", '<svg data-diagram-kind="architecture" ', 1)
                .replace("<g ></g>", body),
                encoding="utf-8",
            )

            result = diagram_lint.lint_file(svg, root)

        self.assertEqual(result.errors, [])

    def test_lint_file_rejects_a_caption_padding_mismatched_with_the_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            template = (
                root
                / "operations"
                / "architecture"
                / "templates"
                / "architecture_diagram_template.svg"
            )
            template.parent.mkdir(parents=True)
            template.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg">'
                '<rect id="template-label" x="0" y="0" width="120" height="28" rx="4" '
                'class="flow-label-blue" data-layout="flow-label" '
                'data-padding-profile="flow-caption"/>'
                '<text x="60" y="19" text-anchor="middle" textLength="96" '
                'lengthAdjust="spacing" data-label-for="template-label">Flow</text>'
                "</svg>",
                encoding="utf-8",
            )
            body = (
                "<style>.flow-label-blue { fill: #eef; }</style>"
                '<rect id="label" x="0" y="0" width="120" height="28" rx="4" '
                'class="flow-label-blue" data-layout="flow-label" '
                'data-padding-profile="flow-caption"/>'
                '<text x="60" y="19" text-anchor="middle" textLength="104" '
                'lengthAdjust="spacing" data-label-for="label">Flow</text>'
            )
            svg = root / "diagram.svg"
            svg.write_text(_svg_text().replace("<g ></g>", body), encoding="utf-8")

            result = diagram_lint.lint_file(svg, root)

        self.assertTrue(
            any(
                "textLength плашки 'label'" in error and "эталона шаблона" in error
                for error in result.errors
            )
        )

    def _dead_definition_svg(self, *, style: str, defs: str = "", body: str) -> str:
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" '
            'viewBox="0 0 12 12" role="img" aria-labelledby="title desc">\n'
            '  <title id="title">Title</title>\n'
            '  <desc id="desc">Desc</desc>\n'
            f"  <defs>{defs}<style>{style}</style></defs>\n"
            f"{body}\n"
            "</svg>\n"
        )

    def test_check_dead_definitions_reports_unused_class_and_marker(self) -> None:
        """Мёртвое определение — ошибка, а не косметика.

        Неиспользуемый класс и маркер ничего не ломают визуально, поэтому
        ни рендеринг, ни ручной просмотр их не находят: именно так дрейф
        накопился в эталонной схеме незамеченным.
        """

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            svg = root / "diagram.svg"
            svg.write_text(
                self._dead_definition_svg(
                    style=".used { fill: #000; } .orphan { fill: #111; }",
                    defs='<marker id="arrow-live" markerWidth="6" markerHeight="6"></marker>'
                    '<marker id="arrow-dead" markerWidth="6" markerHeight="6"></marker>',
                    body='  <g class="used" marker-end="url(#arrow-live)"></g>',
                ),
                encoding="utf-8",
            )
            result = diagram_lint.lint_file(svg, root)

        self.assertFalse(result.ok)
        self.assertTrue(
            any(
                ".orphan" in error and "не используются CSS-классы" in error
                for error in result.errors
            ),
            result.errors,
        )
        self.assertTrue(
            any(
                "#arrow-dead" in error and "не используются маркеры" in error
                for error in result.errors
            ),
            result.errors,
        )
        self.assertFalse(any(".used" in error for error in result.errors), result.errors)
        self.assertFalse(any("#arrow-live" in error for error in result.errors), result.errors)

    def test_check_dead_definitions_reports_undeclared_class_and_missing_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            svg = root / "diagram.svg"
            svg.write_text(
                self._dead_definition_svg(
                    style=".used { fill: #000; }",
                    body='  <g class="used ghost" marker-end="url(#nowhere)"></g>',
                ),
                encoding="utf-8",
            )
            result = diagram_lint.lint_file(svg, root)

        self.assertFalse(result.ok)
        self.assertTrue(
            any(".ghost" in error and "необъявленные" in error for error in result.errors),
            result.errors,
        )
        self.assertTrue(any("#nowhere" in error for error in result.errors), result.errors)

    def test_check_dead_definitions_accepts_a_fully_used_stylesheet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            svg = root / "diagram.svg"
            svg.write_text(
                self._dead_definition_svg(
                    style=".a { fill: #000; } .b { marker-end: url(#arrow); }",
                    defs='<marker id="arrow" markerWidth="6" markerHeight="6"></marker>',
                    body='  <g class="a"></g>\n  <g class="b"></g>',
                ),
                encoding="utf-8",
            )
            result = diagram_lint.lint_file(svg, root)

        self.assertEqual(
            [error for error in result.errors if "класс" in error or "маркер" in error], []
        )

    def test_grouped_side_ports_use_template_derived_spacing_after_transforms(self) -> None:
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<g transform="translate(0 10)">'
            '<rect id="target" x="100" y="20" width="100" height="100"/>'
            '<path d="M240 40H200" data-port-group="right-inputs" '
            'data-port-target="target" data-port-side="right"/>'
            '<path d="M240 72H200" data-port-group="right-inputs" '
            'data-port-target="target" data-port-side="right"/>'
            "</g></svg>"
        )

        matching = diagram_geometry_lint.check_geometry(svg, reference_port_gap=32)
        drifted = diagram_geometry_lint.check_geometry(
            svg.replace("M240 72H200", "M240 44H200"),
            reference_port_gap=32,
        )

        self.assertEqual(matching.errors, [])
        self.assertEqual(matching.port_gaps[0].value, 32)
        self.assertTrue(any("фактически 4 px" in error for error in drifted.errors))

    def test_grouped_side_ports_reject_an_invalid_contract(self) -> None:
        result = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<rect id="target" x="100" y="20" width="100" height="100"/>'
            '<rect data-port-group="not-a-path"/>'
            '<path d="M240 40H200" data-port-group="missing-side" '
            'data-port-target="target"/>'
            '<path d="M240 40H180" data-port-group="off-boundary" '
            'data-port-target="target" data-port-side="right"/>'
            '<path d="M240 72H200" data-port-group="single" '
            'data-port-target="target" data-port-side="right"/>'
            "</svg>"
        )

        self.assertTrue(any("только для <path>" in error for error in result.errors))
        self.assertTrue(any("обязана задать" in error for error in result.errors))
        self.assertTrue(any("не на right-границе" in error for error in result.errors))
        self.assertTrue(any("ровно два коннектора" in error for error in result.errors))

    def test_grouped_side_ports_reject_bad_paths_transforms_and_mixed_targets(self) -> None:
        result = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<rect id="target-a" x="100" y="20" width="100" height="100"/>'
            '<rect id="target-b" x="200" y="20" width="100" height="100"/>'
            '<path d="m240 40h200" data-port-group="bad-path" '
            'data-port-target="target-a" data-port-side="right"/>'
            '<path d="M240 40H200" transform="rotate(10)" data-port-group="bad-transform" '
            'data-port-target="target-a" data-port-side="right"/>'
            '<path d="M240 40H200" data-port-group="mixed" '
            'data-port-target="target-a" data-port-side="right"/>'
            '<path d="M160 72H200" data-port-group="mixed" '
            'data-port-target="target-b" data-port-side="left"/>'
            "</svg>"
        )

        self.assertTrue(any("не позволяет вычислить" in error for error in result.errors))
        self.assertTrue(any("отличный от translate" in error for error in result.errors))
        self.assertTrue(any("одну границу" in error for error in result.errors))

    def test_flow_label_layout_matches_template_geometry(self) -> None:
        template = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<rect id="template-label" x="0" y="0" width="120" height="28" rx="4" '
            'class="flow-label-blue" data-layout="flow-label" data-padding-profile="flow-caption"/>'
            '<text x="60" y="19" text-anchor="middle" textLength="96" lengthAdjust="spacing" '
            'data-label-for="template-label">Flow</text>'
            "</svg>"
        )
        reference = template.flow_label_layouts[0]
        matching = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg"><g transform="translate(10 20)">'
            '<rect id="actual-label" x="0" y="0" width="200" height="28" rx="4" '
            'class="flow-label-red" data-layout="flow-label" data-padding-profile="flow-caption"/>'
            '<text x="100" y="19" text-anchor="middle" textLength="176" lengthAdjust="spacing" '
            'data-label-for="actual-label">Longer flow</text>'
            "</g></svg>",
            reference_flow_label_layouts={"flow-label": reference},
        )
        drifted = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<rect id="actual-label" x="0" y="0" width="200" height="28" rx="4" '
            'class="flow-label-green" data-layout="flow-label" data-padding-profile="flow-caption"/>'
            '<text x="100" y="18" text-anchor="middle" textLength="176" lengthAdjust="spacing" '
            'data-label-for="actual-label">Longer flow</text>'
            "</svg>",
            reference_flow_label_layouts={"flow-label": reference},
        )

        self.assertEqual(matching.errors, [])
        self.assertTrue(any("эталона" in error for error in drifted.errors))

    def test_flow_label_layout_rejects_missing_or_uncentred_labels(self) -> None:
        result = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<g data-layout="flow-label"/>'
            '<rect id="missing-label" x="0" y="0" width="100" height="28" rx="4" '
            'class="flow-label-blue" data-layout="flow-label" data-padding-profile="flow-caption"/>'
            '<rect id="uncentred" x="0" y="40" width="100" height="28" rx="4" '
            'class="flow-label-red" data-layout="flow-label" data-padding-profile="flow-caption"/>'
            '<text x="40" y="59" data-label-for="uncentred">Flow</text>'
            "</svg>"
        )

        self.assertTrue(any("только для <rect>" in error for error in result.errors))
        self.assertTrue(any("ровно 1 <text" in error for error in result.errors))
        self.assertTrue(any("центрирована" in error for error in result.errors))

    def test_flow_label_layout_rejects_invalid_geometry_and_peer_drift(self) -> None:
        result = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<rect id="bad-radius" x="0" y="0" width="100" height="28" '
            'class="flow-label-blue" data-layout="flow-label" data-padding-profile="flow-caption"/>'
            '<rect id="non-text" x="0" y="40" width="100" height="28" rx="4" '
            'class="flow-label-blue" data-layout="flow-label" data-padding-profile="flow-caption"/>'
            '<g data-label-for="non-text"/>'
            '<rect id="bad-coordinates" x="0" y="80" width="100" height="28" rx="4" '
            'class="flow-label-blue" data-layout="flow-label" data-padding-profile="flow-caption"/>'
            '<text data-label-for="bad-coordinates">Flow</text>'
            '<rect id="peer-a" x="0" y="160" width="100" height="28" rx="4" '
            'class="flow-label-blue" data-layout="flow-label" data-padding-profile="flow-caption"/>'
            '<text x="50" y="179" text-anchor="middle" '
            'data-label-for="peer-a">Flow</text>'
            '<rect id="peer-b" x="0" y="200" width="100" height="28" rx="4" '
            'class="flow-label-blue" data-layout="flow-label" data-padding-profile="flow-caption"/>'
            '<text x="50" y="218" text-anchor="middle" '
            'data-label-for="peer-b">Flow</text>'
            "</svg>"
        )

        self.assertTrue(any("числовые x/y/width/height/rx" in error for error in result.errors))
        self.assertTrue(any("обязан стоять на <text>" in error for error in result.errors))
        self.assertTrue(any("числовые x и y" in error for error in result.errors))
        self.assertTrue(any("строки и поля" in error for error in result.errors))

    def test_flow_label_classes_cannot_opt_out_of_layout_contract(self) -> None:
        result = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<rect id="unbound-layout" x="0" y="0" width="100" height="28" rx="4" '
            'class="flow-label-blue"/>'
            '<text x="50" y="19" text-anchor="middle" '
            'data-label-for="unbound-layout">Flow</text>'
            "</svg>"
        )

        self.assertTrue(any("обязана задать data-layout" in error for error in result.errors))

    def test_flow_labels_require_padding_profile_by_object_type(self) -> None:
        result = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<rect id="missing" x="0" y="0" width="100" height="28" rx="4" '
            'class="flow-label-blue" data-layout="flow-label"/>'
            '<text x="50" y="19" text-anchor="middle" data-label-for="missing">Flow</text>'
            '<rect id="unknown" x="0" y="40" width="100" height="28" rx="4" '
            'class="flow-label-blue" data-layout="flow-label" data-padding-profile="wide"/>'
            '<text x="50" y="59" text-anchor="middle" data-label-for="unknown">Flow</text>'
            '<defs><rect id="multiline-port" x="0" y="80" width="160" height="44" rx="4" '
            'class="flow-label-red" data-layout="flow-label-multiline" '
            'data-padding-profile="flow-port"/>'
            '<text x="80" y="97" text-anchor="middle" '
            'data-label-for="multiline-port">First</text>'
            '<text x="80" y="113" text-anchor="middle" '
            'data-label-for="multiline-port">Second</text></defs>'
            '<rect id="port" x="0" y="140" width="300" height="28" rx="4" '
            'class="flow-label-green" data-layout="flow-label" data-padding-profile="flow-port"/>'
            '<text x="150" y="159" text-anchor="middle" data-label-for="port">Port</text>'
            "</svg>"
        )

        self.assertEqual(
            sum("обязана задать data-padding-profile" in error for error in result.errors),
            2,
        )
        self.assertTrue(any("поддерживает только" in error for error in result.errors))
        self.assertFalse(any("плашка потока 'port'" in error for error in result.errors))

    def test_single_line_caption_requires_normalized_inner_text_slot(self) -> None:
        result = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<rect id="missing" x="0" y="0" width="120" height="28" rx="4" '
            'class="flow-label-gray" data-layout="flow-label" '
            'data-padding-profile="flow-caption"/>'
            '<text x="60" y="19" text-anchor="middle" '
            'data-label-for="missing">Flow</text>'
            '<rect id="wrong" x="0" y="40" width="120" height="28" rx="4" '
            'class="flow-label-red" data-layout="flow-label" '
            'data-padding-profile="flow-caption"/>'
            '<text x="60" y="59" text-anchor="middle" textLength="100" '
            'lengthAdjust="spacingAndGlyphs" data-label-for="wrong">Flow</text>'
            '<rect id="port" x="0" y="80" width="300" height="28" rx="4" '
            'class="flow-label-green" data-layout="flow-label" '
            'data-padding-profile="flow-port"/>'
            '<text x="150" y="99" text-anchor="middle" textLength="276" '
            'lengthAdjust="spacing" data-label-for="port">Port</text>'
            "</svg>",
            reference_flow_caption_padding=12.0,
        )

        self.assertTrue(any("числовой textLength" in error for error in result.errors))
        self.assertTrue(any("width - 2 × space-m = 96 px" in error for error in result.errors))
        self.assertTrue(any("lengthAdjust='spacing'" in error for error in result.errors))
        self.assertTrue(any("не должен растягивать текст" in error for error in result.errors))

    def test_single_line_caption_rejects_inline_segments(self) -> None:
        result = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<rect id="segmented" x="0" y="0" width="120" height="28" rx="4" '
            'class="flow-label-gray" data-layout="flow-label" '
            'data-padding-profile="flow-caption"/>'
            '<text x="60" y="19" text-anchor="middle" textLength="96" '
            'lengthAdjust="spacing" data-label-for="segmented">'
            "<tspan>ARC_FLOW_004</tspan><tspan> · SEC_CTL_017</tspan></text>"
            "</svg>"
        )

        self.assertTrue(any("не должна содержать <tspan>" in error for error in result.errors))

    def test_multiline_flow_labels_use_template_rows_and_validate_optional_groups(self) -> None:
        reference_result = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            "<defs>"
            '<rect id="template" x="0" y="0" width="180" height="44" rx="4" '
            'class="flow-label-blue" data-layout="flow-label-multiline" data-padding-profile="flow-caption"/>'
            '<text x="90" y="17" text-anchor="middle" '
            'data-label-for="template">First</text>'
            '<text x="90" y="33" text-anchor="middle" '
            'data-label-for="template">Second</text>'
            "</defs>"
            "</svg>"
        )
        reference = reference_result.flow_label_layouts[0]
        result = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<g transform="rotate(90 100 100)">'
            '<rect id="left" x="0" y="0" width="200" height="44" rx="4" '
            'class="flow-label-red" data-layout="flow-label-multiline" data-padding-profile="flow-caption" '
            'data-equal-width-group="sides"/>'
            '<text x="100" y="17" text-anchor="middle" '
            'data-label-for="left">First</text>'
            '<text x="100" y="33" text-anchor="middle" '
            'data-label-for="left">Second</text></g>'
            '<rect id="right" x="300" y="0" width="180" height="44" rx="4" '
            'class="flow-label-green" data-layout="flow-label-multiline" data-padding-profile="flow-caption" '
            'data-equal-width-group="sides"/>'
            '<text x="390" y="17" text-anchor="middle" '
            'data-label-for="right">First</text>'
            '<text x="390" y="33" text-anchor="middle" '
            'data-label-for="right">Second</text>'
            "</svg>",
            reference_flow_label_layouts={"flow-label-multiline": reference},
        )

        self.assertTrue(any("ширина плашки" in error for error in result.errors))
        self.assertFalse(any("эталона architecture" in error for error in result.errors))

    def test_flow_label_rows_must_be_complete_local_and_bound(self) -> None:
        result = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<g><rect id="multiline" x="0" y="0" width="180" height="44" rx="4" '
            'class="flow-label-blue" data-layout="flow-label-multiline" data-padding-profile="flow-caption"/>'
            '<text x="90" y="17" text-anchor="middle" '
            'data-label-for="multiline">Only row</text></g>'
            '<g><rect id="local" x="0" y="60" width="180" height="28" rx="4" '
            'class="flow-label-red" data-layout="flow-label" data-padding-profile="flow-caption"/></g>'
            '<text x="90" y="79" text-anchor="middle" '
            'data-label-for="local">Wrong parent</text>'
            '<text x="90" y="33" text-anchor="middle" '
            'data-label-for="dangling">Dangling</text>'
            "</svg>"
        )

        self.assertTrue(any("ровно 2 <text" in error for error in result.errors))
        self.assertTrue(any("соседним элементом" in error for error in result.errors))
        self.assertTrue(any("не указывает на плашку" in error for error in result.errors))

    def test_visible_architecture_ids_use_middle_dot_not_slash(self) -> None:
        invalid = diagram_lint.ElementTree.fromstring(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            "<text>ARC_FLOW_004 / SEC_CTL_017 · Плановая задача</text>"
            "</svg>"
        )
        valid = diagram_lint.ElementTree.fromstring(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            "<text>ARC_FLOW_004 · SEC_CTL_004 / 006 / 007–009 / 015 · Плановая задача</text>"
            "</svg>"
        )
        invalid_result = diagram_lint.LintResult(file="invalid.svg")
        valid_result = diagram_lint.LintResult(file="valid.svg")

        diagram_lint._check_visible_id_separators(invalid, invalid_result)
        diagram_lint._check_visible_id_separators(valid, valid_result)

        self.assertTrue(any("символом '/'" in error for error in invalid_result.errors))
        self.assertEqual(valid_result.errors, [])

    def test_architecture_template_exposes_port_and_flow_label_references(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            template = (
                root
                / "operations"
                / "architecture"
                / "templates"
                / "architecture_diagram_template.svg"
            )
            template.parent.mkdir(parents=True)
            template.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg">'
                '<rect id="target" x="100" y="20" width="100" height="100"/>'
                '<path d="M240 40H200" data-port-group="right-inputs" '
                'data-port-target="target" data-port-side="right"/>'
                '<path d="M240 72H200" data-port-group="right-inputs" '
                'data-port-target="target" data-port-side="right"/>'
                '<rect id="label" x="0" y="140" width="120" height="28" rx="4" '
                'class="flow-label-blue" data-layout="flow-label" data-padding-profile="flow-caption"/>'
                '<text x="60" y="159" text-anchor="middle" textLength="96" '
                'lengthAdjust="spacing" '
                'data-label-for="label">Flow</text>'
                '<defs><rect id="multiline-label" x="0" y="180" width="160" height="44" rx="4" '
                'class="flow-label-red" data-layout="flow-label-multiline" data-padding-profile="flow-caption"/>'
                '<text x="80" y="197" text-anchor="middle" '
                'data-label-for="multiline-label">First</text>'
                '<text x="80" y="213" text-anchor="middle" '
                'data-label-for="multiline-label">Second</text></defs>'
                "</svg>",
                encoding="utf-8",
            )
            port_result = diagram_lint.LintResult(file="diagram.svg")
            label_result = diagram_lint.LintResult(file="diagram.svg")
            padding_result = diagram_lint.LintResult(file="diagram.svg")

            port_gap = diagram_lint._architecture_reference_port_gap(root, port_result)
            label_layouts = diagram_lint._architecture_reference_flow_label_layouts(
                root, label_result
            )
            padding = diagram_lint._architecture_reference_flow_caption_padding(
                root, padding_result
            )

        self.assertEqual(port_result.errors, [])
        self.assertEqual(port_gap, 32)
        self.assertEqual(label_result.errors, [])
        self.assertIsNotNone(label_layouts)
        assert label_layouts is not None
        self.assertEqual(label_layouts["flow-label"].text_y_offsets, (19,))
        self.assertEqual(label_layouts["flow-label-multiline"].text_y_offsets, (17, 33))
        self.assertEqual(padding_result.errors, [])
        self.assertEqual(padding, 12.0)

    def test_architecture_reference_helpers_report_missing_invalid_and_empty_templates(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing_port = diagram_lint.LintResult(file="diagram.svg")
            missing_label = diagram_lint.LintResult(file="diagram.svg")
            missing_padding = diagram_lint.LintResult(file="diagram.svg")
            self.assertIsNone(diagram_lint._architecture_reference_port_gap(root, missing_port))
            self.assertIsNone(
                diagram_lint._architecture_reference_flow_label_layouts(root, missing_label)
            )
            self.assertIsNone(
                diagram_lint._architecture_reference_flow_caption_padding(root, missing_padding)
            )

            template = (
                root
                / "operations"
                / "architecture"
                / "templates"
                / "architecture_diagram_template.svg"
            )
            template.parent.mkdir(parents=True)
            template.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg"><rect x="0.33"/></svg>',
                encoding="utf-8",
            )
            invalid_port = diagram_lint.LintResult(file="diagram.svg")
            invalid_label = diagram_lint.LintResult(file="diagram.svg")
            invalid_padding = diagram_lint.LintResult(file="diagram.svg")
            self.assertIsNone(diagram_lint._architecture_reference_port_gap(root, invalid_port))
            self.assertIsNone(
                diagram_lint._architecture_reference_flow_label_layouts(root, invalid_label)
            )
            self.assertIsNone(
                diagram_lint._architecture_reference_flow_caption_padding(root, invalid_padding)
            )

            template.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")
            empty_port = diagram_lint.LintResult(file="diagram.svg")
            empty_label = diagram_lint.LintResult(file="diagram.svg")
            empty_padding = diagram_lint.LintResult(file="diagram.svg")
            self.assertIsNone(diagram_lint._architecture_reference_port_gap(root, empty_port))
            self.assertIsNone(
                diagram_lint._architecture_reference_flow_label_layouts(root, empty_label)
            )
            self.assertIsNone(
                diagram_lint._architecture_reference_flow_caption_padding(root, empty_padding)
            )

        self.assertTrue(any("не найден" in error for error in missing_port.errors))
        self.assertTrue(any("не найден" in error for error in missing_label.errors))
        self.assertTrue(any("не найден" in error for error in missing_padding.errors))
        self.assertTrue(any("не позволяет" in error for error in invalid_port.errors))
        self.assertTrue(any("не позволяет" in error for error in invalid_label.errors))
        self.assertTrue(any("не позволяет" in error for error in invalid_padding.errors))
        self.assertTrue(any("ровно один" in error for error in empty_port.errors))
        self.assertTrue(any("ровно по одной" in error for error in empty_label.errors))
        self.assertTrue(any("ровно одно значение" in error for error in empty_padding.errors))

    def test_architecture_reference_flow_caption_padding_reports_ambiguous_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            template = (
                root
                / "operations"
                / "architecture"
                / "templates"
                / "architecture_diagram_template.svg"
            )
            template.parent.mkdir(parents=True)
            template.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg">'
                '<rect id="twelve" x="0" y="0" width="120" height="28" rx="4" '
                'class="flow-label-blue" data-layout="flow-label" '
                'data-padding-profile="flow-caption"/>'
                '<text x="60" y="19" text-anchor="middle" textLength="96" '
                'lengthAdjust="spacing" data-label-for="twelve">Flow</text>'
                '<rect id="eight" x="0" y="40" width="120" height="28" rx="4" '
                'class="flow-label-blue" data-layout="flow-label" '
                'data-padding-profile="flow-caption"/>'
                '<text x="60" y="59" text-anchor="middle" textLength="104" '
                'lengthAdjust="spacing" data-label-for="eight">Flow</text>'
                "</svg>",
                encoding="utf-8",
            )
            ambiguous_result = diagram_lint.LintResult(file="diagram.svg")
            ambiguous_padding = diagram_lint._architecture_reference_flow_caption_padding(
                root, ambiguous_result
            )

        self.assertIsNone(ambiguous_padding)
        self.assertTrue(any("ровно одно значение" in error for error in ambiguous_result.errors))

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

    def test_default_targets_also_covers_the_template_skeletons(self) -> None:
        """Шаблоны обязаны проходить линтер (foundations §15.1).

        Пока они не входили в цель по умолчанию, эта обязанность не
        исполнялась ни одним автоматическим прогоном — и геометрические
        дефекты шаблонов накапливались незамеченными.
        """

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artefacts = root / "work" / "artefacts" / "architecture"
            artefacts.mkdir(parents=True)
            delivered = artefacts / "delivered.svg"
            delivered.write_text("<svg></svg>", encoding="utf-8")

            templates = root / "operations" / "architecture" / "templates"
            templates.mkdir(parents=True)
            skeleton = templates / "architecture_diagram_template.svg"
            skeleton.write_text("<svg></svg>", encoding="utf-8")

            self.assertEqual(diagram_lint.default_targets(root), sorted([delivered, skeleton]))

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


class ArchitectureCardAlignmentTests(unittest.TestCase):
    def test_template_card_text_inset_rejects_invalid_reference_geometry(self) -> None:
        cases = (
            ("<svg", "не удалось разобрать"),
            ("<svg/>", "не содержит template-component"),
            ('<rect id="template-component" x="0"/>', "не имеет контейнера"),
            (
                '<svg><g><rect id="template-component" x="0"/></g></svg>',
                "не содержит строки component-id",
            ),
            (
                '<svg><g><rect id="template-component" x="bad"/>'
                '<text x="28" class="component-id">ID</text></g></svg>',
                "нечисловой левый отступ",
            ),
            (
                '<svg><g><rect id="template-component" x="28"/>'
                '<text x="28" class="component-id">ID</text></g></svg>',
                "неверный левый отступ",
            ),
        )
        for svg, expected in cases:
            with self.subTest(expected=expected):
                inset, errors = diagram_geometry_lint.measure_reference_card_text_inset(svg)
                self.assertIsNone(inset)
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_card_text_alignment_reports_invalid_geometry_and_ignores_nested_rows(self) -> None:
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<g><rect id="bad-card" x="bad" y="0" width="100" height="60" '
            'class="execution-card"/><text x="28" class="component-id">ID</text></g>'
            '<g><rect id="card" x="0" y="80" width="100" height="60" '
            'class="execution-card"/>'
            '<path d="M0 0H4"/>'
            '<text class="component-id">ID</text>'
            '<rect x="28" y="110" width="44" height="20"/>'
            '<text x="50" y="125" class="component-title" text-anchor="middle">Nested</text>'
            "</g></svg>"
        )
        result = diagram_geometry_lint.check_geometry(svg, reference_card_text_inset=28)
        self.assertTrue(any("требует числовые" in error for error in result.errors))
        self.assertTrue(any("текст без числового x" in error for error in result.errors))
        self.assertFalse(any("Nested" in error for error in result.errors))

    def test_component_and_transition_rows_use_template_left_inset(self) -> None:
        root = Path(__file__).resolve().parents[3]
        template = (root / diagram_lint.ARCHITECTURE_TEMPLATE_RELATIVE).read_text(encoding="utf-8")
        svg = (
            root / "work/artefacts/architecture/personal_ai_platform_architecture.svg"
        ).read_text(encoding="utf-8")
        inset, errors = diagram_geometry_lint.measure_reference_card_text_inset(template)
        self.assertEqual(errors, [])
        self.assertIsNotNone(inset)
        assert inset is not None
        reference = diagram_geometry_lint.check_geometry(template).control_transition_layouts[0]

        def check(text: str) -> list[str]:
            return diagram_geometry_lint.check_geometry(
                text,
                reference_card_text_inset=inset,
                reference_transition_layout=reference,
            ).errors

        self.assertEqual(check(svg), [])
        for card_id in (
            "pre-model-control-card",
            "owner-choice-card",
            "context-card",
            "model-gateway-card",
            "tool-gateway-card",
        ):
            with self.subTest(card_id=card_id):
                start = svg.index(f'<rect id="{card_id}"')
                first_text = re.search(r'<text x="([^"]+)"', svg[start:])
                self.assertIsNotNone(first_text)
                assert first_text is not None
                x_start = start + first_text.start(1)
                x_end = start + first_text.end(1)
                shifted = svg[:x_start] + str(float(first_text.group(1)) + 4) + svg[x_end:]
                self.assertTrue(
                    any(card_id in error and "выровнены слева" in error for error in check(shifted))
                )
        original = '<text x="620.5" y="1245" class="component-title"'
        centred = '<text x="620.5" y="1245" class="component-title" text-anchor="middle"'
        self.assertIn(original, svg)
        self.assertTrue(
            any(
                "pre-model-control-card" in error and "выровнены слева" in error
                for error in check(svg.replace(original, centred, 1))
            )
        )


if __name__ == "__main__":
    unittest.main()
