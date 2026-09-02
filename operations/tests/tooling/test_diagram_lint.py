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
