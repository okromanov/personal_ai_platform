from __future__ import annotations

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

    def test_control_transition_cards_share_calculated_layout(self) -> None:
        matching = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<g><rect id="first" x="10" y="20" width="100" height="60" rx="5" '
            'class="control-card" data-layout="control-transition"/>'
            '<text x="60" y="35" class="eyebrow" text-anchor="middle" '
            'data-layout-slot="identity">A</text>'
            '<text x="60" y="55" class="title" text-anchor="middle" '
            'data-layout-slot="title">B</text></g>'
            '<g transform="translate(20 100)">'
            '<rect id="second" x="10" y="20" width="100" height="60" rx="5" '
            'class="control-card" data-layout="control-transition"/>'
            '<text x="60" y="35" class="eyebrow" text-anchor="middle" '
            'data-layout-slot="identity">C</text>'
            '<text x="60" y="55" class="title" text-anchor="middle" '
            'data-layout-slot="title">D</text></g>'
            "</svg>"
        )

        self.assertEqual(matching.errors, [])

    def test_control_transition_layout_rejects_drift(self) -> None:
        result = diagram_geometry_lint.check_geometry(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<g><rect id="first" x="10" y="20" width="100" height="60" rx="5" '
            'class="control-card" data-layout="control-transition"/>'
            '<text x="60" y="35" class="eyebrow" text-anchor="middle" '
            'data-layout-slot="identity">A</text></g>'
            '<g><rect id="second" x="10" y="100" width="104" height="60" rx="5" '
            'class="control-card" data-layout="control-transition"/>'
            '<text x="62" y="116" class="eyebrow" text-anchor="middle" '
            'data-layout-slot="identity">B</text></g>'
            "</svg>"
        )

        self.assertTrue(
            any("геометрия переходной карточки" in error for error in result.errors),
            result.errors,
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


if __name__ == "__main__":
    unittest.main()
